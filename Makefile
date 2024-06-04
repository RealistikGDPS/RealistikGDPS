#!/usr/bin/make
build:
	docker build -t realistikgdps:latest .

run:
	docker compose up \
		redis \
		mysql \
		meilisearch \
		datadog \
		realistikgdps

run-bg:
	docker compose up -d \
		redis \
		mysql \
		meilisearch \
		datadog \
		realistikgdps

stop:
	docker compose down

logs:
	docker compose logs -f

shell:
	docker run -it --net=host --entrypoint /bin/bash realistikgdps:latest

pma:
	docker compose up phpmyadmin

datadog:
	docker-compose up datadog

converter:
	APP_COMPONENT=converter docker compose up \
		redis \
		mysql \
		meilisearch \
		realistikgdps

lint:
	pre-commit run --all-files
