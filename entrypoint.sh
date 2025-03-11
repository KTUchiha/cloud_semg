#!/bin/bash
set -e

# Check for the --create-db argument and remove it from the argument list
CREATE_DB=0
if [[ "$1" == "--create-db" ]]; then
    CREATE_DB=1
    shift
fi

echo "Starting Supervisor (PostgreSQL, NATS, and App)..."
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf &

if [ "$CREATE_DB" -eq 1 ]; then
    echo "Waiting for PostgreSQL to be available on localhost:5432..."
    # Wait until pg_isready reports PostgreSQL is ready
    until pg_isready -h localhost -p 5432; do
      sleep 1
    done
    echo "PostgreSQL is ready."

    echo "Ensuring database 'sensordb' exists..."
    # Connect to the default 'postgres' database and create sensordb if it doesn't exist.
    psql -h localhost -U postgres -d postgres -c "CREATE DATABASE sensordb" || echo "Database sensordb already exists"

    echo "Creating database schema..."
    # Run the schema file using the postgres superuser on the new database.
    psql -h localhost -U postgres -d sensordb -f /app/db/postgres.sql
    echo "Database schema created."
fi

echo "System startup complete. Keeping container alive..."
tail -f /dev/null
