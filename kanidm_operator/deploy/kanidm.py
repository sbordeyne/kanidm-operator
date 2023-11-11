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

from kubernetes import client
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_pod_status import V1PodStatus
import kopf
from jinja2.environment import Environment
from ruamel import yaml

from kanidm_operator.typing.kanidm import KanidmResource


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
    core.create_namespaced_persistent_volume_claim(namespace, pvc_backup)
    pvc_db = yaml.safe_load(
        env.get_template('pvc-db.yaml').render(
            namespace=namespace,
            db_storage_class=spec["database"]["storageClass"],
            db_storage_size=spec["database"]["storageSize"],
            version=spec["version"],
        ),
    )
    core.create_namespaced_persistent_volume_claim(namespace, pvc_db)
    service = yaml.safe_load(
        env.get_template('service.yaml').render(
            version=spec["version"],
            namespace=namespace,
            http_port=spec["webPort"],
            ldap_port=spec["ldapPort"]
        ),
    )
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
    core.create_namespaced_config_map(
        namespace,
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "kanidm-config", "namespace": namespace},
            "data": {"server.toml": server_config},
        },
    )

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
            core.create_namespaced_secret(
                namespace,
                {
                    "apiVersion": "v1",
                    "kind": "Secret",
                    "type": "Opaque",
                    "metadata": {
                        "name": "kanidm-admin-password",
                        "namespace": namespace,
                    },
                    "data": {
                        "username": "admin",
                        "password": b64encode(admin_password.encode("utf-8")).decode(),
                    },
                },
            )
            core.create_namespaced_secret(
                namespace,
                {
                    "apiVersion": "v1",
                    "kind": "Secret",
                    "type": "Opaque",
                    "metadata": {
                        "name": "kanidm-idm-admin-password",
                        "namespace": namespace,
                    },
                    "data": {
                        "username": "idm_admin",
                        "password": b64encode(idm_admin_password.encode("utf-8")).decode(),
                    },
                },
            )


@kopf.on.update("kanidm.github.io", "v1alpha1", "kanidms")
async def on_update_kanidms(
    spec: KanidmResource, name: str, namespace: str, logger: Logger, **kwargs,
):
    pass


@kopf.on.delete("kanidm.github.io", "v1alpha1", "kanidms")
async def on_delete_kanidms(
    spec: KanidmResource, name: str, namespace: str, logger: Logger, **kwargs,
):
    core = client.CoreV1Api()
    crd_client = client.CustomObjectsApi()
    apps = client.AppsV1Api()

    crd_client.delete_namespaced_custom_object(
        "cert-manager.io",
        "cert-manager.io/v1",
        namespace,
        "certificates",
        "kanidm-tls",
    )
    core.delete_namespaced_persistent_volume_claim("kanidm-backups", namespace)
    core.delete_namespaced_persistent_volume_claim("kanidm-db", namespace)
    core.delete_namespaced_service("kanidm-svc", namespace)
    core.delete_namespaced_config_map("kanidm-config", namespace)
    if not spec["highAvailability"]["enabled"]:
        apps.delete_namespaced_deployment("kanidm", namespace)
