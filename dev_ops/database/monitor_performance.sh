#!/bin/bash

# ============================================================================
# Performance Monitoring Script for Large-Scale Database
# Monitors key metrics for databases with 1M+ records
# ============================================================================

set -eu

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        export "$line" 2>/dev/null || true
    done < "$PROJECT_ROOT/.env"
fi

POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASS=${POSTGRES_PASS:-}
POSTGRES_DBNAME=${POSTGRES_DBNAME:-db_mynexthome}
PG_HOST=${PG_HOST:-localhost}
PG_PORT=${PG_PORT:-5432}

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Database Performance Monitor${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# Function to display section header
section_header() {
    echo ""
    echo -e "${BLUE}--- $1 ---${NC}"
    echo ""
}

# 1. Database Size and Growth
section_header "Database Size and Growth"
PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" <<EOF
SELECT 
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname)) AS size,
    pg_size_pretty(pg_database_size(pg_database.datname) - 
        (SELECT pg_database_size(pg_database.datname) FROM pg_database WHERE datname = '$POSTGRES_DBNAME' 
         AND pg_database_size(pg_database.datname) > 0)) AS growth
FROM pg_database
WHERE datname = '$POSTGRES_DBNAME';
EOF

# 2. Table Statistics
section_header "Top 10 Largest Tables"
PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" <<EOF
SELECT 
    schemaname || '.' || relname AS table_name,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||relname)) AS table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||relname)) AS indexes_size,
    n_live_tup AS row_count,
    n_dead_tup AS dead_rows,
    CASE 
        WHEN n_live_tup > 0 THEN ROUND((n_dead_tup::numeric / n_live_tup::numeric) * 100, 2)
        ELSE 0
    END AS dead_row_percent
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||relname) DESC
LIMIT 10;
EOF

# 3. Index Statistics
section_header "Index Usage Statistics"
PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" <<EOF
SELECT 
    schemaname || '.' || relname AS table_name,
    indexrelname AS index_name,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan AS times_used,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    CASE 
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_scan < 100 THEN 'LOW USE'
        ELSE 'ACTIVE'
    END AS usage_status
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 15;
EOF

# 4. Connection Statistics
section_header "Connection Statistics"
PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" <<EOF
SELECT 
    count(*) AS total_connections,
    count(*) FILTER (WHERE state = 'active') AS active_connections,
    count(*) FILTER (WHERE state = 'idle') AS idle_connections,
    count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_transaction,
    count(*) FILTER (WHERE wait_event_type IS NOT NULL) AS waiting_connections
FROM pg_stat_activity
WHERE datname = '$POSTGRES_DBNAME';
EOF

# 5. Cache Hit Ratio
section_header "Cache Hit Ratio (Should be > 99%)"
PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" <<EOF
SELECT 
    'heap' AS type,
    sum(heap_blks_read) AS disk_reads,
    sum(heap_blks_hit) AS cache_hits,
    CASE 
        WHEN sum(heap_blks_hit) + sum(heap_blks_read) > 0 THEN
            ROUND(100.0 * sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)), 2)
        ELSE 0
    END AS cache_hit_ratio
FROM pg_statio_user_tables
UNION ALL
SELECT 
    'index' AS type,
    sum(idx_blks_read) AS disk_reads,
    sum(idx_blks_hit) AS cache_hits,
    CASE 
        WHEN sum(idx_blks_hit) + sum(idx_blks_read) > 0 THEN
            ROUND(100.0 * sum(idx_blks_hit) / (sum(idx_blks_hit) + sum(idx_blks_read)), 2)
        ELSE 0
    END AS cache_hit_ratio
FROM pg_statio_user_indexes;
EOF

# 6. Slow Queries (if pg_stat_statements is enabled)
section_header "Top 10 Slowest Queries"
PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" <<EOF
SELECT 
    LEFT(query, 100) AS query_preview,
    calls,
    ROUND(total_exec_time::numeric, 2) AS total_time_ms,
    ROUND(mean_exec_time::numeric, 2) AS avg_time_ms,
    ROUND(max_exec_time::numeric, 2) AS max_time_ms,
    ROUND((100 * total_exec_time / sum(total_exec_time) OVER ())::numeric, 2) AS percent_total_time
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY mean_exec_time DESC
LIMIT 10;
EOF

# 7. Lock Information
section_header "Current Locks"
PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" <<EOF
SELECT 
    locktype,
    mode,
    COUNT(*) AS lock_count
FROM pg_locks
WHERE database = (SELECT oid FROM pg_database WHERE datname = '$POSTGRES_DBNAME')
GROUP BY locktype, mode
ORDER BY lock_count DESC;
EOF

# 8. Vacuum Status
section_header "Autovacuum Status"
PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" <<EOF
SELECT 
    schemaname || '.' || relname AS table_name,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    CASE 
        WHEN last_autoanalyze IS NULL THEN 'NEVER ANALYZED'
        WHEN last_autoanalyze < NOW() - INTERVAL '7 days' THEN 'STALE'
        ELSE 'OK'
    END AS analyze_status
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY last_autoanalyze NULLS FIRST
LIMIT 10;
EOF

echo ""
echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}Monitoring Complete${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""
echo -e "${BLUE}Recommendations:${NC}"
echo "  - Cache hit ratio should be > 99%"
echo "  - Dead row percentage should be < 10%"
echo "  - Unused indexes should be reviewed and potentially removed"
echo "  - Tables with stale statistics should be analyzed"
echo "  - Monitor slow queries and optimize as needed"
echo ""

