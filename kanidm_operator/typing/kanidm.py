from enum import StrEnum
from typing import TypedDict


class LogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warn"
    ERROR = "error"
    FATAL = "fatal"


class FilesystemType(StrEnum):
    OTHER = "other"
    ZFS = "zfs"


class DatabaseResource(TypedDict):
    fsType: FilesystemType
    arcSize: int | None
    storageClass: str
    storageSize: str


class BackupResource(TypedDict):
    enabled: bool
    schedule: str
    versions: int
    storageClass: str
    storageSize: str


class HighAvailabilityResource(TypedDict):
    enabled: bool
    replicas: int


class CertificateResource(TypedDict):
    issuer: str


class IngressControllers(StrEnum):
    NGINX = "nginx"
    TRAEFIK = "traefik"
    HA_PROXY = "haproxy"
    CADDY = "caddy"


class IngressResource(TypedDict):
    enabled: bool
    reverseProxy: IngressControllers
    annotations: dict[str, str]
    trustXForwardedFor: bool


class KanidmResource(TypedDict):
    version: str
    webPort: int
    ldapPort: int
    database: DatabaseResource
    logLevel: LogLevel
    domain: str
    backup: BackupResource
    highAvailability: HighAvailabilityResource
    certificate: CertificateResource
    ingress: IngressResource
