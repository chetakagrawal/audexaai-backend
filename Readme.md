You are creating a small, clean FastAPI backend skeleton for the Audexa AI project.

Goal for THIS STEP ONLY:
- Create boilerplate code and project structure.
- No database models yet, no SQS, no LLM.
- Just config, app wiring, and a couple of trivial endpoints.

Tech:
- Python 3.11
- FastAPI
- Uvicorn
- pydantic-settings for config
- Use `uvicorn` for dev server.
- Use `poetry` or `uv` + `pyproject.toml` (you choose, but keep it simple).

Project structure I want:

audexa-backend/
  pyproject.toml
  README.md
  audexa/
    __init__.py
    config.py        # Pydantic settings
    main.py          # FastAPI app factory + include routers
    api/
      __init__.py
      router.py      # main APIRouter that includes versioned routers
      v1/
        __init__.py
        health.py    # GET /api/v1/health
        me_stub.py   # GET /api/v1/me (returns stub data for now)
    logging_config.py

Requirements for this step:

1. Implement `config.py` using pydantic-settings with at least:
   - `ENV` (str, default "dev")
   - `API_PREFIX` (default "/api")
2. Implement `main.py` so I can run:
   `uvicorn audexa.main:app --reload`
3. Implement `api/router.py` that mounts `/api/v1` and includes `health` + `me_stub` routers.
4. Implement `api/v1/health.py` with:
   - `GET /api/v1/health` returning JSON: `{ "status": "ok", "env": ENV }`.
5. Implement `api/v1/me_stub.py` with:
   - `GET /api/v1/me` returning stub user:
     `{ "id": "dev-user", "tenant_id": "dev-tenant", "email": "dev@audexa.ai" }`.
6. Add `logging_config.py` with a basic logging setup (INFO level, console handler).
7. Update `README.md` with:
   - How to install deps
   - How to run the dev server.

Do NOT add database, SQS, or any complex logic yet. Just clean boilerplate with good structure and comments.
