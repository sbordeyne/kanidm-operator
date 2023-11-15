from logging import Logger

import kopf
from kanidm import KanidmClient

from kanidm_operator.typing.group import GroupResource


@kopf.on.create("kanidm.github.io", "v1alpha1", "groups")
async def on_create_group(
    spec: GroupResource,
    name: str,
    namespace: str,
    logger: Logger,
    **kwargs,
):
    client = KanidmClient()
    await client.group_create(
        name=spec["name"],
    )


@kopf.on.field("kanidm.github.io", "v1alpha1", "groups", field="spec.name")
async def on_update_group(
    old: str,
    new: str,
    status: str,
    namespace: str,
):
    client = KanidmClient()
    await client.group_delete(
        name=old,
    )
    await client.group_create(
        name=new,
    )


@kopf.on.delete("kanidm.github.io", "v1alpha1", "groups")
async def on_delete_group(
    spec: GroupResource,
    name: str,
    namespace: str,
    logger: Logger,
    **kwargs,
):
    client = KanidmClient()
    await client.group_delete(
        name=spec["name"],
    )
