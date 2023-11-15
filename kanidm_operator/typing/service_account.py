from typing import TypedDict


class SecretResource(TypedDict):
    name: str
    namespace: str


class SSHKeyResource(TypedDict):
    tag: str
    publicKey: str


class SSHGenerateResource(TypedDict):
    tag: str
    generate: bool


class TokenResource(TypedDict):
    name: str
    autoRotate: bool
    expiresAfter: str
    readWrite: bool


class ServiceAccountResource(TypedDict):
    name: str
    displayName: str
    expiresAt: str | None
    beginFrom: str | None
    secret: SecretResource
    groups: list[str] | None
    ssh: list[SSHKeyResource | SSHGenerateResource] | None
    tokens: list[TokenResource] | None
