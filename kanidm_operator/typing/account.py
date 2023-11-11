from typing import TypedDict


class AccountResource(TypedDict):
    name: str
    displayName: str
    groups: list[str] | None
    legalName: str | None
    emails: list[str] | None
