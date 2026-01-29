# Auth & Identity Service (FastAPI)

Production‑style backend service showcasing authentication fundamentals, JWT, PostgreSQL, Redis rate limiting, and RBAC. Designed for portfolio use and easy testing via Swagger, Postman, or curl.
<p align="center">
  <img src="Screenshot%202026-01-28%20164631.png" alt="Auth Identity Service Screenshot" width="700">
</p>

## Features
- User registration with email verification (mocked/logged)
- JWT access + refresh tokens
- Refresh token rotation + logout (revocation)
- Password reset flow with expiring tokens
- Role‑based access control (user/admin)
- Redis rate limiting on auth endpoints
- Swagger/OpenAPI docs out of the box
- Dockerized local setup

## Tech Stack
- FastAPI, SQLAlchemy, Alembic
- PostgreSQL
- Redis
- JWT (python-jose), bcrypt (passlib)

## Project Structure
```
app/
  api/            # routes + dependencies
  core/           # settings, security, rate limit
  db/             # models + session
  schemas/        # pydantic models
  services/       # auth business logic
alembic/          # migrations
```

## Quick Start (Docker)
1. Copy `env.sample` to `.env` and adjust secrets.
2. Start services:
```
docker compose up --build
```
3. Run migrations:
```
docker compose exec api alembic upgrade head
```
4. Open docs:
- Swagger: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Local Setup (no Docker)
```
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```
Set env vars (see `env.sample`), then:
```
alembic upgrade head
uvicorn app.main:app --reload
```

## Example Requests
Register:
```
curl -X POST http://localhost:8000/api/v1/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"email":"user@example.com","password":"StrongPass123"}'
```

Verify email (token appears in logs):
```
curl -X POST http://localhost:8000/api/v1/auth/verify-email \\
  -H "Content-Type: application/json" \\
  -d '{"token":"<token-from-logs>"}'
```

Login:
```
curl -X POST http://localhost:8000/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email":"user@example.com","password":"StrongPass123"}'
```

Refresh:
```
curl -X POST http://localhost:8000/api/v1/auth/refresh \\
  -H "Content-Type: application/json" \\
  -d '{"refresh_token":"<refresh>"}'
```

## Notes
- Mock email verification and reset tokens are logged on the server.
- Refresh tokens are stored in PostgreSQL and cached in Redis for fast revocation.
- `/health` returns a simple service status.
