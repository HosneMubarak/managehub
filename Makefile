build:
	docker compose up --build -d --remove-orphans
up:
	docker compose up -d
down:
	docker compose down
down-v:
	docker compose down -v
show-logs:
	docker compose logs
show-logs-web:
	docker compose logs web
show-logs-postgres:
	docker compose logs postgres
show-logs-nginx:
	docker compose logs nginx
makemigrations:
	docker compose run --rm web python manage.py makemigrations
migrate:
	docker compose run --rm web python manage.py migrate
collectstatic:
	docker compose run --rm web python manage.py collectstatic --noinput --clear
superuser:
	docker compose run --rm web python manage.py createsuperuser
shell:
	docker compose run --rm web python manage.py shell
db-volume:
	docker volume inspect managehub_managehub_web_postgres_data
managehub-db:
	docker compose exec postgres psql --user=postgres --dbname=managehub_db
restart:
	docker compose restart
rebuild:
	docker compose down && docker compose up --build -d
clean:
	docker system prune -f
clean-all:
	docker system prune -af --volumes
