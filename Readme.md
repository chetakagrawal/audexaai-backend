# Audexa AI Backend

FastAPI backend for the Audexa AI platform.

## Tech Stack

- **Python 3.11+**
- **FastAPI** - Modern, fast web framework
- **Uvicorn** - ASGI server
- **Pydantic Settings** - Configuration management
- **Poetry** - Dependency management

## Project Structure

```
audexaai-backend/
├── pyproject.toml          # Poetry configuration
├── README.md               # This file
├── main.py                 # FastAPI app factory
├── config.py               # Pydantic settings
├── logging_config.py       # Logging setup
└── api/
    ├── __init__.py
    ├── router.py           # Main API router
    └── v1/
        ├── __init__.py
        ├── health.py       # GET /api/v1/health
        └── me_stub.py      # GET /api/v1/me
```

## Installation

### Prerequisites

- Python 3.11 or higher
- Poetry (recommended: install via `pipx install poetry`)

#### Installing Poetry

**Recommended method (using pipx):**
```bash
# Install pipx if you don't have it
pip install pipx
pipx ensurepath

# Install poetry via pipx
pipx install poetry
```

**Alternative methods:**
- Official installer: `curl -sSL https://install.python-poetry.org | python3 -`
- Via pip: `pip install poetry` (not recommended - can cause conflicts)

### Setup

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Activate the virtual environment:**
   ```bash
   poetry shell
   ```

   Or run commands with `poetry run`:
   ```bash
   poetry run uvicorn main:app --reload
   ```

## Running the Development Server

### Option 1: Using Poetry

```bash
poetry run uvicorn main:app --reload
```

### Option 2: Using Poetry Script

```bash
poetry run dev
```

### Option 3: Direct Uvicorn (if in poetry shell)

```bash
uvicorn main:app --reload
```

The server will start at `http://localhost:8000`

## API Endpoints

### Root
- `GET /` - API information

### Health Check
- `GET /api/v1/health` - Returns `{ "status": "ok", "env": "dev" }`

### User (Stub)
- `GET /api/v1/me` - Returns stub user data:
  ```json
  {
    "id": "dev-user",
    "tenant_id": "dev-tenant",
    "email": "dev@audexa.ai"
  }
  ```

### Database Check
- `GET /api/v1/db-check` - Checks database connectivity:
  - Returns `{ "db": "ok" }` if connection succeeds
  - Returns `500` error if connection fails

## Configuration

Configuration is managed via environment variables using `pydantic-settings`. Create a `.env` file in the project root:

```env
ENV=dev
API_PREFIX=/api
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/audexa
```

Default values:
- `ENV`: `"dev"`
- `API_PREFIX`: `"/api"`
- `DATABASE_URL`: `"postgresql+psycopg://user:password@localhost:5432/audexa"`

## Development

### API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Project Status

This is a minimal skeleton with:
- ✅ FastAPI app structure
- ✅ Configuration management
- ✅ Versioned API routes
- ✅ Health check endpoint
- ✅ Stub user endpoint
- ✅ Logging setup
- ✅ SQLAlchemy 2.x with async support
- ✅ Database connection management
- ✅ Alembic migrations setup
- ✅ Database health check endpoint
- ✅ Multi-tenant data model (tenants, users, memberships)
- ✅ Controls and Applications CRUD with audit metadata
- ✅ Version history system (automatic snapshots via Postgres triggers)
  - Generic `entity_versions` table for version snapshots
  - Automatic capture on UPDATE/DELETE for `controls` and `applications`
  - Service layer for querying version history

**Not yet implemented:**
- Authentication (in progress)
- SQS integration
- LLM integration

## Database Setup

### Quick Setup with Docker (Recommended)

The easiest way to get PostgreSQL running locally is with Docker:

1. **Make sure Docker Desktop is running**

2. **Run the setup script:**
   ```powershell
   .\setup-db.ps1
   ```

   Or manually create the container:
   ```powershell
   docker run --name postgres-audexa `
     -e POSTGRES_USER=postgres `
     -e POSTGRES_PASSWORD=audexa123 `
     -e POSTGRES_DB=audexa `
     -p 5432:5432 `
     -d postgres:16
   ```

3. **Create a `.env` file** (copy from `.env.example`):
   ```env
   DATABASE_URL=postgresql+psycopg://postgres:audexa123@localhost:5432/audexa
   ```

### Alternative: Install PostgreSQL Locally

1. Download from: https://www.postgresql.org/download/windows/
2. Install and remember your password
3. Create the database:
   ```sql
   CREATE DATABASE audexa;
   ```
4. Update `.env` with your credentials

### Configuration

Set the `DATABASE_URL` environment variable or add it to your `.env` file:

```env
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/dbname
```

### Running Migrations

Alembic is configured and ready. To create and run migrations:

```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback one migration
poetry run alembic downgrade -1
```

**Note:** The database URL in `alembic.ini` is overridden by `config.settings.DATABASE_URL` in `alembic/env.py`, so you only need to set it in your `.env` file.

### Testing Database Connection

Once your database is configured, test the connection:

```bash
curl http://localhost:8000/api/v1/db-check
```

This will return `{"db": "ok"}` if the connection succeeds, or a 500 error with details if it fails.

## License

Proprietary - Audexa AI
