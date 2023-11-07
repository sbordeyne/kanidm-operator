from pathlib import Path
from subprocess import check_output, Popen, PIPE

from .models import Person


def login(func):
    def wrapper(self, *args, **kwargs):
        process = Popen(
            [self.executable_path, "login", "--name", self.user, "--url", self.url],
            stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True,
        )
        process.communicate(input=self.password + "\n")
        return func(self, *args, **kwargs)

    return wrapper


class KandimClient:
    def __init__(self, executable_path: Path, user: str, password: str, url: str) -> None:
        self.executable_path = executable_path
        self.user = user
        self.url = url
        self.password = password

    @login
    def person_list(self) -> list[Person]:
        output = check_output(
            [self.executable_path, "person", "list", "--url", self.url],
            shell=True,
        )
        people = output.decode("utf8").split("---")
        people = [person for person in people if person != ""]
        return [Person.parse(person) for person in people]
