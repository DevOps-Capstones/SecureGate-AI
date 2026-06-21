# Database

Sprint 1 uses PostgreSQL with an initial schema for projects, scans, and reports.

The migration in `migrations/001_initial_schema.sql` is mounted into the PostgreSQL container at startup through Docker Compose.

Connection defaults:

- Host: `localhost`
- Port: `5432`
- Database: `securegate`
- Username: `securegate`
- Password: `securegate_password`
