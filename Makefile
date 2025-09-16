# Makefile
.PHONY: help up down logs-be logs-fe reset-db migrate-create migrate-up migrate-down migrate-history

help:
	@echo "Commands:"
	@echo "  up          : Start all services using docker-compose."
	@echo "  down        : Stop all services."
	@echo "  logs-be     : View real-time logs for the backend."
	@echo "  logs-fe     : View real-time logs for the frontend."
	@echo "  reset-db    : Clean and re-initialize the database with sample data."
	@echo ""
	@echo "Database Migration Commands:"
	@echo "  migrate-create MSG='description' : Create a new migration with auto-generated changes."
	@echo "  migrate-up     : Apply all pending migrations to the database."
	@echo "  migrate-down   : Downgrade the database by one migration."
	@echo "  migrate-history: Show migration history."

up:
	@echo "🚀 Starting all Supervity services..."
	docker-compose up --build -d

down:
	@echo "🛑 Stopping all Supervity services..."
	docker-compose down

logs-be:
	@echo "👀 Tailing backend logs..."
	docker-compose logs -f backend

logs-fe:
	@echo "👀 Tailing frontend logs..."
	docker-compose logs -f frontend

reset-db:
	@echo "🧹 Resetting the database..."
	docker-compose exec backend python scripts/cleanup_db.py --reset
	@echo "🌱 Seeding database with initial config data..."
	docker-compose exec backend python scripts/init_config_data.py
	@echo "✅ Database reset complete!"

migrate-create:
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Error: Please provide a message. Usage: make migrate-create MSG='your description'"; \
		exit 1; \
	fi
	@echo "🔄 Creating new migration: $(MSG)"
	docker-compose exec backend alembic revision --autogenerate -m "$(MSG)"
	@echo "✅ Migration created successfully!"

migrate-up:
	@echo "⬆️  Applying pending migrations..."
	docker-compose exec backend alembic upgrade head
	@echo "✅ All migrations applied!"

migrate-down:
	@echo "⬇️  Downgrading database by one migration..."
	docker-compose exec backend alembic downgrade -1
	@echo "✅ Database downgraded!"

migrate-history:
	@echo "📋 Migration history:"
	docker-compose exec backend alembic history --verbose 