from typing import TypedDict


class AccountResource(TypedDict):
    name: str
    displayName: str
    legalName: str | None
    emails: list[str] | None
