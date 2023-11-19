import json
from logging import Logger

import kopf

from kanidm_operator.auth import InClusterKanidmClient
from kanidm_operator.typing.group import GroupResource


@kopf.on.create("kanidm.github.io", "v1alpha1", "groups")
async def on_create_group(
    spec: GroupResource,
    patch: dict,
    namespace: str,
    logger: Logger,
    **kwargs,
):
    async with InClusterKanidmClient(namespace, "admin", logger) as client:
        await client.group_create(
            name=spec["name"],
        )
        group = await client.group_get(spec["name"])
        await client.group_set_members(group.uuid, spec["members"])
    patch = {
        "metadata": {
            "annotations": {
                "kanidm.github.io/last-applied-spec": json.dumps(spec),
                "kanidm.github.io/group-id": group.uuid,
            }
        }
    }


@kopf.on.field("kanidm.github.io", "v1alpha1", "groups", field="spec.name")
async def on_update_group_name(**kwargs):
    raise kopf.PermanentError("Group name cannot be changed")


@kopf.on.field("kanidm.github.io", "v1alpha1", "groups", field="spec.members")
async def on_update_group_members(
    spec: GroupResource,
    annotations: dict[str, str],
    namespace: str,
    logger: Logger,
    **kwargs,
):
    group_id = annotations["kanidm.github.io/group-id"]
    async with InClusterKanidmClient(namespace, "admin", logger) as client:
        await client.group_set_members(group_id, spec["members"])


@kopf.on.delete("kanidm.github.io", "v1alpha1", "groups")
async def on_delete_group(
    spec: GroupResource,
    namespace: str,
    logger: Logger,
    **kwargs,
):
    async with InClusterKanidmClient(namespace, "admin", logger) as client:
        await client.group_delete(
            name=spec["name"],
        )
