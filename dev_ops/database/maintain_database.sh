#!/bin/bash

# ============================================================================
# MyNextHome Database Maintenance Script
# Performs maintenance tasks for optimal database performance
# ============================================================================

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

error_exit() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

success_msg() {
    echo -e "${GREEN}✓ $1${NC}"
}

info_msg() {
    echo -e "${BLUE}ℹ $1${NC}"
}

warning_msg() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    # Safely load environment variables, handling comments and empty lines
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        # Export the variable
        export "$line" 2>/dev/null || true
    done < "$PROJECT_ROOT/.env"
fi

POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASS=${POSTGRES_PASS:-}
POSTGRES_DBNAME=${POSTGRES_DBNAME:-db_mynexthome}
PG_HOST=${PG_HOST:-localhost}
PG_PORT=${PG_PORT:-5432}

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Database Maintenance${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# Function to run VACUUM ANALYZE
vacuum_analyze() {
    info_msg "Running VACUUM ANALYZE on all tables..."
    PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" <<EOF
SELECT 'VACUUM ANALYZE ' || quote_ident(schemaname) || '.' || quote_ident(tablename) || ';'
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
\gexec
EOF
    success_msg "VACUUM ANALYZE completed"
}

# Function to reindex database
reindex_database() {
    info_msg "Reindexing database..."
    PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" -c "REINDEX DATABASE $POSTGRES_DBNAME;"
    success_msg "Reindexing completed"
}

# Function to update statistics
update_statistics() {
    info_msg "Updating table statistics..."
    PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" -c "SELECT analyze_all_tables();"
    success_msg "Statistics updated"
}

# Function to show database statistics
show_statistics() {
    info_msg "Database Statistics:"
    echo ""
    PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" <<EOF
-- Database size
SELECT 
    'Database Size' as metric,
    pg_size_pretty(pg_database_size('$POSTGRES_DBNAME')) as value;

-- Table sizes
SELECT 
    schemaname || '.' || tablename as table_name,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;

-- Index usage statistics
SELECT 
    schemaname || '.' || indexrelname as index_name,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC
LIMIT 10;

-- Slow query statistics (if pg_stat_statements is enabled)
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 5;
EOF
}

# Function to check for bloat
check_bloat() {
    info_msg "Checking for table bloat..."
    PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" <<EOF
SELECT 
    schemaname || '.' || relname as table_name,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||relname)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname) - pg_relation_size(schemaname||'.'||relname)) as indexes_size,
    n_dead_tup as dead_tuples,
    n_live_tup as live_tuples,
    CASE 
        WHEN n_live_tup > 0 THEN ROUND((n_dead_tup::numeric / n_live_tup::numeric) * 100, 2)
        ELSE 0
    END as dead_tuple_percent
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY dead_tuple_percent DESC
LIMIT 10;
EOF
}

# Main menu
if [ $# -eq 0 ]; then
    echo "Available maintenance operations:"
    echo "  1) vacuum    - Run VACUUM ANALYZE on all tables"
    echo "  2) reindex   - Reindex all indexes"
    echo "  3) stats     - Update table statistics"
    echo "  4) show      - Show database statistics"
    echo "  5) bloat     - Check for table bloat"
    echo "  6) all       - Run all maintenance operations"
    echo ""
    read -p "Select operation (1-6): " choice
    
    case $choice in
        1) vacuum_analyze ;;
        2) reindex_database ;;
        3) update_statistics ;;
        4) show_statistics ;;
        5) check_bloat ;;
        6) 
            vacuum_analyze
            update_statistics
            show_statistics
            check_bloat
            ;;
        *) error_exit "Invalid choice" ;;
    esac
else
    case "$1" in
        vacuum) vacuum_analyze ;;
        reindex) reindex_database ;;
        stats) update_statistics ;;
        show) show_statistics ;;
        bloat) check_bloat ;;
        all)
            vacuum_analyze
            update_statistics
            show_statistics
            check_bloat
            ;;
        *) error_exit "Invalid operation. Use: vacuum, reindex, stats, show, bloat, or all" ;;
    esac
fi

echo ""
success_msg "Maintenance completed!"

