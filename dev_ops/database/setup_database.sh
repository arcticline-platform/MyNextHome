#!/bin/bash

# ============================================================================
# MyNextHome Database Setup Script
# Creates PostgreSQL database with PostGIS and optimizations for large queries
# ============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Error handling function
error_exit() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

# Success message function
success_msg() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Warning message function
warning_msg() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Info message function
info_msg() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ============================================================================
# Load Environment Variables
# ============================================================================
if [ -f "$PROJECT_ROOT/.env" ]; then
    # Safely load environment variables, handling comments and empty lines
    # Use a safer method that handles special characters
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        # Export the variable
        export "$line" 2>/dev/null || true
    done < "$PROJECT_ROOT/.env"
    success_msg "Loaded environment variables from .env file"
else
    warning_msg ".env file not found. Using default values."
    POSTGRES_USER=${POSTGRES_USER:-postgres}
    POSTGRES_PASS=${POSTGRES_PASS:-}
    POSTGRES_DBNAME=${POSTGRES_DBNAME:-db_mynexthome}
    PG_HOST=${PG_HOST:-localhost}
    PG_PORT=${PG_PORT:-5432}
fi

# Set defaults if not provided
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASS=${POSTGRES_PASS:-}
POSTGRES_DBNAME=${POSTGRES_DBNAME:-db_mynexthome}
PG_HOST=${PG_HOST:-localhost}
PG_PORT=${PG_PORT:-5432}

# ============================================================================
# Validate Prerequisites
# ============================================================================
echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}MyNextHome Database Setup${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    error_exit "psql is not installed. Please install PostgreSQL client."
fi

# Check if PostgreSQL server is accessible
info_msg "Checking PostgreSQL server connection..."
if ! PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d postgres -c "SELECT version();" &>/dev/null; then
    error_exit "Cannot connect to PostgreSQL server. Please check your credentials and server status."
fi
success_msg "PostgreSQL server is accessible"

# Check if PostGIS is available
info_msg "Checking PostGIS availability..."
POSTGIS_AVAILABLE=$(PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d postgres -tAc "SELECT COUNT(*) FROM pg_available_extensions WHERE name = 'postgis';" 2>/dev/null || echo "0")
if [ "$POSTGIS_AVAILABLE" != "1" ]; then
    error_exit "PostGIS extension is not available. Please install PostGIS on your PostgreSQL server."
fi
success_msg "PostGIS extension is available"

# Display configuration
echo ""
info_msg "Configuration:"
echo "  Database: $POSTGRES_DBNAME"
echo "  User: $POSTGRES_USER"
echo "  Host: $PG_HOST"
echo "  Port: $PG_PORT"
echo ""

# ============================================================================
# Check Existing Database
# ============================================================================
DB_EXISTS=$(PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$POSTGRES_DBNAME';" 2>/dev/null || echo "0")

if [ "$DB_EXISTS" = "1" ]; then
    warning_msg "Database '$POSTGRES_DBNAME' already exists."
    
    # Check if running in non-interactive mode
    if [ -t 0 ]; then
        read -p "Do you want to recreate it? This will DELETE all data! (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            info_msg "Dropping existing database..."
            
            # Terminate all connections to the database
            PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d postgres <<EOF
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$POSTGRES_DBNAME'
  AND pid <> pg_backend_pid();
EOF
            
            # Drop the database
            if ! PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DBNAME;" 2>/dev/null; then
                error_exit "Failed to drop existing database. Please check for active connections."
            fi
            success_msg "Existing database dropped"
        else
            info_msg "Skipping database creation. Using existing database."
            
            # Check if PostGIS is enabled on existing database
            POSTGIS_ENABLED=$(PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" -tAc "SELECT COUNT(*) FROM pg_extension WHERE extname = 'postgis';" 2>/dev/null || echo "0")
            if [ "$POSTGIS_ENABLED" != "1" ]; then
                warning_msg "PostGIS is not enabled on existing database. Enabling now..."
                PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" -c "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS postgis_topology;" || error_exit "Failed to enable PostGIS"
                success_msg "PostGIS enabled on existing database"
            fi
            exit 0
        fi
    else
        warning_msg "Running in non-interactive mode. Skipping database recreation."
        exit 0
    fi
fi

# ============================================================================
# Create Database and Run Setup
# ============================================================================
info_msg "Creating database and applying optimizations..."
echo ""

# Run the SQL script with error handling
if ! PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -f "$SCRIPT_DIR/create_db.sql" 2>&1; then
    error_exit "Database setup failed. Check the error messages above."
fi

echo ""
success_msg "Database setup completed successfully!"
echo ""

# ============================================================================
# Verification
# ============================================================================
info_msg "Verifying installation..."

# Verify PostGIS
POSTGIS_VERSION=$(PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" -tAc "SELECT PostGIS_version();" 2>/dev/null || echo "")
if [ -n "$POSTGIS_VERSION" ]; then
    success_msg "PostGIS version: $POSTGIS_VERSION"
else
    warning_msg "Could not verify PostGIS version"
fi

# Display installed extensions
echo ""
info_msg "Installed extensions:"
PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" -c "\dx" || warning_msg "Could not list extensions"

# Display database size
echo ""
info_msg "Database size:"
PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" -tAc "SELECT pg_size_pretty(pg_database_size('$POSTGRES_DBNAME'));" || warning_msg "Could not get database size"

# Display key configuration settings
echo ""
info_msg "Key database settings:"
PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" <<EOF
SELECT 
    name,
    setting || COALESCE(' ' || unit, '') as value,
    context
FROM pg_settings
WHERE name IN (
    'work_mem',
    'maintenance_work_mem',
    'effective_cache_size',
    'max_connections',
    'statement_timeout',
    'random_page_cost'
)
ORDER BY name;
EOF

echo ""
echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""
info_msg "Next steps:"
echo "  1. Run Django migrations: python manage.py migrate"
echo "  2. Create a superuser: python manage.py createsuperuser"
echo "  3. Collect static files: python manage.py collectstatic"
echo ""

