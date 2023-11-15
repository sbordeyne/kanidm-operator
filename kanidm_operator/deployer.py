from base64 import b64encode
from typing import Any, Callable
from logging import Logger

from jinja2 import Environment, PackageLoader, select_autoescape
from kubernetes.client import (
    CoreV1Api,
    CustomObjectsApi,
    AppsV1Api,
    NetworkingV1Api,
)
import kopf
from ruamel import yaml


def b64enc(value: Any, encoding="utf-8") -> str:
    if isinstance(value, bytes):
        return b64encode(value).decode(encoding)
    return b64encode(str(value).encode(encoding)).decode(encoding)


def slugify(value: str) -> str:
    return (
        value
        .lower()
        .replace(" ", "-")
        .replace("_", "-")
    )


class Deployer:
    def __init__(self, namespace: str, version: str, logger: Logger):
        self.logger = logger
        self.namespace = namespace
        self.version = version
        self.apis = {
            "v1": CoreV1Api(),
            "apps/v1": AppsV1Api(),
            "networking.k8s.io/v1": NetworkingV1Api(),
            "cert-manager.io/v1": CustomObjectsApi(),
        }
        self.env = Environment(
            loader=PackageLoader(
                "kanidm_operator",
                package_path="templates",
                encoding="utf-8",
            ),
            autoescape=select_autoescape(["toml", "yaml", "yml", "json"]),
        )
        self.env.filters["b64enc"] = b64enc
        self.env.filters["slugify"] = slugify
        self.yaml = yaml.YAML(
            typ="safe",
            pure=True,
        )
        self.logger.info("Deployer initialization complete, env loaded.")

    def _create_resource(
        self,
        api,
        method_name: str,
        namespace: str,
        body: dict[str, Any],
        **kwargs,
    ):
        method = getattr(api, method_name)
        return method(namespace=namespace, body=body, **kwargs)

    def create_resource_factory(
        self,
        api_version: str,
        kind: str,
        namespace: str | None = None,
    ) -> Callable[[dict[str, Any]], None]:
        api = self.apis[api_version]
        if namespace is None:
            namespace = self.namespace
        match kind:
            case "Secret":
                return lambda body: self._create_resource(
                    api,
                    "create_namespaced_secret",
                    namespace,
                    body,
                )
            case "Deployment":
                return lambda body: self._create_resource(
                    api,
                    "create_namespaced_deployment",
                    namespace,
                    body,
                )
            case "Service":
                return lambda body: self._create_resource(
                    api,
                    "create_namespaced_service",
                    namespace,
                    body,
                )
            case "Ingress":
                return lambda body: self._create_resource(
                    api,
                    "create_namespaced_ingress",
                    namespace,
                    body,
                )
            case "Certificate":
                return lambda body: self._create_resource(
                    api,
                    "create_namespaced_custom_object",
                    group="cert-manager.io",
                    version="v1",
                    namespace=namespace,
                    plural="certificates",
                    body=body,
                )
            case "ConfigMap":
                return lambda body: self._create_resource(
                    api,
                    "create_namespaced_config_map",
                    namespace,
                    body,
                )
            case "ServiceAccount":
                return lambda body: self._create_resource(
                    api,
                    "create_namespaced_service_account",
                    namespace,
                    body,
                )
            case "Role":
                return lambda body: self._create_resource(
                    api,
                    "create_namespaced_role",
                    namespace,
                    body,
                )
            case "RoleBinding":
                return lambda body: self._create_resource(
                    api,
                    "create_namespaced_role_binding",
                    namespace,
                    body,
                )
            case "PersistentVolumeClaim":
                return lambda body: self._create_resource(
                    api,
                    "create_namespaced_persistent_volume_claim",
                    namespace,
                    body,
                )
            case _:
                raise NotImplementedError(f"Unknown kind: {kind}")

    def deploy(
        self,
        template_name: str,
        **extra_variables,
    ) -> None:
        variables = {
            "namespace": self.namespace,
            "version": self.version,
        }
        template = self.env.get_template(
            name=template_name, globals=variables
        )
        rendered_yaml = template.render(**extra_variables)
        resource = self.yaml.load(rendered_yaml)
        kopf.adopt(resource)
        return self.create_resource_factory(
            api_version=resource["apiVersion"],
            kind=resource["kind"],
            namespace=resource.get("metadata", {}).get("namespace", None),
        )(body=resource)
