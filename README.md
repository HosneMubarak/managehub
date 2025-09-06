# ManageHub - Project Management System

A Django-based project management system with Docker deployment.

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd managehub
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Build and run with Docker**
   ```bash
   make build
   ```

4. **Create superuser**
   ```bash
   make superuser
   ```

5. **Access the application**
   - Web: http://localhost:8000
   - Admin: http://localhost:8000/admin

## Available Commands

```bash
make build          # Build and start all services
make up             # Start services
make down           # Stop services
make down-v         # Stop services and remove volumes
make restart        # Restart all services
make rebuild        # Rebuild and restart services

make makemigrations # Create new migrations
make migrate        # Apply migrations
make collectstatic  # Collect static files
make superuser      # Create Django superuser
make shell          # Django shell

make show-logs      # Show all logs
make show-logs-web  # Show web service logs
make show-logs-nginx # Show nginx logs
make show-logs-postgres # Show database logs

make clean          # Clean Docker system
make clean-all      # Clean everything including volumes
```

## Services

- **Web**: Django application (port 8000, internal)
- **Nginx**: Reverse proxy and static file server (port 8000)
- **PostgreSQL**: Database (port 5432)

## Environment Variables

Key variables in `.env`:
- `DJANGO_SECRET_KEY`: Django secret key
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: Database configuration
- `DEBUG`: Set to `False` for production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts

## Development

For development with additional tools, install optional dependencies:
```bash
pip install django-debug-toolbar django-extensions ipython
```

## Project Structure

```
managehub/
├── docker/                 # Docker configuration
│   ├── django/            # Django container setup
│   ├── nginx/             # Nginx configuration
│   └── postgres/          # PostgreSQL setup
├── templates/             # Django templates
├── static/               # Static files
├── media/                # User uploads
├── requirements.txt      # Python dependencies
└── docker-compose.yml    # Docker services configuration
