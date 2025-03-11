# Use Python 3.8 slim as the base image
FROM python:3.8-slim

# Install system dependencies: ffmpeg, build tools, libpq, PostgreSQL, NATS server, and Supervisor
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    libpq-dev \
    postgresql postgresql-contrib \
    nats-server \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Update PATH so that PostgreSQL binaries are found.
# (Adjust the version number if needed.)


# Set the Postgres data directory environment variable and declare it as a volume
ENV PGDATA=/var/lib/postgresql/data
ENV PG_VERSION=15
# Update PATH so that PostgreSQL binaries are found
ENV PATH="/usr/lib/postgresql/${PG_VERSION}/bin:${PATH}"
# Set environment variables for NATS and PostgreSQL
ENV NATS_SERVER="nats://127.0.0.1:4222"  
ENV NATS_USER="semguser"  
ENV NATS_PASSWORD="your_password"  
ENV NATS_TOPIC="sensor.data"  
ENV API_URL="http://127.0.0.1:8000/predict"  
ENV BATCH_SIZE=64

ENV POSTGRES_HOST="localhost"  
ENV POSTGRES_DB="sensordb"  
ENV POSTGRES_USER="semguser"  
ENV POSTGRES_PASSWORD="your_password"


VOLUME ["/var/lib/postgresql/data"]

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the entire project into the container
COPY . .

# Adjust the start_all.sh script to use /app as the PROJECT_DIR and make it executable
RUN chmod +x start_all.sh

# (Optional) Create a minimal NATS server configuration if not provided
RUN echo "port: 4222" > nats-server.conf

# Copy the entrypoint script and make it executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set up Supervisor configuration to run PostgreSQL, NATS, and your app.
# For PostgreSQL, we check if the DB is initialized (by testing for PG_VERSION); if not, we run initdb.
RUN mkdir -p /var/log/supervisor && \
    echo "[supervisord]\nnodaemon=true\n" > /etc/supervisor/conf.d/supervisord.conf && \
    echo "[program:postgres]" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "command=/bin/bash -c 'chown -R postgres:postgres /var/lib/postgresql/data; if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then initdb -D /var/lib/postgresql/data; fi && exec postgres -D /var/lib/postgresql/data'" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "autostart=true" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "autorestart=true" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "user=postgres" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "[program:nats]" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "command=nats-server -c /app/nats-server.conf" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "autostart=true" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "autorestart=true" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "[program:app]" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "command=bash -c './start_all.sh'" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "autostart=true" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "autorestart=true" >> /etc/supervisor/conf.d/supervisord.conf

# Expose ports for FastAPI (8000), Streamlit (8501), UDP (8081), NATS (4222), and PostgreSQL (5432)
EXPOSE 8000 8501 8081 4222 5432

# Use the entrypoint script so that an optional '--create-db' argument can be passed
ENTRYPOINT ["/app/entrypoint.sh"]
