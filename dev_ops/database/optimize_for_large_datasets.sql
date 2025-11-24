-- ============================================================================
-- Optimization Script for Large Datasets (1M+ records)
-- Run this after initial database setup to optimize for large-scale data
-- ============================================================================

-- Connect to the database
\c db_mynexthome

-- ============================================================================
-- Enhanced Memory Settings for Large Datasets
-- ============================================================================

-- Increase work_mem for large sorting and hash operations
-- For 1M+ records, we need more memory per operation
ALTER DATABASE db_mynexthome SET work_mem = '512MB';

-- Increase maintenance_work_mem for large VACUUM and index operations
ALTER DATABASE db_mynexthome SET maintenance_work_mem = '2GB';

-- Increase effective_cache_size (adjust based on your server RAM)
-- For servers with 16GB+ RAM, use 8-12GB
ALTER DATABASE db_mynexthome SET effective_cache_size = '8GB';

-- ============================================================================
-- Parallel Query Settings for Large Tables
-- ============================================================================

-- Increase parallel workers for large table scans
ALTER DATABASE db_mynexthome SET max_parallel_workers_per_gather = 8;
ALTER DATABASE db_mynexthome SET max_parallel_workers = 16;

-- Set minimum parallel table scan size (tables larger than this will use parallel workers)
ALTER DATABASE db_mynexthome SET min_parallel_table_scan_size = '8MB';

-- Set minimum parallel index scan size
ALTER DATABASE db_mynexthome SET min_parallel_index_scan_size = '512kB';

-- ============================================================================
-- Autovacuum Settings for Large Tables
-- ============================================================================

-- These are server-level settings, but documented here for reference
-- Add to postgresql.conf:
-- autovacuum_max_workers = 6
-- autovacuum_naptime = 10s
-- autovacuum_vacuum_scale_factor = 0.05  (vacuum when 5% of table changes)
-- autovacuum_analyze_scale_factor = 0.02  (analyze when 2% of table changes)
-- autovacuum_vacuum_cost_delay = 10ms
-- autovacuum_vacuum_cost_limit = 2000

-- ============================================================================
-- Query Planner Optimizations
-- ============================================================================

-- Increase statistics target for better query planning on large tables
-- This will be set per-table, but we set a higher default
ALTER DATABASE db_mynexthome SET default_statistics_target = 500;

-- ============================================================================
-- Connection and Lock Settings
-- ============================================================================

-- Increase max_locks_per_transaction for large bulk operations
-- Note: This is server-level, add to postgresql.conf: max_locks_per_transaction = 256

-- ============================================================================
-- Create Indexes for Common Large-Scale Queries
-- ============================================================================

-- Note: These are examples. Adjust based on your actual query patterns.
-- Run these after your Django migrations create the tables.

-- Composite indexes for common property search patterns
-- CREATE INDEX IF NOT EXISTS idx_property_status_price ON accounts_property(status, price);
-- CREATE INDEX IF NOT EXISTS idx_property_type_bedrooms ON accounts_property(property_type_id, bedrooms);
-- CREATE INDEX IF NOT EXISTS idx_property_created_status ON accounts_property(created, status);

-- Spatial indexes (GIST) for geographic queries (PostGIS)
-- CREATE INDEX IF NOT EXISTS idx_address_location_gist ON accounts_address(location) USING GIST;

-- Partial indexes for active/filtered data
-- CREATE INDEX IF NOT EXISTS idx_property_active ON accounts_property(status) WHERE status = 'published';

-- ============================================================================
-- Helper Functions for Large Dataset Management
-- ============================================================================

-- Function to get table sizes and row counts
CREATE OR REPLACE FUNCTION get_table_statistics()
RETURNS TABLE(
    schema_name text,
    table_name text,
    row_count bigint,
    total_size text,
    table_size text,
    indexes_size text,
    bloat_estimate text
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        schemaname::text,
        relname::text,
        n_live_tup::bigint,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname))::text,
        pg_size_pretty(pg_relation_size(schemaname||'.'||relname))::text,
        pg_size_pretty(pg_indexes_size(schemaname||'.'||relname))::text,
        CASE 
            WHEN n_live_tup > 0 THEN 
                ROUND((n_dead_tup::numeric / n_live_tup::numeric) * 100, 2)::text || '%'
            ELSE '0%'
        END as bloat_estimate
    FROM pg_stat_user_tables
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||relname) DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to analyze large tables with higher statistics
CREATE OR REPLACE FUNCTION analyze_large_tables(target_statistics int DEFAULT 500)
RETURNS void AS $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT schemaname, tablename 
        FROM pg_stat_user_tables 
        WHERE schemaname = 'public'
        AND n_live_tup > 10000  -- Only analyze tables with significant data
        ORDER BY n_live_tup DESC
    ) LOOP
        EXECUTE format('ALTER TABLE %I.%I SET (statistics_target = %s)', 
                      r.schemaname, r.tablename, target_statistics);
        EXECUTE format('ANALYZE %I.%I', r.schemaname, r.tablename);
        RAISE NOTICE 'Analyzed table: %.%', r.schemaname, r.tablename;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to check for missing indexes on foreign keys
CREATE OR REPLACE FUNCTION check_missing_fk_indexes()
RETURNS TABLE(
    table_name text,
    column_name text,
    constraint_name text
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tc.table_name::text,
        kcu.column_name::text,
        tc.constraint_name::text
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu 
        ON tc.constraint_name = kcu.constraint_name
    LEFT JOIN pg_indexes pi 
        ON pi.tablename = tc.table_name 
        AND pi.indexdef LIKE '%' || kcu.column_name || '%'
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'public'
        AND pi.indexname IS NULL;
END;
$$ LANGUAGE plpgsql;

-- Function to estimate index bloat
CREATE OR REPLACE FUNCTION get_index_bloat()
RETURNS TABLE(
    schemaname text,
    tablename text,
    indexname text,
    index_size text,
    bloat_ratio numeric
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        schemaname::text,
        tablename::text,
        indexrelname::text,
        pg_size_pretty(pg_relation_size(indexrelid))::text,
        CASE 
            WHEN idx_scan = 0 THEN 100.0
            ELSE ROUND((idx_scan::numeric / (idx_scan + idx_tup_read + idx_tup_fetch)::numeric) * 100, 2)
        END as bloat_ratio
    FROM pg_stat_user_indexes
    WHERE schemaname = 'public'
    ORDER BY pg_relation_size(indexrelid) DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Create Materialized View for Common Aggregations (Optional)
-- ============================================================================

-- Example: Property statistics by type (refresh periodically)
-- CREATE MATERIALIZED VIEW IF NOT EXISTS property_stats_by_type AS
-- SELECT 
--     property_type_id,
--     COUNT(*) as total_properties,
--     AVG(price) as avg_price,
--     MIN(price) as min_price,
--     MAX(price) as max_price,
--     COUNT(*) FILTER (WHERE status = 'published') as published_count
-- FROM accounts_property
-- GROUP BY property_type_id;
-- 
-- CREATE UNIQUE INDEX ON property_stats_by_type(property_type_id);
-- 
-- -- Refresh function
-- CREATE OR REPLACE FUNCTION refresh_property_stats()
-- RETURNS void AS $$
-- BEGIN
--     REFRESH MATERIALIZED VIEW CONCURRENTLY property_stats_by_type;
-- END;
-- $$ LANGUAGE plpgsql;

-- ============================================================================
-- Verification
-- ============================================================================

SELECT 'Large dataset optimizations applied successfully!' as status;
SELECT * FROM get_table_statistics() LIMIT 5;

\echo ''
\echo '============================================================================'
\echo 'Large Dataset Optimizations Applied'
\echo '============================================================================'
\echo 'Next steps:'
\echo '1. Review and create indexes based on your query patterns'
\echo '2. Set server-level settings in postgresql.conf (see postgresql.conf.template)'
\echo '3. Run analyze_large_tables() after loading significant data'
\echo '4. Monitor with get_table_statistics() and get_index_bloat()'
\echo '============================================================================'

