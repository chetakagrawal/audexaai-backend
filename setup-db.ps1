# PostgreSQL Docker Setup Script for Audexa Backend

Write-Host "Setting up PostgreSQL database for Audexa Backend..." -ForegroundColor Green

# Check if Docker is running
$dockerCheck = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Docker Desktop is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker is running" -ForegroundColor Green

# Check if container already exists
$containerExists = docker ps -a --filter "name=postgres-audexa" --format "{{.Names}}"

if ($containerExists -eq "postgres-audexa") {
    Write-Host "Container 'postgres-audexa' already exists." -ForegroundColor Yellow
    $response = Read-Host "Do you want to remove it and create a new one? (y/N)"
    if ($response -eq "y" -or $response -eq "Y") {
        docker stop postgres-audexa
        docker rm postgres-audexa
        Write-Host "Removed existing container." -ForegroundColor Green
    } else {
        Write-Host "Starting existing container..." -ForegroundColor Yellow
        docker start postgres-audexa
        Write-Host "✓ PostgreSQL is running on localhost:5432" -ForegroundColor Green
        Write-Host ""
        Write-Host "Connection string:" -ForegroundColor Cyan
        Write-Host "DATABASE_URL=postgresql+psycopg://postgres:audexa123@localhost:5432/audexa" -ForegroundColor White
        exit 0
    }
}

# Create and start PostgreSQL container
Write-Host "Creating PostgreSQL container..." -ForegroundColor Yellow
docker run --name postgres-audexa `
    -e POSTGRES_USER=postgres `
    -e POSTGRES_PASSWORD=audexa123 `
    -e POSTGRES_DB=audexa `
    -p 5432:5432 `
    -d postgres:16

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ PostgreSQL container created and started!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Database Details:" -ForegroundColor Cyan
    Write-Host "  Host: localhost" -ForegroundColor White
    Write-Host "  Port: 5432" -ForegroundColor White
    Write-Host "  Database: audexa" -ForegroundColor White
    Write-Host "  Username: postgres" -ForegroundColor White
    Write-Host "  Password: audexa123" -ForegroundColor White
    Write-Host ""
    Write-Host "Add this to your .env file:" -ForegroundColor Cyan
    Write-Host "DATABASE_URL=postgresql+psycopg://postgres:audexa123@localhost:5432/audexa" -ForegroundColor White
    Write-Host ""
    Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    Write-Host "✓ PostgreSQL is ready!" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to create PostgreSQL container" -ForegroundColor Red
    exit 1
}

