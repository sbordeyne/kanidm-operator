from logging import Logger

import kopf

from kanidm_operator.auth import InClusterKanidmClient
from kanidm_operator.typing.badlist import BadlistResource


@kopf.on.create("kanidm.github.io", "v1alpha1", "pw-badlists")
async def on_create_badlist(
    spec: BadlistResource,
    namespace: str,
    logger: Logger,
    **kwargs,
):
    async with InClusterKanidmClient(namespace, "admin", logger) as client:
        await client.system_password_badlist_append(spec["passwords"])


@kopf.on.delete("kanidm.github.io", "v1alpha1", "pw-badlists")
async def on_delete_badlist(
    spec: BadlistResource,
    namespace: str,
    logger: Logger,
    **kwargs,
):
    async with InClusterKanidmClient(namespace, "admin", logger) as client:
        await client.system_password_badlist_remove(spec["passwords"])


@kopf.on.field("kanidm.github.io", "v1alpha1", "pw-badlists", field="spec.passwords")
async def on_update_badlist(
    old: list[str],
    new: list[str],
    namespace: str,
    logger: Logger,
    **kwargs,
):
    to_add = set(new) - set(old)
    to_remove = set(old) - set(new)
    async with InClusterKanidmClient(namespace, "admin", logger) as client:
        await client.system_password_badlist_append(to_add)
        await client.system_password_badlist_remove(to_remove)
