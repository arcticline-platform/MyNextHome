# DevOps Scripts

This folder contains scripts for setting up and managing the MyNextHome application infrastructure.

## Database Setup

### Files

- `create_db.sql` - SQL script to create the PostgreSQL database with PostGIS extensions and performance optimizations
- `setup_database.sh` - Robust shell script wrapper to execute the database setup
- `maintain_database.sh` - Database maintenance and optimization script

### Features

The database setup is optimized for:
- **Large queries** - Configured with increased work_mem, maintenance_work_mem, and effective_cache_size
- **Spatial operations** - PostGIS extensions with spatial query optimizations
- **High performance** - Parallel query execution, JIT compilation, and optimized planner settings
- **Production ready** - Connection limits, timeouts, logging, and monitoring
- **Feature databases** - Optimized for complex spatial queries and large datasets

### Usage

#### Option 1: Using the shell script (Recommended)

```bash
./dev_ops/setup_database.sh
```

The script will:
- Validate PostgreSQL server connectivity
- Check PostGIS availability
- Read database configuration from `.env` file
- Check if the database already exists (with safe handling)
- Create the database with optimized settings
- Enable PostGIS, PostGIS Topology, and PostGIS Raster extensions
- Configure performance parameters for large queries
- Set up monitoring and logging
- Verify the installation and display configuration

#### Option 2: Using the SQL script directly

```bash
PGPASSWORD=Admin psql -U postgres -h localhost -f dev_ops/create_db.sql
```

Replace `Admin` with your PostgreSQL password from the `.env` file.

### Database Optimizations Applied

#### Memory Settings
- `work_mem`: 256MB (for sorting and hash operations)
- `maintenance_work_mem`: 1GB (for VACUUM, CREATE INDEX)
- `effective_cache_size`: 4GB (query planner optimization)

#### Performance Settings
- `random_page_cost`: 1.1 (optimized for SSD storage)
- `max_parallel_workers_per_gather`: 4 (parallel query execution)
- `max_parallel_workers`: 8 (overall parallel operations)
- `jit`: enabled (Just-In-Time compilation for complex queries)

#### Connection & Timeout Settings
- `max_connections`: 100
- `statement_timeout`: 30 minutes (prevents runaway queries)
- `lock_timeout`: 10 minutes

#### Monitoring & Logging
- `log_min_duration_statement`: 1000ms (logs slow queries)
- `log_connections`: enabled
- `log_disconnections`: enabled
- `pg_stat_statements`: enabled (query performance tracking)

#### Spatial Optimizations
- PostGIS extensions with spatial indexing support
- Optimized query planner for geographic queries
- Helper functions for spatial operations

### Database Maintenance

Use the maintenance script to keep your database optimized:

```bash
./dev_ops/maintain_database.sh [operation]
```

Available operations:
- `vacuum` - Run VACUUM ANALYZE on all tables
- `reindex` - Reindex all indexes
- `stats` - Update table statistics
- `show` - Show database statistics and sizes
- `bloat` - Check for table bloat
- `all` - Run all maintenance operations

Examples:
```bash
# Interactive menu
./dev_ops/maintain_database.sh

# Run specific operation
./dev_ops/maintain_database.sh vacuum
./dev_ops/maintain_database.sh show
./dev_ops/maintain_database.sh all
```

### Requirements

- PostgreSQL 11+ server running
- PostGIS 3.0+ extension installed in PostgreSQL
- Database credentials configured in `.env` file:
  - `POSTGRES_USER`
  - `POSTGRES_PASS`
  - `POSTGRES_DBNAME`
  - `PG_HOST`
  - `PG_PORT`

### What gets created

- Database: `db_mynexthome` (or as specified in `.env`)
- PostGIS extension (with spatial types and functions)
- PostGIS Topology extension (for spatial relationships)
- PostGIS Raster extension (for raster data support)
- pg_stat_statements extension (for query performance monitoring)
- Helper functions for database management
- Optimized configuration for large queries and spatial operations

### Performance Tuning Notes

The default settings are optimized for a server with:
- 8GB+ RAM
- SSD storage
- Multiple CPU cores

For different server configurations, you may want to adjust:
- `work_mem`: Should be ~25% of RAM / max_connections
- `maintenance_work_mem`: Can be up to 2GB for large tables
- `effective_cache_size`: Should be 50-75% of total RAM
- `max_parallel_workers`: Should match CPU cores

### Large-Scale Deployments (1M+ Records)

For databases handling 1 million or more records, additional optimizations are recommended:

#### 1. Apply Large Dataset Optimizations

```bash
PGPASSWORD=Admin psql -U postgres -h localhost -d db_mynexthome -f dev_ops/optimize_for_large_datasets.sql
```

This will:
- Increase memory settings (work_mem to 512MB, maintenance_work_mem to 2GB)
- Optimize parallel query settings
- Create helper functions for large dataset management
- Set higher statistics targets

#### 2. Configure Server-Level Settings

Copy settings from `postgresql.conf.large_scale` to your PostgreSQL configuration:

```bash
# Edit postgresql.conf (location varies by OS)
sudo nano /etc/postgresql/14/main/postgresql.conf

# Or merge settings:
sudo cp dev_ops/postgresql.conf.large_scale /tmp/
# Then manually merge relevant settings into your postgresql.conf
```

Key settings for large datasets:
- `shared_buffers = 4GB` (adjust based on RAM)
- `effective_cache_size = 12GB` (50-75% of RAM)
- `max_parallel_workers = 16`
- `autovacuum_max_workers = 6`
- `autovacuum_vacuum_scale_factor = 0.05`

#### 3. Monitor Performance

Use the performance monitoring script:

```bash
./dev_ops/monitor_performance.sh
```

This displays:
- Database size and growth
- Largest tables and row counts
- Index usage statistics
- Connection statistics
- Cache hit ratios
- Slow queries
- Lock information
- Vacuum status

#### 4. Indexing Strategy for Large Tables

After running migrations, create additional indexes based on your query patterns:

```sql
-- Example indexes for property searches
CREATE INDEX idx_property_status_price ON accounts_property(status, price);
CREATE INDEX idx_property_type_bedrooms ON accounts_property(property_type_id, bedrooms);
CREATE INDEX idx_property_created_status ON accounts_property(created, status);

-- Spatial index for geographic queries
CREATE INDEX idx_address_location_gist ON accounts_address(location) USING GIST;

-- Partial index for active listings
CREATE INDEX idx_property_active ON accounts_property(status) WHERE status = 'published';
```

#### 5. Regular Maintenance for Large Datasets

Schedule regular maintenance:

```bash
# Weekly: Full maintenance
./dev_ops/maintain_database.sh all

# Daily: Update statistics for large tables
PGPASSWORD=Admin psql -U postgres -h localhost -d db_mynexthome -c "SELECT analyze_large_tables(500);"

# Monthly: Check for missing indexes
PGPASSWORD=Admin psql -U postgres -h localhost -d db_mynexthome -c "SELECT * FROM check_missing_fk_indexes();"
```

#### 6. Connection Pooling

For high-traffic applications, use connection pooling:

**Option A: PgBouncer (Recommended)**
```bash
# Install PgBouncer
sudo apt-get install pgbouncer

# Configure pool_mode = transaction
# Set pool_size based on your needs (typically 25-50% of max_connections)
```

**Option B: Django Connection Pooling**
```python
# In settings.py
DATABASES = {
    'default': {
        # ... existing config ...
        'CONN_MAX_AGE': 600,  # Reuse connections for 10 minutes
    }
}
```

#### 7. Table Partitioning (10M+ Records)

For very large tables (10M+ rows), consider partitioning:

```sql
-- Example: Partition properties by year
CREATE TABLE accounts_property_2024 PARTITION OF accounts_property
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### Performance Benchmarks

With the optimized configuration, the database can handle:
- ✅ **1M+ records** with good performance
- ✅ **10M+ records** with proper indexing and partitioning
- ✅ **100+ concurrent connections** with connection pooling
- ✅ **Complex spatial queries** on large datasets
- ✅ **High write throughput** with optimized autovacuum

### Troubleshooting

#### Connection Issues
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check credentials in `.env` file
- Verify network connectivity to database host

#### PostGIS Not Available
- Install PostGIS: `sudo apt-get install postgresql-postgis` (Ubuntu/Debian)
- Or: `sudo yum install postgis` (RHEL/CentOS)

#### Performance Issues
- Run maintenance: `./dev_ops/maintain_database.sh all`
- Check slow queries: Review logs or use `pg_stat_statements`
- Monitor database size and bloat: `./dev_ops/maintain_database.sh bloat`
- Run performance monitor: `./dev_ops/monitor_performance.sh`
- Review cache hit ratio (should be > 99%)
- Check for missing indexes: `SELECT * FROM check_missing_fk_indexes();`

#### Large Dataset Issues
- If queries are slow: Check indexes and run `ANALYZE`
- If database is growing too fast: Review autovacuum settings
- If connections are maxing out: Implement connection pooling
- If disk I/O is high: Increase `shared_buffers` and `effective_cache_size`

