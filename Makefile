#!/usr/bin/make
build:
	docker build -t realistikgdps:latest .

run:
	docker-compose up \
		redis \
		mysql \
		meilisearch \
		realistikgdps

run-bg:
	docker-compose up -d \
		redis \
		mysql \
		meilisearch \
		realistikgdps

stop:
	docker-compose down

logs:
	docker-compose logs -f

shell:
	docker run -it --net=host --entrypoint /bin/bash realistikgdps:latest

pma:
	docker-compose up phpmyadmin

converter:
	APP_COMPONENT=converter docker-compose up \
		redis \
		mysql \
		meilisearch \
		realistikgdps

lint:
	pre-commit run --all-files

upload:
	docker build -t ${USER}/realistikgdps:latest .
	docker push ${USER}/realistikgdps:latest
