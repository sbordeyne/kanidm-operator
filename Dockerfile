FROM python:3.10-alpine
WORKDIR /app

# Install pipx (tooling: poetry)
RUN pip3 install --user pipx
ENV PATH=/root/.local/bin:$PATH
RUN pipx ensurepath

RUN pipx install poetry
RUN poetry config virtualenvs.create true

# Install python dependencies
COPY poetry.lock /app/poetry.lock
COPY pyproject.toml /app/pyproject.toml
COPY kanidm_operator /app/kanidm_operator
RUN poetry install --only=main

ENTRYPOINT ["poetry", "run", "kopf", "run"]
