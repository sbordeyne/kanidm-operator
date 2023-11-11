"""
Controls the deployment of kanidm in the cluster.
Will read the kanidms.kanidm.github.io CRD to deploy either:
  - In High Availability mode : n read replicas of kanidm, 1 write replica with UI
  - In Single Instance mode : 1 kanidm instance with UI as a deployment
"""

from base64 import b64encode
import json
from logging import Logger
import time
from typing import Any

from kubernetes import client
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_pod_status import V1PodStatus
import kopf
from jinja2.environment import Environment
from ruamel import yaml

from kanidm_operator.typing.kanidm import KanidmResource


def _get_secret(username: str, password: str, namespace: str) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "type": "Opaque",
        "metadata": {
            "name": username.replace("_", "-"),
            "namespace": "kanidm-system",
        },
        "data": {
            "username": b64encode(username.encode("utf-8")).decode("utf-8"),
            "password": b64encode(password.encode("utf-8")).decode("utf-8"),
        },
    }


@kopf.on.create("kanidm.github.io", "v1alpha1", "kanidms")
async def on_create_kanidms(
    spec: KanidmResource, name: str, namespace: str, logger: Logger, **kwargs,
):
    core = client.CoreV1Api()
    crd_client = client.CustomObjectsApi()
    apps = client.AppsV1Api()
    networking = client.NetworkingV1Api()

    env = Environment()
    certificate = yaml.safe_load(
        env.get_template('certificate.yaml').render(
            namespace=namespace,
            hostname=spec["domain"],
            certificate_issuer=spec["certificate"]["issuer"],
            version=spec["version"],
        ),
    )
    kopf.adopt(certificate)
    crd_client.create_namespaced_custom_object(
        "cert-manager.io",
        "cert-manager.io/v1",
        namespace,
        "certificates",
        certificate,
    )
    pvc_backup = yaml.safe_load(
        env.get_template('pvc-backups.yaml').render(
            namespace=namespace,
            backup_storage_class=spec["backup"]["storageClass"],
            backup_storage_size=spec["backup"]["storageSize"],
            version=spec["version"]
        ),
    )
    kopf.adopt(pvc_backup)
    core.create_namespaced_persistent_volume_claim(namespace, pvc_backup)
    pvc_db = yaml.safe_load(
        env.get_template('pvc-db.yaml').render(
            namespace=namespace,
            db_storage_class=spec["database"]["storageClass"],
            db_storage_size=spec["database"]["storageSize"],
            version=spec["version"],
        ),
    )
    kopf.adopt(pvc_db)
    core.create_namespaced_persistent_volume_claim(namespace, pvc_db)
    service = yaml.safe_load(
        env.get_template('service.yaml').render(
            version=spec["version"],
            namespace=namespace,
            http_port=spec["webPort"],
            ldap_port=spec["ldapPort"]
        ),
    )
    kopf.adopt(service)
    core.create_namespaced_service(namespace, service)
    # TODO: Need to generate configs for HA mode with 1 WriteReplica and n ReadReplicas
    server_config = env.get_template('server.toml').render(
        domain=spec["domain"],
        log_level=spec.get("logLevel", "info"),
        ldap_port=spec.get("ldapPort", "3890"),
        web_port=spec.get("webPort", "8443"),
        database_fs_type=spec["database"]["fsType"],
        database_arc_size=spec["database"]["arcSize"],
        backup_enabled=spec["backup"]["enabled"],
        backup_schedule=spec["backup"]["schedule"],
        backup_versions=spec["backup"]["versions"],
        trust_x_forwarded_for=spec["ingress"]["trustXForwardedFor"],
        role="WriteReplica",
    )
    server_config = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": "kanidm-config", "namespace": namespace},
        "data": {"server.toml": server_config},
    }
    kopf.adopt(server_config)
    core.create_namespaced_config_map(namespace, server_config)

    if not spec["highAvailability"]["enabled"]:
        deployment = yaml.safe_load(
            env.get_template('deployment.yaml').render(
                version=spec["version"],
                namespace=namespace,
                http_port=spec.get("webPort", "8443"),
                ldap_port=spec.get("ldapPort", "3890"),
                image=f"kanidm/server:{spec['version']}",
            ),
        )
        kopf.adopt(deployment)
        apps.create_namespaced_deployment(namespace, deployment)
    # TODO: Handle HighAvailability mode

    if spec.get("ingress").get("enabled", False):
        ingress = yaml.safe_load(
            env.get_template('ingress.yaml').render(
                namespace=namespace,
                hostname=spec["domain"],
                ingress_controller=spec["ingress"]["reverseProxy"],
                version=spec["version"],
            ),
        )
        kopf.adopt(ingress)
        networking.create_namespaced_ingress(namespace, ingress)

    done = False
    while not done:
        pods: list[V1Pod] = core.list_namespaced_pod(
            namespace,
            label_selector="app.kubernetes.io/name=kanidm",
        ).items
        if len(pods) == 0:
            time.sleep(5)
            continue
        pod = pods[0]
        status: V1PodStatus = pod.status
        if status.phase == "Running":
            done = True
            admin_password: str = json.loads(core.connect_get_namespaced_pod_exec(
                pod.metadata.name,
                namespace,
                container="kanidm",
                command=["kanidmd", "recover-account", "-o json", "admin"],
            ))["password"]
            idm_admin_password: str = json.loads(core.connect_get_namespaced_pod_exec(
                pod.metadata.name,
                namespace,
                command=["kanidmd", "recover-account", "-o json", "idm_admin"],
            ))["password"]
            admin_secret = _get_secret("admin", admin_password, namespace)
            kopf.adopt(admin_secret)
            idm_admin_secret = _get_secret("idm_admin", idm_admin_password, namespace)
            kopf.adopt(idm_admin_secret)
            core.create_namespaced_secret("kanidm-system", admin_secret)
            core.create_namespaced_secret("kanidm-system", idm_admin_secret)


@kopf.on.update("kanidm.github.io", "v1alpha1", "kanidms")
async def on_update_kanidms(
    spec: KanidmResource, name: str, namespace: str, logger: Logger, **kwargs,
):
    pass
