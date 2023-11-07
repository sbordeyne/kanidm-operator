from dataclasses import dataclass
from uuid import UUID


# FORMAT:

# class: account
# class: memberof
# class: object
# class: person
# displayname: Deepomatic
# memberof: idm_all_persons@auth.slfhst.io
# memberof: idm_all_accounts@auth.slfhst.io
# name: deepomatic
# spn: deepomatic@auth.slfhst.io
# uuid: 39fc59d4-ac00-47f0-b616-28efd5737bab

@dataclass
class Person:
    classes: list[str]
    displayname: str
    memberof: list[str]
    name: str
    spn: str
    uuid: UUID

    @staticmethod
    def parse(data: str) -> "Person":
        parsed = {
            "classes": [],
            "memberof": [],
            "displayname": None,
            "name": None,
            "spn": None,
            "uuid": None,
        }
        lines = data.splitlines()
        for line in lines:
            key, value = line.split(": ", 1)
            if key == "class":
                parsed["classes"].append(value)
            elif key == "memberof":
                parsed["memberof"].append(value)
            else:
                parsed[key] = value
        return Person(**parsed)
