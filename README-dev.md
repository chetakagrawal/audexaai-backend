# AudexaAI Backend - Development Scripts

## 🚀 Quick Start

### Start Development Server (Recommended)
```cmd
# Double-click or run:
start-backend.bat
```
- Starts FastAPI development server with auto-reload
- Default port: http://localhost:8000
- API docs available at http://localhost:8000/docs
- Uses reliable batch file

### Manual Start
```bash
poetry run uvicorn main:app --reload
```
- Starts FastAPI development server with auto-reload
- Default port: http://localhost:8000
- API docs available at http://localhost:8000/docs

## 🛑 Stop Development Server

### Kill by Port
```cmd
# Find process using port 8000
netstat -ano | findstr :8000

# Kill by PID from above output
taskkill /PID <PID> /F
```

### Kill All Python Processes
```cmd
taskkill /IM python.exe /F
```

## 🧪 Testing

### Run Tests
```bash
poetry run pytest
```

### Run Tests with Coverage
```bash
poetry run pytest --cov=.
```

### Run Specific Test File
```bash
poetry run pytest tests/test_pbc_evidence.py
```

## 🔧 Other Commands

### Database Migrations
```bash
# Create new migration
poetry run alembic revision --autogenerate -m "description"

# Run migrations
poetry run alembic upgrade head

# Downgrade
poetry run alembic downgrade -1
```

### Install Dependencies
```bash
poetry install
```

### Activate Virtual Environment
```bash
poetry shell
```

## 📁 Project Structure
```
audexaai-backend/
├── api/                    # FastAPI routes
├── models/                 # SQLAlchemy models
├── repos/                  # Repository layer
├── services/               # Business logic
├── tests/                  # Test files
├── alembic/                # Database migrations
├── config.py              # Configuration
├── main.py                # FastAPI app entry point
├── pyproject.toml         # Poetry configuration
├── README-dev.md          # This file
└── start-dev.ps1         # PowerShell start script
```

## 🔄 Development Workflow

1. **Setup**: `poetry install` (first time)
2. **Start**: `poetry run dev`
3. **Develop**: Make changes, auto-reload handles updates
4. **Test**: `poetry run pytest` for unit/integration tests
5. **Migrate**: Use alembic commands for database changes
6. **Stop**: Use taskkill commands above when done

## 🐛 Troubleshooting

- **Port 8000 in use**: Kill existing process or change port in config
- **Dependencies**: Run `poetry install` if packages are missing
- **Database**: Ensure PostgreSQL is running and configured
- **Migrations**: Run `alembic upgrade head` after pulling changes

## 🔗 Related Services

- **Database**: PostgreSQL (configure in config.py)
- **Frontend**: http://localhost:3000 (audexaai-web)
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **API Redoc**: http://localhost:8000/redoc (ReDoc UI)
