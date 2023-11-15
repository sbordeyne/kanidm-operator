from base64 import b64decode
import json as jsonlib
from logging import Logger, getLogger
import time
from typing import Any, Coroutine, Dict

import kanidm
from kanidm import CallJsonType
from kanidm.types import ClientResponse, KanidmClientConfig
from kubernetes import client, config
from kubernetes.client.models.v1_service import V1Service
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_secret import V1Secret

from kanidm_operator.deployer import slugify


def get_incluster_config(
    namespace: str,
    username: str,
) -> KanidmClientConfig:
    config.load_incluster_config()
    core = client.CoreV1Api()
    secret: V1Secret = core.list_namespaced_secret(
        namespace,
        label_selector=f"kanidm.github.io/credentials-for={slugify(username)}",
    ).data[0]
    service: V1Service = core.list_namespaced_service(
        namespace=namespace,
        label_selector="app.kubernetes.io/name=kanidm-svc",
    ).data[0]
    service_metadata: V1ObjectMeta = service.metadata
    service_name: str = service_metadata.name
    port: int = [port for port in service.spec.ports if port.name == "https"][0].port
    return KanidmClientConfig(
        uri=f"https://{service_name}.{namespace}.svc.cluster.local:{port}",
        verify_certificate=False,
        username=username,
        password=b64decode(secret.data["password"].encode("utf-8")).decode("utf-8"),
    )


class KanidmClient(kanidm.KanidmClient):
    # To avoid redoing auth all the time, we cache the client in memory
    # Should in theory be fast enough, and we only use 2 clients : admin and idm_admin
    # at most there's also anonymous + some users ? For now it'll do.
    _CACHE = {}

    def __init__(self, namespace: str, username: str, logger: Logger = None):
        self.namespace = namespace
        self.username = username
        self.logger = logger or getLogger(
            f"kanidm_operator.auth.client.KanidmClient.{username}",
        )
        super().__init__(get_incluster_config(namespace, username))

    async def __aenter__(self):
        cache_key = f"{self.namespace}:{self.username}"
        if cache_key in self._CACHE:
            return self._CACHE[cache_key]
        self.config.auth_token = (await self.authenticate_password()).state.success
        self._CACHE[cache_key] = self
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return

    async def _call(
        self,
        method: str,
        path: str,
        headers: Dict[str, str] | None = None,
        timeout: int | None = None,
        json: CallJsonType = None,
        params: Dict[str, str] | None = None,
    ) -> Coroutine[Any, Any, ClientResponse]:
        token_valid = await self.check_token_valid()
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        if query_string:
            query_string = f"?{query_string}"
        body = jsonlib.dumps(json)
        if not token_valid:
            # Redo authentication step
            self.logger.info("Token invalid, re-authenticating.")
            auth = await self.authenticate_password()
            self.logger.info(
                "Authentication step complete for account %s", self.username
            )
            self.config.auth_token = auth.state.success
        self.logger.info(
            "Calling %s%s %s with body %s", method, query_string, path, body
        )
        start = time.time()
        response = await super()._call(method, path, headers, timeout, json, params)
        response_time = time.time() - start
        self.logger.info("Response: %s in %f seconds.", response, response_time)
        return response
