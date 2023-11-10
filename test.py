from kubernetes import config, client

config.load_kube_config()

crd_client = client.CustomObjectsApi()

