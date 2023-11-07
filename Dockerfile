FROM kanidm/tools:latest as tools
FROM opensuse/python:latest
WORKDIR /app

# Copy kanidm binary from tools image
COPY --from=tools /sbin/kanidm /bin/kanidm

# Install python dependencies

COPY poetry.lock /app/poetry.lock
COPY pyproject.toml /app/pyproject.toml
RUN pip install poetry
RUN python3 -m poetry config virtualenvs.create true
RUN python3 -m poetry install --only=main --no-root

# Copy the rest of the app

COPY kanidm_operator /app/kanidm_operator
RUN python3 -m poetry install --only=main

CMD ["python3", "-m", "kanidm_operator"]