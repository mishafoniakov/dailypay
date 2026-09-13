up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart airflow-webserver airflow-scheduler

restart-all:
	docker compose restart

ps:
	docker compose ps

health:
	curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/health

dbt-run:
	docker exec dailypay_dbt dbt run

dbt-test:
	docker exec dailypay_dbt dbt test

push:
	git add .
	git commit -m "$(MSG)"
	git push origin main