-- PostgreSQL init script: runs automatically on the very first container startup.
-- Creates a dedicated database for Airflow metadata, keeping 'startup_os'
-- exclusively for application tables (documents, chunks, app_monitoring_logs).
SELECT 'CREATE DATABASE airflow_db'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'airflow_db'
)\gexec
