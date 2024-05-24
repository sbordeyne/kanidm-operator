FROM python:3.11-slim as base
WORKDIR /app

# Install pipx (tooling: poetry)
RUN pip3 install --user pipx
ENV PATH=/root/.local/bin:$PATH
RUN pipx ensurepath

RUN apt update && \
    apt install -y \
        build-essential \
        openssh-client \
        libssl-dev \
        libffi-dev \
        python3-dev \
        ssh \
        git && \
    rm -rf /var/lib/apt/lists/*
RUN mkdir -p -m 0600 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

RUN pipx install poetry
RUN poetry config virtualenvs.create true
RUN poetry config virtualenvs.in-project true

# Install python dependencies
COPY poetry.lock /app/poetry.lock
COPY pyproject.toml /app/pyproject.toml
COPY kanidm_operator /app/kanidm_operator
COPY README.md /app/README.md
RUN --mount=type=ssh poetry install --only=main --no-interaction --no-ansi

FROM python:3.11-alpine as final

WORKDIR /app
COPY --from=base /app .
ENV PATH /app/.venv/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENTRYPOINT ["python3", "-m", "kopf", "run"]
