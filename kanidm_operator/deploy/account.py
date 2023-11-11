from logging import Logger

import kopf
from kanidm import KanidmClient


@kopf.on.create("kanidm.github.io", "v1alpha1", "accounts")
async def on_create_account(
    spec: AccountResource, name: str, namespace: str, logger: Logger, **kwargs,
):
    client = KanidmClient()
    await client.create_person(name, namespace)
    await client.close()
