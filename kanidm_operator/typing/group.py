from typing import TypedDict


class UserMemberResource(TypedDict):
    username: str


class UserIdMemberResource(TypedDict):
    userId: str


class GroupMemberResource(TypedDict):
    group: str


class GroupIdMemberResource(TypedDict):
    groupId: str


class ServiceAccountMemberResource(TypedDict):
    serviceAccount: str


class ServiceAccountIdMemberResource(TypedDict):
    serviceAccountId: str


MemberResource = (
    UserMemberResource
    | UserIdMemberResource
    | GroupMemberResource
    | GroupIdMemberResource
    | ServiceAccountMemberResource
    | ServiceAccountIdMemberResource
)


class GroupResource(TypedDict):
    name: str
    members: list[MemberResource]
