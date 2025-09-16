# Dockerfile

# Stage 1: Build with dependencies
FROM python:3.11-slim as builder
WORKDIR /opt/venv
RUN apt-get update && apt-get install -y build-essential && apt-get clean
COPY packages/requirements.txt ./requirements.txt
RUN python -m venv .
RUN . bin/activate && pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Stage 2: Final production image
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
# Copy only the application source code and Gunicorn config
COPY src ./src
COPY gunicorn ./gunicorn
COPY sample_data ./sample_data
COPY scripts ./scripts
# Copy alembic files for database migrations
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

# Create necessary directories
RUN mkdir -p generated_documents
RUN chmod 755 generated_documents

# Add the venv to the PATH
ENV PATH="/opt/venv/bin:$PATH"

# Set PYTHONPATH to include src directory, allowing `app.main:app` to be found
ENV PYTHONPATH="/app/src"

# Health check using /api/health endpoint
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Expose the port the app runs on
EXPOSE 8000

# The default command to run the application in production.
# This will be overridden by the docker-compose file for local development.
CMD ["gunicorn", "-c", "gunicorn/prod.py", "app.main:app"]