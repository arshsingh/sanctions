.PHONY: build run psql test test-data migrate migration

build:
	docker-compose build

run:
	docker-compose up

psql:
	docker-compose exec postgres psql -U postgres -d sanctions

test:
	docker-compose run --rm --no-deps --entrypoint python -w /src/worker worker \
		-m unittest discover -s tests -p 'test_*.py'

test-data:
	docker-compose run --rm worker generate-test-data

migrate:
	docker-compose run --rm migrations up

migration:  # make migration name_of_migration
	docker-compose run --rm migrations new $1
