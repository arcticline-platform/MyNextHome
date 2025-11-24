#!/bin/bash

# ============================================================================
# Test Script for MyNextHome Database Setup Scripts
# ============================================================================

set -eu

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

test_pass() {
    echo -e "${GREEN}✓ PASS: $1${NC}"
    PASSED=$((PASSED + 1))
}

test_fail() {
    echo -e "${RED}✗ FAIL: $1${NC}"
    FAILED=$((FAILED + 1))
}

test_info() {
    echo -e "${BLUE}ℹ TEST: $1${NC}"
}

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Testing MyNextHome Database Scripts${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

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

# ============================================================================
# Test 1: Check if scripts are executable
# ============================================================================
test_info "Checking script permissions..."

if [ -x "$SCRIPT_DIR/setup_database.sh" ]; then
    test_pass "setup_database.sh is executable"
else
    test_fail "setup_database.sh is not executable"
fi

if [ -x "$SCRIPT_DIR/maintain_database.sh" ]; then
    test_pass "maintain_database.sh is executable"
else
    test_fail "maintain_database.sh is not executable"
fi

# ============================================================================
# Test 2: Validate SQL script syntax
# ============================================================================
test_info "Validating SQL script syntax..."

# Check if SQL file exists and is readable
if [ -f "$SCRIPT_DIR/create_db.sql" ]; then
    test_pass "create_db.sql exists and is readable"
    
    # Check for basic SQL syntax issues
    if grep -q "CREATE DATABASE" "$SCRIPT_DIR/create_db.sql"; then
        test_pass "SQL script contains CREATE DATABASE statement"
    else
        test_fail "SQL script missing CREATE DATABASE statement"
    fi
    
    if grep -q "CREATE EXTENSION.*postgis" "$SCRIPT_DIR/create_db.sql"; then
        test_pass "SQL script contains PostGIS extension creation"
    else
        test_fail "SQL script missing PostGIS extension creation"
    fi
else
    test_fail "create_db.sql does not exist"
fi

# ============================================================================
# Test 3: Test PostgreSQL connectivity
# ============================================================================
test_info "Testing PostgreSQL connectivity..."

if PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d postgres -c "SELECT 1;" &>/dev/null; then
    test_pass "PostgreSQL server is accessible"
else
    test_fail "Cannot connect to PostgreSQL server"
    echo -e "${RED}Tests cannot continue without database connection${NC}"
    exit 1
fi

# ============================================================================
# Test 4: Test PostGIS availability
# ============================================================================
test_info "Testing PostGIS availability..."

POSTGIS_AVAILABLE=$(PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d postgres -tAc "SELECT COUNT(*) FROM pg_available_extensions WHERE name = 'postgis';" 2>/dev/null || echo "0")
if [ "$POSTGIS_AVAILABLE" = "1" ]; then
    test_pass "PostGIS extension is available"
else
    test_fail "PostGIS extension is not available"
fi

# ============================================================================
# Test 5: Test database exists and has PostGIS
# ============================================================================
test_info "Testing database configuration..."

DB_EXISTS=$(PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$POSTGRES_DBNAME';" 2>/dev/null || echo "0")
if [ "$DB_EXISTS" = "1" ]; then
    test_pass "Database '$POSTGRES_DBNAME' exists"
    
    # Check PostGIS extension
    POSTGIS_ENABLED=$(PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" -tAc "SELECT COUNT(*) FROM pg_extension WHERE extname = 'postgis';" 2>/dev/null || echo "0")
    if [ "$POSTGIS_ENABLED" = "1" ]; then
        test_pass "PostGIS extension is enabled in database"
    else
        test_fail "PostGIS extension is not enabled in database"
    fi
    
    # Check helper functions
    if PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" -c "SELECT get_database_size();" &>/dev/null; then
        test_pass "Helper function get_database_size() exists"
    else
        test_fail "Helper function get_database_size() does not exist"
    fi
    
    if PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" -c "SELECT analyze_all_tables();" &>/dev/null; then
        test_pass "Helper function analyze_all_tables() exists"
    else
        test_fail "Helper function analyze_all_tables() does not exist"
    fi
else
    test_fail "Database '$POSTGRES_DBNAME' does not exist"
fi

# ============================================================================
# Test 6: Test maintenance script operations
# ============================================================================
test_info "Testing maintenance script operations..."

# Test show operation
if ./dev_ops/maintain_database.sh show &>/dev/null; then
    test_pass "Maintenance script 'show' operation works"
else
    test_fail "Maintenance script 'show' operation failed"
fi

# Test stats operation
if ./dev_ops/maintain_database.sh stats &>/dev/null; then
    test_pass "Maintenance script 'stats' operation works"
else
    test_fail "Maintenance script 'stats' operation failed"
fi

# Test bloat operation
if ./dev_ops/maintain_database.sh bloat &>/dev/null; then
    test_pass "Maintenance script 'bloat' operation works"
else
    test_fail "Maintenance script 'bloat' operation failed"
fi

# Test vacuum operation
if ./dev_ops/maintain_database.sh vacuum &>/dev/null; then
    test_pass "Maintenance script 'vacuum' operation works"
else
    test_fail "Maintenance script 'vacuum' operation failed"
fi

# ============================================================================
# Test 7: Test database settings
# ============================================================================
test_info "Testing database configuration settings..."

# Check if we can query settings
SETTINGS_COUNT=$(PGPASSWORD="$POSTGRES_PASS" psql -U "$POSTGRES_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$POSTGRES_DBNAME" -tAc "SELECT COUNT(*) FROM pg_settings WHERE name IN ('work_mem', 'maintenance_work_mem', 'effective_cache_size');" 2>/dev/null || echo "0")
if [ "$SETTINGS_COUNT" -ge "3" ]; then
    test_pass "Can query database settings"
else
    test_fail "Cannot query database settings"
fi

# ============================================================================
# Test 8: Test setup script validation
# ============================================================================
test_info "Testing setup script validation..."

# Test that setup script validates prerequisites
if echo "n" | ./dev_ops/setup_database.sh 2>&1 | grep -q "PostgreSQL server is accessible"; then
    test_pass "Setup script validates PostgreSQL connectivity"
else
    test_fail "Setup script does not validate PostgreSQL connectivity"
fi

if echo "n" | ./dev_ops/setup_database.sh 2>&1 | grep -q "PostGIS extension is available"; then
    test_pass "Setup script validates PostGIS availability"
else
    test_fail "Setup script does not validate PostGIS availability"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}Failed: $FAILED${NC}"
    echo ""
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi

