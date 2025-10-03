#!/bin/bash

# SigNoz Database Initialization Script
# This script runs inside the ClickHouse container to initialize the required database and tables

echo "Initializing SigNoz database schema..."

# Wait for ClickHouse to be ready
echo "Waiting for ClickHouse to be ready..."
until clickhouse-client --host signoz-clickhouse --query "SELECT 1" > /dev/null 2>&1; do
    echo "ClickHouse is not ready yet, waiting..."
    sleep 2
done

echo "ClickHouse is ready, creating database and tables..."

# Create databases
echo "Creating signoz_metrics database..."
clickhouse-client --host signoz-clickhouse --query "CREATE DATABASE IF NOT EXISTS signoz_metrics"

echo "Creating signoz_traces database..."
clickhouse-client --host signoz-clickhouse --query "CREATE DATABASE IF NOT EXISTS signoz_traces"

echo "Creating signoz_logs database..."
clickhouse-client --host signoz-clickhouse --query "CREATE DATABASE IF NOT EXISTS signoz_logs"

# Create signoz_metrics tables
echo "Creating signoz_metrics tables..."

# Distributed time series table
clickhouse-client --host signoz-clickhouse --query "
CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_time_series_v4 (
    timestamp DateTime64(9) CODEC(DoubleDelta, LZ4),
    fingerprint UInt64 CODEC(DoubleDelta, LZ4),
    metric_name LowCardinality(String) CODEC(ZSTD(1)),
    datatype LowCardinality(String) CODEC(ZSTD(1)),
    temporality LowCardinality(String) CODEC(ZSTD(1)),
    is_monotonic UInt8 CODEC(T64, LZ4),
    unit LowCardinality(String) CODEC(ZSTD(1)),
    description LowCardinality(String) CODEC(ZSTD(1)),
    value Float64 CODEC(Gorilla, LZ4),
    attributes_string_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
    attributes_string_value Array(String) CODEC(ZSTD(1)),
    attributes_int64_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
    attributes_int64_value Array(Int64) CODEC(T64, LZ4),
    attributes_float64_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
    attributes_float64_value Array(Float64) CODEC(Gorilla, LZ4),
    attributes_bool_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
    attributes_bool_value Array(UInt8) CODEC(T64, LZ4),
    attributes_bytes_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
    attributes_bytes_value Array(String) CODEC(ZSTD(1))
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (metric_name, fingerprint, timestamp)
SETTINGS index_granularity = 8192
"

# Distributed updated metadata table
clickhouse-client --host signoz-clickhouse --query "
CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_updated_metadata (
    metric_name String,
    type String,
    description String,
    temporality String,
    is_monotonic UInt8,
    unit String,
    updated_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY metric_name
"

# Create signoz_traces tables
echo "Creating signoz_traces tables..."

# Distributed top level operations table
clickhouse-client --host signoz-clickhouse --query "
CREATE TABLE IF NOT EXISTS signoz_traces.distributed_top_level_operations (
    timestamp DateTime64(9) CODEC(DoubleDelta, LZ4),
    service_name LowCardinality(String) CODEC(ZSTD(1)),
    operation_name LowCardinality(String) CODEC(ZSTD(1)),
    count UInt64 CODEC(T64, LZ4),
    error_count UInt64 CODEC(T64, LZ4),
    p50 Float64 CODEC(Gorilla, LZ4),
    p95 Float64 CODEC(Gorilla, LZ4),
    p99 Float64 CODEC(Gorilla, LZ4)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (service_name, operation_name, timestamp)
SETTINGS index_granularity = 8192
"

       # Distributed error index table (this was missing and causing the error)
       clickhouse-client --host signoz-clickhouse --query "
       CREATE TABLE IF NOT EXISTS signoz_traces.distributed_signoz_error_index_v2 (
           timestamp DateTime64(9) CODEC(DoubleDelta, LZ4),
           trace_id String CODEC(ZSTD(1)),
           span_id String CODEC(ZSTD(1)),
           service_name LowCardinality(String) CODEC(ZSTD(1)),
           operation_name LowCardinality(String) CODEC(ZSTD(1)),
           error_type LowCardinality(String) CODEC(ZSTD(1)),
           error_message String CODEC(ZSTD(1)),
           error_stack String CODEC(ZSTD(1)),
           attributes_string_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_string_value Array(String) CODEC(ZSTD(1)),
           attributes_int64_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_int64_value Array(Int64) CODEC(T64, LZ4),
           attributes_float64_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_float64_value Array(Float64) CODEC(Gorilla, LZ4),
           attributes_bool_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_bool_value Array(UInt8) CODEC(T64, LZ4),
           attributes_bytes_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_bytes_value Array(String) CODEC(ZSTD(1))
       ) ENGINE = MergeTree()
       PARTITION BY toYYYYMM(timestamp)
       ORDER BY (service_name, operation_name, timestamp)
       SETTINGS index_granularity = 8192
       "

       # Distributed span attributes keys table
       clickhouse-client --host signoz-clickhouse --query "
       CREATE TABLE IF NOT EXISTS signoz_traces.distributed_span_attributes_keys (
           timestamp DateTime64(9) CODEC(DoubleDelta, LZ4),
           tag_key LowCardinality(String) CODEC(ZSTD(1)),
           tag_value String CODEC(ZSTD(1)),
           tag_type LowCardinality(String) CODEC(ZSTD(1)),
           count UInt64 CODEC(T64, LZ4)
       ) ENGINE = MergeTree()
       PARTITION BY toYYYYMM(timestamp)
       ORDER BY (tag_key, tag_value, timestamp)
       SETTINGS index_granularity = 8192
       "

# Create signoz_logs tables
echo "Creating signoz_logs tables..."

       # Distributed logs table (updated with all required columns)
       clickhouse-client --host signoz-clickhouse --query "
       CREATE TABLE IF NOT EXISTS signoz_logs.distributed_logs (
           timestamp DateTime64(9) CODEC(DoubleDelta, LZ4),
           id String CODEC(ZSTD(1)),
           trace_id String CODEC(ZSTD(1)),
           span_id String CODEC(ZSTD(1)),
           trace_flags UInt8 CODEC(T64, LZ4),
           severity_text LowCardinality(String) CODEC(ZSTD(1)),
           severity_number UInt8 CODEC(T64, LZ4),
           scope_name LowCardinality(String) CODEC(ZSTD(1)),
           scope_version LowCardinality(String) CODEC(ZSTD(1)),
           body String CODEC(ZSTD(1)),
           attributes_string_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_string_value Array(String) CODEC(ZSTD(1)),
           attributes_int64_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_int64_value Array(Int64) CODEC(T64, LZ4),
           attributes_float64_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_float64_value Array(Float64) CODEC(Gorilla, LZ4),
           attributes_bool_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_bool_value Array(UInt8) CODEC(T64, LZ4),
           attributes_bytes_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_bytes_value Array(String) CODEC(ZSTD(1)),
           resources_string_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           resources_string_value Array(String) CODEC(ZSTD(1)),
           scope_string_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           scope_string_value Array(String) CODEC(ZSTD(1))
       ) ENGINE = MergeTree()
       PARTITION BY toYYYYMM(timestamp)
       ORDER BY (timestamp)
       SETTINGS index_granularity = 8192
       "

       # Create logs table (non-distributed)
       clickhouse-client --host signoz-clickhouse --query "
       CREATE TABLE IF NOT EXISTS signoz_logs.logs (
           timestamp DateTime64(9) CODEC(DoubleDelta, LZ4),
           id String CODEC(ZSTD(1)),
           trace_id String CODEC(ZSTD(1)),
           span_id String CODEC(ZSTD(1)),
           trace_flags UInt8 CODEC(T64, LZ4),
           severity_text LowCardinality(String) CODEC(ZSTD(1)),
           severity_number UInt8 CODEC(T64, LZ4),
           scope_name LowCardinality(String) CODEC(ZSTD(1)),
           scope_version LowCardinality(String) CODEC(ZSTD(1)),
           body String CODEC(ZSTD(1)),
           attributes_string_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_string_value Array(String) CODEC(ZSTD(1)),
           attributes_int64_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_int64_value Array(Int64) CODEC(T64, LZ4),
           attributes_float64_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_float64_value Array(Float64) CODEC(Gorilla, LZ4),
           attributes_bool_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_bool_value Array(UInt8) CODEC(T64, LZ4),
           attributes_bytes_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           attributes_bytes_value Array(String) CODEC(ZSTD(1)),
           resources_string_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           resources_string_value Array(String) CODEC(ZSTD(1)),
           scope_string_key Array(LowCardinality(String)) CODEC(ZSTD(1)),
           scope_string_value Array(String) CODEC(ZSTD(1))
       ) ENGINE = MergeTree()
       PARTITION BY toYYYYMM(timestamp)
       ORDER BY (timestamp)
       SETTINGS index_granularity = 8192
       "

       # Create distributed tag attributes table
       clickhouse-client --host signoz-clickhouse --query "
       CREATE TABLE IF NOT EXISTS signoz_logs.distributed_tag_attributes_v2 (
           timestamp DateTime64(9) CODEC(DoubleDelta, LZ4),
           tag_key LowCardinality(String) CODEC(ZSTD(1)),
           tag_value String CODEC(ZSTD(1)),
           tag_type LowCardinality(String) CODEC(ZSTD(1)),
           count UInt64 CODEC(T64, LZ4)
       ) ENGINE = MergeTree()
       PARTITION BY toYYYYMM(timestamp)
       ORDER BY (tag_key, tag_value, timestamp)
       SETTINGS index_granularity = 8192
       "

# Verify the setup
echo "Verifying database setup..."
echo "Checking signoz_metrics tables..."
clickhouse-client --host signoz-clickhouse --query "SHOW TABLES FROM signoz_metrics"

echo "Checking signoz_traces tables..."
clickhouse-client --host signoz-clickhouse --query "SHOW TABLES FROM signoz_traces"

echo "Checking signoz_logs tables..."
clickhouse-client --host signoz-clickhouse --query "SHOW TABLES FROM signoz_logs"

echo "SigNoz database initialization complete!"
