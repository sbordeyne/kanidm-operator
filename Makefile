ITERATION = 1
VERSION = 1.1.0-beta.13

black:
	poetry run black kanidm_operator

shell:
	env $(cat .env | grep -v "#" | xargs) poetry run python3 -m asyncio

build:
	docker build -t sbordeyne/kanidm-operator:$(VERSION)-$(ITERATION) .
	docker tag sbordeyne/kanidm-operator:$(VERSION)-$(ITERATION) sbordeyne/kanidm-operator:latest

push:
	docker push sbordeyne/kanidm-operator:$(VERSION)-$(ITERATION)
	docker push sbordeyne/kanidm-operator:latest

all: build push
