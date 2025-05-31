#!/bin/bash
set -e

echo "Setting up PostgreSQL for Django project..."

# PostgreSQL commands
psql -U postgres << SQL
CREATE USER muadhin_user WITH PASSWORD 'SuperSecurePeewee23!';
CREATE DATABASE muadhin_db;
GRANT ALL PRIVILEGES ON DATABASE muadhin_db TO muadhin_user;
ALTER USER muadhin_user CREATEDB;
SQL

# Connect to the new database and set permissions
psql -U postgres -d muadhin_db << SQL
GRANT ALL ON SCHEMA public TO muadhin_user;
SQL

echo "Database setup complete!"
