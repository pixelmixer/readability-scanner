#!/bin/bash

# Custom ClickHouse entrypoint that initializes SigNoz database

# Start ClickHouse in the background
echo "Starting ClickHouse server..."
sudo -u clickhouse clickhouse-server --config-file=/etc/clickhouse-server/config.xml &

# Wait for ClickHouse to be ready
echo "Waiting for ClickHouse to be ready..."
until clickhouse-client --query "SELECT 1" > /dev/null 2>&1; do
    echo "ClickHouse is not ready yet, waiting..."
    sleep 2
done

echo "ClickHouse is ready, initializing SigNoz database..."

# Create database
echo "Creating signoz_metrics database..."
clickhouse-client --query "CREATE DATABASE IF NOT EXISTS signoz_metrics"

# Create table
echo "Creating distributed_updated_metadata table..."
clickhouse-client --query "CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_updated_metadata (metric_name String, type String, description String, temporality String, is_monotonic UInt8, unit String, updated_at DateTime DEFAULT now()) ENGINE = MergeTree() ORDER BY metric_name"

# Verify the setup
echo "Verifying database setup..."
if clickhouse-client --query "SHOW TABLES FROM signoz_metrics" | grep -q "distributed_updated_metadata"; then
    echo "SigNoz database initialization completed successfully!"
else
    echo "Warning: Table verification failed, but database operations completed"
fi

# Keep the container running
wait
