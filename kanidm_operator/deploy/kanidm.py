"""
Controls the deployment of kanidm in the cluster.
Will read the kanidms.kanidm.github.io CRD to deploy either:
  - In High Availability mode : n read replicas of kanidm, 1 write replica with UI
  - In Single Instance mode : 1 kanidm instance with UI as a deployment
"""

import json
from logging import Logger
import time

from kubernetes import client
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_pod_status import V1PodStatus
import kopf

from kanidm_operator.deployer import Deployer
from kanidm_operator.typing.kanidm import KanidmResource


@kopf.on.create("kanidm.github.io", "v1alpha1", "kanidms")
async def on_create_kanidms(
    spec: KanidmResource,
    name: str,
    namespace: str,
    logger: Logger,
    **kwargs,
):
    deployer = Deployer(namespace, spec["version"], logger)

    deployer.deploy(
        "certificate.yaml",
        hostname=spec["domain"],
        certificate_issuer=spec["certificate"]["issuer"],
        version=spec["version"],
    )
    deployer.deploy(
        "pvc-backups.yaml",
        backup_storage_class=spec["backup"]["storageClass"],
        backup_storage_size=spec["backup"]["storageSize"],
    )
    deployer.deploy(
        "pvc-db.yaml",
        db_storage_class=spec["database"]["storageClass"],
        db_storage_size=spec["database"]["storageSize"],
    )
    deployer.deploy(
        "service.yaml",
        http_port=spec["webPort"],
        ldap_port=spec["ldapPort"],
    )
    deployer.deploy(
        "server.toml",
        domain=spec["domain"],
        log_level=spec.get("logLevel", "info"),
        ldap_port=spec.get("ldapPort", "3890"),
        http_port=spec.get("webPort", "8443"),
        database_fs_type=spec["database"]["fsType"],
        database_arc_size=spec["database"]["arcSize"],
        backup_enabled=spec["backup"]["enabled"],
        backup_schedule=spec["backup"]["schedule"],
        backup_versions=spec["backup"]["versions"],
        trust_x_forwarded_for=spec["ingress"]["trustXForwardedFor"],
        role="WriteReplica",
    )

    if not spec["highAvailability"]["enabled"]:
        deployer.deploy(
            "deployment.yaml",
            http_port=spec.get("webPort", "8443"),
            ldap_port=spec.get("ldapPort", "3890"),
            image=f"kanidm/server:{spec['version']}",
        )
    # TODO: Handle HighAvailability mode

    if spec.get("ingress").get("enabled", False):
        deployer.deploy(
            "ingress.yaml",
            hostname=spec["domain"],
            ingress_controller=spec["ingress"]["reverseProxy"],
        )

    done = False
    core = client.CoreV1Api()
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
            admin_password: str = json.loads(
                core.connect_get_namespaced_pod_exec(
                    pod.metadata.name,
                    namespace,
                    container="kanidm",
                    command=["kanidmd", "recover-account", "-o json", "admin"],
                )
            )["password"]
            idm_admin_password: str = json.loads(
                core.connect_get_namespaced_pod_exec(
                    pod.metadata.name,
                    namespace,
                    command=["kanidmd", "recover-account", "-o json", "idm_admin"],
                )
            )["password"]
            deployer.deploy(
                "secret.yaml",
                username="admin",
                password=admin_password,
            )
            deployer.deploy(
                "secret.yaml",
                username="idm_admin",
                password=idm_admin_password,
            )


@kopf.on.update("kanidm.github.io", "v1alpha1", "kanidms")
async def on_update_kanidms(
    spec: KanidmResource,
    name: str,
    namespace: str,
    logger: Logger,
    **kwargs,
):
    pass
