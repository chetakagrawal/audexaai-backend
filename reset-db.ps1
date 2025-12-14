# Database Reset Script for Audexa Backend
Write-Host "Database Reset Script" -ForegroundColor Green
Write-Host "====================" -ForegroundColor Green
Write-Host ""

# Check if Docker container exists
$containerExists = docker ps -a --filter "name=postgres-audexa" --format "{{.Names}}"
if ($containerExists -ne "postgres-audexa") {
    Write-Host "Container 'postgres-audexa' not found!" -ForegroundColor Red
    Write-Host "Please run setup-db.ps1 first to create the container." -ForegroundColor Yellow
    exit 1
}

# Check if container is running
$containerRunning = docker ps --filter "name=postgres-audexa" --format "{{.Names}}"
if ($containerRunning -ne "postgres-audexa") {
    Write-Host "Starting PostgreSQL container..." -ForegroundColor Yellow
    docker start postgres-audexa
    Start-Sleep -Seconds 3
    Write-Host "Container started" -ForegroundColor Green
}

# Set DATABASE_URL for Alembic
$env:DATABASE_URL = "postgresql+psycopg://postgres:audexa123@localhost:5432/audexa"

Write-Host ""
Write-Host "Step 1: Checking current migration status..." -ForegroundColor Cyan
poetry run alembic current
Write-Host ""

Write-Host "Step 2: Running migrations to ensure schema is up to date..." -ForegroundColor Cyan
poetry run alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to run migrations" -ForegroundColor Red
    exit 1
}
Write-Host "Migrations applied" -ForegroundColor Green
Write-Host ""

Write-Host "Step 3: Clearing all data from database..." -ForegroundColor Cyan
Write-Host "This will TRUNCATE all tables (keeps schema, removes all data)" -ForegroundColor Yellow

# Truncate all known tables with CASCADE to handle foreign keys
$truncateQuery = "TRUNCATE TABLE signups, project_controls, controls, projects, user_tenants, auth_identities, users, tenants RESTART IDENTITY CASCADE;"

Write-Host "Truncating tables..." -ForegroundColor Gray
docker exec postgres-audexa psql -U postgres -d audexa -c $truncateQuery

if ($LASTEXITCODE -eq 0) {
    Write-Host "All tables truncated successfully" -ForegroundColor Green
} else {
    Write-Host "Failed to truncate tables (might not exist yet)" -ForegroundColor Yellow
    Write-Host "Continuing anyway..." -ForegroundColor Gray
}

Write-Host ""
Write-Host "Step 4: Verifying database state..." -ForegroundColor Cyan
poetry run alembic current
Write-Host ""

Write-Host "Database reset complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  - Run your application" -ForegroundColor White
Write-Host "  - Create new test data as needed" -ForegroundColor White
