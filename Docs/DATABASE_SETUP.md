# Database Setup Guide

This document provides comprehensive information about the database setup for the UEM Placement Preparation Platform.

## Overview

The platform uses SQLAlchemy ORM with Flask-Migrate for database management. It supports both SQLite (development) and PostgreSQL (production) databases.

## Database Models

### 1. User Model
- **Purpose**: Stores UEM student information and authentication data
- **Key Features**:
  - UEM email validation (@uem.edu.in domain)
  - Secure password hashing using Werkzeug
  - Admin role support
  - Relationship with test attempts and progress metrics

### 2. Test Model
- **Purpose**: Stores company-specific placement test templates
- **Key Features**:
  - Company and year indexing for fast retrieval
  - JSON pattern data storage for test configuration
  - Relationship with questions and test attempts

### 3. Question Model
- **Purpose**: Stores individual questions for each test
- **Key Features**:
  - Section-based organization (Aptitude, Reasoning, etc.)
  - JSON options storage for multiple choice questions
  - Difficulty and topic indexing for analytics
  - Support for explanations

### 4. TestAttempt Model
- **Purpose**: Tracks user test submissions and results
- **Key Features**:
  - Score and timing tracking
  - JSON answers storage
  - Performance indexing for leaderboards
  - Completion status tracking

### 5. ProgressMetrics Model
- **Purpose**: Stores user performance analytics by subject area
- **Key Features**:
  - Subject-wise accuracy tracking
  - Unique constraint per user-subject combination
  - Automatic metric updates

## Database Schema

```sql
-- Core tables with relationships
users (id, email, password_hash, name, year, branch, created_at, is_admin)
tests (id, company, year, pattern_data, created_at)
questions (id, test_id, section, question_text, options, correct_answer, explanation, difficulty, topic)
test_attempts (id, user_id, test_id, score, total_questions, time_taken, answers, started_at, completed_at)
progress_metrics (id, user_id, subject_area, accuracy_rate, total_attempts, last_updated)
```

## Indexes for Performance

### Primary Indexes
- `ix_users_email` - Unique index for fast user lookup
- `ix_tests_company` - Fast company-based test retrieval
- `ix_questions_test_id` - Efficient question loading per test
- `ix_test_attempts_user_id` - User performance history
- `ix_progress_metrics_user_id` - User analytics lookup

### Performance Indexes
- `ix_tests_year` - Year-based filtering
- `ix_tests_created_at` - Chronological sorting
- `ix_questions_section` - Section-based queries
- `ix_questions_difficulty` - Difficulty filtering
- `ix_questions_topic` - Topic-based analytics
- `ix_test_attempts_score` - Leaderboard calculations
- `ix_test_attempts_started_at` - Time-based queries
- `ix_test_attempts_completed_at` - Completion tracking

## Setup Instructions

### Development Setup (SQLite)

1. **Initialize the database**:
   ```bash
   python init_db.py
   ```

2. **Run migrations**:
   ```bash
   flask db upgrade
   ```

3. **Validate setup**:
   ```bash
   python validate_db.py
   ```

### Production Setup (PostgreSQL)

1. **Set environment variables**:
   ```bash
   export FLASK_ENV=production
   export DATABASE_URL=postgresql://user:password@host:port/database
   ```

2. **Initialize database**:
   ```bash
   python init_db.py
   ```

3. **Apply PostgreSQL optimizations**:
   ```bash
   psql -d your_database -f migrations/postgresql_setup.sql
   ```

4. **Run migrations**:
   ```bash
   flask db upgrade
   ```

## Migration Management

### Creating New Migrations
```bash
flask db migrate -m "Description of changes"
flask db upgrade
```

### Rolling Back Migrations
```bash
flask db downgrade
```

### Checking Migration Status
```bash
flask db current
flask db history
```

## PostgreSQL Production Features

### Advanced Constraints
- UEM email domain validation
- Score range validation (0 to total_questions)
- Positive time validation
- Completion order validation (completed_at >= started_at)
- Accuracy rate validation (0-100%)

### Performance Functions
- `calculate_user_stats(user_id)` - Comprehensive user statistics
- `get_leaderboard(limit)` - Ranked user performance
- `refresh_analytics_summary()` - Update materialized views

### Data Retention
- `cleanup_old_test_attempts(days)` - Remove old test data
- Configurable retention policies

### Analytics Views
- `analytics_summary` - Materialized view for dashboard analytics
- Automatic refresh capabilities
- Indexed for fast querying

## Validation and Testing

### Database Validation Script
The `validate_db.py` script performs comprehensive validation:
- Table existence and structure
- Index presence and configuration
- Foreign key relationships
- Model method functionality
- Database connectivity
- Sample query execution

### Running Validation
```bash
python validate_db.py
```

Expected output: All validations should pass with green checkmarks.

## Security Considerations

### Data Protection
- Password hashing using Werkzeug's secure methods
- SQL injection prevention through SQLAlchemy ORM
- Input validation at model level
- Secure session management

### Access Control
- UEM email domain restriction
- Admin role separation
- User data isolation
- Audit trail for admin actions

## Performance Optimization

### Query Optimization
- Strategic indexing for common queries
- Composite indexes for multi-column searches
- Partial indexes for filtered queries
- Full-text search capabilities (PostgreSQL)

### Caching Strategy
- Model-level caching for frequently accessed data
- Query result caching for analytics
- Session-based caching for user data

### Monitoring
- Query performance tracking
- Index usage analysis
- Connection pool monitoring
- Error rate tracking

## Backup and Recovery

### Development
- SQLite database files are automatically backed up
- Migration scripts provide schema versioning

### Production
- Regular PostgreSQL backups recommended
- Point-in-time recovery capabilities
- Migration rollback procedures
- Data export/import utilities

## Troubleshooting

### Common Issues

1. **Migration Conflicts**:
   ```bash
   flask db stamp head  # Mark current state
   flask db migrate     # Create new migration
   ```

2. **Index Creation Failures**:
   - Check for existing data conflicts
   - Verify column data types
   - Review constraint violations

3. **Performance Issues**:
   - Analyze query execution plans
   - Check index usage
   - Review connection pool settings

### Debug Commands
```bash
# Check database connection
python -c "from app import app, db; app.app_context().push(); print(db.engine.execute('SELECT 1').scalar())"

# Inspect table structure
python -c "from sqlalchemy import inspect; from app import app, db; app.app_context().push(); print(inspect(db.engine).get_table_names())"

# Check migration status
flask db current
```

## Environment Configuration

### Development (.env)
```
FLASK_ENV=development
DATABASE_URL=sqlite:///uem_placement_dev.db
```

### Production (.env)
```
FLASK_ENV=production
DATABASE_URL=postgresql://user:password@host:port/database
SECRET_KEY=your-secret-key
```

## Best Practices

1. **Always run migrations in order**
2. **Test migrations on development first**
3. **Backup before major schema changes**
4. **Use transactions for data modifications**
5. **Monitor query performance regularly**
6. **Keep migration files in version control**
7. **Document schema changes thoroughly**

## Support

For database-related issues:
1. Check the validation script output
2. Review migration logs
3. Verify environment configuration
4. Test with sample data
5. Consult the troubleshooting section

The database setup is designed to be robust, scalable, and maintainable for the UEM Placement Preparation Platform's requirements.