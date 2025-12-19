# Drop all tables and rerun migrations
Write-Host "Database Drop and Migration Script" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
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
Write-Host "Step 1: Dropping all tables..." -ForegroundColor Cyan
Write-Host "This will DROP all tables and their data!" -ForegroundColor Yellow

# Drop all tables using a SQL script that handles dependencies
# Use a simpler approach: drop schema and recreate it
Write-Host "Dropping all tables..." -ForegroundColor Gray
docker exec postgres-audexa psql -U postgres -d audexa -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO postgres; GRANT ALL ON SCHEMA public TO public;"

if ($LASTEXITCODE -eq 0) {
    Write-Host "All tables dropped successfully" -ForegroundColor Green
} else {
    Write-Host "Failed to drop tables" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Resetting Alembic version table..." -ForegroundColor Cyan
# Drop alembic_version table if it exists
docker exec postgres-audexa psql -U postgres -d audexa -c "DROP TABLE IF EXISTS alembic_version CASCADE;"
Write-Host "Alembic version table dropped" -ForegroundColor Green

Write-Host ""
Write-Host "Step 3: Running all migrations from scratch..." -ForegroundColor Cyan
poetry run alembic upgrade head

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to run migrations" -ForegroundColor Red
    exit 1
}
Write-Host "Migrations applied successfully" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Verifying migration status..." -ForegroundColor Cyan
poetry run alembic current

Write-Host ""
Write-Host "Step 5: Verifying partial unique index exists..." -ForegroundColor Cyan
$indexCheck = docker exec postgres-audexa psql -U postgres -d audexa -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'controls' AND indexname = 'ux_controls_tenant_code_active';"
Write-Host $indexCheck

Write-Host ""
Write-Host "Database reset and migrations complete!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now run the test:" -ForegroundColor Cyan
Write-Host "  poetry run pytest tests/test_controls_integration.py::test_can_reuse_control_code_after_soft_delete -v" -ForegroundColor White

