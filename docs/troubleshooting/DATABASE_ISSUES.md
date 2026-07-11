# Database Troubleshooting Guide

Common database-related issues and their solutions.

## Database Connection Errors

### Symptoms
- `Database connection failed`
- `SQLite error`
- `database is locked`
- Server won't start

### Solutions

1. **Run database diagnostic:**
   - Use web interface: Run `check_database` script
   - Verifies database connectivity
   - Checks database integrity

2. **Check database file permissions:**
   ```bash
   ls -la streamtv.db
   chmod 644 streamtv.db  # If needed
   ```

3. **Check if database is locked:**
   ```bash
   # macOS/Linux
   lsof streamtv.db
   ```
   If locked, stop all StreamTV processes and try again.

4. **Verify database location:**
   - Check `config.yaml` for database path
   - Default: `sqlite:///./streamtv.db`
   - Ensure directory is writable

5. **Test database connection:**
   ```bash
   python3 -c "from streamtv.database.session import SessionLocal; db = SessionLocal(); print('OK'); db.close()"
   ```

## Database Corruption

### Symptoms
- `database disk image is malformed`
- Inconsistent data
- Queries fail unexpectedly
- Data appears corrupted

### Solutions

1. **Backup current database:**
   ```bash
   cp streamtv.db streamtv.db.backup
   ```

2. **Run repair script:**
   - Use web interface: Run `repair_database` script
   - Attempts to repair corrupted database
   - May recover some data

3. **If repair fails:**
   ```bash
   # Restore from backup
   cp streamtv.db.backup streamtv.db
   
   # OR recreate database
   rm streamtv.db
   python3 -c "from streamtv.database.session import init_db; init_db()"
   ```

4. **Re-import data:**
   - After recreating, re-import channels
   - Re-import media items
   - Recreate schedules

## Database Locked Errors

### Symptoms
- `database is locked`
- Multiple processes accessing database
- Timeout errors

### Solutions

1. **Check for multiple processes:**
   ```bash
   ps aux | grep streamtv
   ```
   Ensure only one instance is running.

2. **Stop all StreamTV processes:**
   ```bash
   pkill -f streamtv.main
   ```

3. **Check for file locks:**
   ```bash
   lsof streamtv.db
   ```
   Kill any processes holding locks.

4. **Wait and retry:**
   - SQLite locks are usually temporary
   - Wait a few seconds and retry
   - Check if operation completes

5. **Increase timeout:**
   - SQLite has default timeout
   - May need to increase in code
   - Check for long-running queries

## Database Performance Issues

### Symptoms
- Slow queries
- High database file size
- Slow web interface

### Solutions

1. **Check database size:**
   ```bash
   ls -lh streamtv.db
   ```
   Large databases may be slow.

2. **Optimize database:**
   ```bash
   sqlite3 streamtv.db "VACUUM;"
   ```
   Rebuilds database and reclaims space.

3. **Check for missing indexes:**
   - Database should have indexes on common queries
   - Check query performance
   - Add indexes if needed (advanced)

4. **Clear old data:**
   - Remove old log entries if stored in database
   - Clean up unused media items
   - Archive old channels if needed

5. **Monitor database activity:**
   - Check for long-running queries
   - Look for query patterns in logs
   - Optimize frequent queries

## Database Migration Issues

### Symptoms
- Migration errors
- Schema version mismatches
- Upgrade failures

### Solutions

1. **Check database version:**
   ```bash
   sqlite3 streamtv.db "SELECT * FROM alembic_version;"
   ```

2. **Run migrations manually:**
   ```bash
   alembic upgrade head
   ```

3. **Backup before migration:**
   ```bash
   cp streamtv.db streamtv.db.pre-migration
   ```

4. **If migration fails:**
   - Restore from backup
   - Check migration logs
   - May need to recreate database

## Database Initialization Issues

### Symptoms
- Database not created on first run
- Initialization fails
- Missing tables

### Solutions

1. **Initialize manually:**
   ```bash
   python3 -c "from streamtv.database.session import init_db; init_db()"
   ```

2. **Check directory permissions:**
   ```bash
   ls -la .
   ```
   Ensure directory is writable.

3. **Verify database path:**
   - Check `config.yaml` for database URL
   - Ensure path is valid
   - Check disk space

4. **Check for existing database:**
   ```bash
   ls -la streamtv.db
   ```
   If exists but corrupted, remove and recreate.

## Database Backup and Recovery

### Backup Database

1. **Manual backup:**
   ```bash
   cp streamtv.db streamtv.db.backup
   ```

2. **Regular backups:**
   - Set up automated backups
   - Backup before major changes
   - Keep multiple backup versions

3. **Backup location:**
   - Store backups outside application directory
   - Use versioned backups (date-based)
   - Test restore procedure

### Restore Database

1. **Stop server:**
   ```bash
   pkill -f streamtv.main
   ```

2. **Restore backup:**
   ```bash
   cp streamtv.db.backup streamtv.db
   ```

3. **Verify restore:**
   ```bash
   python3 -c "from streamtv.database.session import SessionLocal; db = SessionLocal(); print('OK'); db.close()"
   ```

4. **Start server:**
   ```bash
   ./start_server.sh
   ```

## Database Maintenance

### Regular Maintenance

1. **Vacuum database:**
   ```bash
   sqlite3 streamtv.db "VACUUM;"
   ```
   Rebuilds database and reclaims space.

2. **Analyze database:**
   ```bash
   sqlite3 streamtv.db "ANALYZE;"
   ```
   Updates query optimizer statistics.

3. **Check integrity:**
   ```bash
   sqlite3 streamtv.db "PRAGMA integrity_check;"
   ```
   Verifies database integrity.

4. **Clear cache:**
   - Use web interface: Run `clear_cache` script
   - Clears application cache
   - May help with performance

## Getting Help

If database issues persist:

1. **Collect information:**
   - Database file size
   - Error messages
   - Database version
   - Recent changes

2. **Run diagnostics:**
   - Use `check_database` script
   - Run integrity check
   - Check database logs

3. **Backup before troubleshooting:**
   - Always backup before major changes
   - Keep backup until issue resolved
   - Test restore procedure

4. **Check documentation:**
   - [Main Troubleshooting Guide](../TROUBLESHOOTING.md)
   - [Troubleshooting Scripts](TROUBLESHOOTING_SCRIPTS.md)
   - [Installation Issues](INSTALLATION_ISSUES.md)

See also:
- SQLite documentation: https://www.sqlite.org/docs.html
- Database schema information in codebase
