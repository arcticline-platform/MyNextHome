-- ============================================================================
-- MyNextHome Database Setup Script
-- Creates PostgreSQL database with PostGIS and optimizations for large queries
-- ============================================================================

-- Create database with optimized settings for large datasets and spatial queries
CREATE DATABASE db_mynexthome
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

-- Connect to the new database
\c db_mynexthome

-- ============================================================================
-- Enable PostGIS Extensions
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgis_raster;

-- ============================================================================
-- Performance Monitoring Extensions
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- ============================================================================
-- Database Configuration for Large Queries and Spatial Operations
-- Note: Some settings require superuser privileges and may need to be set
-- at the server level in postgresql.conf. These are database-level settings.
-- ============================================================================

-- Connect back to postgres database to set database-level configurations
\c postgres

-- Set work_mem for better handling of large queries (adjust based on available RAM)
-- This allows more memory for sorting and hash operations per query
ALTER DATABASE db_mynexthome SET work_mem = '256MB';

-- Set maintenance_work_mem for VACUUM, CREATE INDEX, etc.
ALTER DATABASE db_mynexthome SET maintenance_work_mem = '1GB';

-- Increase effective_cache_size (should be ~50-75% of total RAM)
-- This helps the query planner make better decisions
ALTER DATABASE db_mynexthome SET effective_cache_size = '4GB';

-- Set random_page_cost lower for SSD storage (default is 4.0 for HDD)
-- For SSDs, 1.1-1.5 is more appropriate
ALTER DATABASE db_mynexthome SET random_page_cost = 1.1;

-- Enable JIT compilation for complex queries (PostgreSQL 11+)
ALTER DATABASE db_mynexthome SET jit = on;

-- Set statement timeout to prevent runaway queries (30 minutes)
ALTER DATABASE db_mynexthome SET statement_timeout = '1800000';

-- Set lock timeout (10 minutes)
ALTER DATABASE db_mynexthome SET lock_timeout = '600000';

-- Increase max_parallel_workers_per_gather for parallel query execution
ALTER DATABASE db_mynexthome SET max_parallel_workers_per_gather = 4;

-- Set max_parallel_workers for overall parallel operations
-- Note: This is a server-level setting, but we set it here for reference
-- You may need to set this in postgresql.conf: max_parallel_workers = 8

-- ============================================================================
-- Connection and Transaction Settings
-- ============================================================================

-- Enable synchronous commit for data integrity (can be set to 'off' for better performance)
-- For production with replication, keep as 'on'
ALTER DATABASE db_mynexthome SET synchronous_commit = 'on';

-- Note: max_connections and checkpoint_completion_target are server-level settings
-- and should be configured in postgresql.conf:
-- max_connections = 100
-- checkpoint_completion_target = 0.9

-- ============================================================================
-- Spatial Query Optimizations
-- ============================================================================

-- Set geqo_threshold for better query planning with many tables
ALTER DATABASE db_mynexthome SET geqo_threshold = 12;

-- Enable query planner optimizations (these are session-level, but good defaults)
-- Note: These are typically set per-session, but we document them here
-- enable_seqscan, enable_indexscan, etc. are usually left at defaults

-- ============================================================================
-- Logging and Monitoring
-- ============================================================================

-- Log slow queries (queries taking longer than 1 second)
-- Note: log_min_duration_statement, log_connections, log_disconnections
-- are server-level settings and should be set in postgresql.conf:
-- log_min_duration_statement = 1000
-- log_connections = on
-- log_disconnections = on

-- ============================================================================
-- Vacuum and Maintenance Settings
-- ============================================================================

-- Note: autovacuum and autovacuum_work_mem are server-level settings
-- and should be configured in postgresql.conf:
-- autovacuum = on
-- autovacuum_work_mem = 512MB

-- Reconnect to the new database for remaining operations
\c db_mynexthome

-- ============================================================================
-- Create helper functions for spatial operations
-- ============================================================================

-- Function to get database size
CREATE OR REPLACE FUNCTION get_database_size()
RETURNS TABLE(database_name text, size text) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        datname::text,
        pg_size_pretty(pg_database_size(datname))::text
    FROM pg_database
    WHERE datname = current_database();
END;
$$ LANGUAGE plpgsql;

-- Function to analyze all tables (useful for maintaining statistics)
CREATE OR REPLACE FUNCTION analyze_all_tables()
RETURNS void AS $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'ANALYZE ' || quote_ident(r.tablename);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Verification and Reporting
-- ============================================================================

-- Display PostGIS version
SELECT 'PostGIS Version: ' || PostGIS_version() as info;

-- Display database configuration (database-level settings)
SELECT 
    name,
    setting,
    unit,
    context,
    source
FROM pg_settings
WHERE name IN (
    'work_mem',
    'maintenance_work_mem',
    'effective_cache_size',
    'random_page_cost',
    'statement_timeout',
    'lock_timeout',
    'max_parallel_workers_per_gather',
    'jit'
)
ORDER BY name;

-- Display database size
SELECT * FROM get_database_size();

-- Display installed extensions
SELECT 
    extname as "Extension Name",
    extversion as "Version",
    n.nspname as "Schema"
FROM pg_extension e
JOIN pg_namespace n ON e.extnamespace = n.oid
ORDER BY extname;

\echo ''
\echo '============================================================================'
\echo 'Database setup completed successfully!'
\echo '============================================================================'
\echo 'Database: db_mynexthome'
\echo 'PostGIS: Enabled with spatial optimizations'
\echo 'Configuration: Optimized for large queries and spatial operations'
\echo '============================================================================'

