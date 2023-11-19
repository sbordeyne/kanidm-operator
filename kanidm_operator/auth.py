from base64 import b64decode
from datetime import datetime, timedelta
import json as jsonlib
from logging import Logger, getLogger
import os
import time
from typing import Any, Coroutine, Dict, Optional

import kanidm
from kanidm import CallJsonType
from kanidm.types import ClientResponse, KanidmClientConfig
from kubernetes import client as kube_client, config
from kubernetes.client.models.v1_service import V1Service
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_secret import V1Secret

from kanidm_operator.deployer import slugify


def get_incluster_config(
    namespace: str,
    username: str,
) -> KanidmClientConfig:
    config.load_incluster_config()
    core = kube_client.CoreV1Api()
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
    _CLIENTS = {}
    _AUTH_EXPIRY = {}

    def __init__(self, logger: Logger = None, username: str = "admin", **kwargs):
        self.username = username
        self.logger = logger or getLogger(
            f"kanidm_operator.auth.client.KanidmClient.{username}",
        )
        super().__init__(**kwargs)

    async def check_token_valid(self, token: str | None = None) -> bool:
        token = token or self.config.auth_token
        if token is None:
            return False
        expire_at = self._AUTH_EXPIRY.get(token, None)
        if expire_at is None:
            valid = await super().check_token_valid(token)
            if valid:
                self._AUTH_EXPIRY[token] = datetime.now() + timedelta(hours=1)
            return valid
        if expire_at > datetime.now():
            return True
        return await super().check_token_valid(token)

    async def __aenter__(self) -> "KanidmClient":
        cache_key = self.username
        if cache_key in self._CLIENTS:
            return self._CLIENTS[cache_key]
        await self.authenticate_password()
        self._CLIENTS[cache_key] = self
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
        if path.startswith("/v1/auth"):
            return await super()._call(method, path, headers, timeout, json, params)
        token_valid = await self.check_token_valid()
        query_string = ""
        if params:
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

class InClusterKanidmClient(KanidmClient):
    def __init__(self, namespace: str, username: str = "admin", logger: Logger = None):
        super().__init__(
            config=get_incluster_config(namespace, username),
            username=username,
            logger=logger,
        )


class LocalKanidmClient(KanidmClient):
    def __init__(self, username: str):
        self.namespace = "local"
        self.username = username
        self.logger = getLogger(
            f"kanidm_operator.auth.client.LocalKanidmClient.{self.username}",
        )
        super().__init__(
            config=KanidmClientConfig(
                uri="https://localhost:443",
                verify_certificate=False,
                username=username,
                password=os.getenv(f"KANIDM_{username.upper()}_PASSWORD"),
            ),
        )


client = LocalKanidmClient("admin")
idm_client = LocalKanidmClient("idm_admin")
# from kanidm_operator.auth import client, idm_client; await client.__aenter__(); await idm_client.__aenter__()
