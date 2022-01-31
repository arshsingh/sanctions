.PHONY: build run psql test-data migrate migration

build:
	docker-compose build

run:
	docker-compose up

psql:
	docker-compose exec postgres psql -U postgres -d sanctions

test-data:
	docker-compose run --rm worker generate-test-data

migrate:
	docker-compose run --rm migrations up

migration:  # make migration name_of_migration
	docker-compose run --rm migrations new $1
