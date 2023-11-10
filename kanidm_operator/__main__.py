from kubernetes import client, config
from kanidm import KanidmClient, KanidmClientConfig


def main():
    config.load_incluster_config()
    crd_client = client.CustomObjectsApi()
    kanidms_config = crd_client.list_cluster_custom_object(
        group="kanidm.github.io",
        version="v1alpha1",
        plural="kanidms",
    )
