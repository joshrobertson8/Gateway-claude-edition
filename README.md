# Gateway

Theory → Practice. Drop in learning material, get bite-sized Python coding challenges with AI hints, grading, and a session report. Powered by a local Ollama running `gpt-oss:120b`.

## Architecture

```
backend/   FastAPI + SQLModel + SQLite (no auth), layered:
  app/
    main.py        app + CORS + startup
    config.py      env / model name
    database.py    engine + session
    models.py      SQLModel tables (Activity, Problem, Submission,
                   ProblemResponse, AsyncJob)
    schemas.py     Pydantic camelCase request/response models
    routers/       thin HTTP layer (activities, jobs, submissions)
    services/      business logic
      ai_service.py         Ollama client (problems / grading / hints / report)
      job_service.py        async job orchestration
      activity_service.py   create activity + run generation
      submission_service.py submit code + grade + report
      runner_service.py     python subprocess runner
frontend/  Vite + React + Monaco
  src/
    App.jsx
    api.js                       fetch client + job poller
    components/{Landing,Workspace,Report}.jsx
```

Long-running LLM work is persisted as `async_job` rows; the frontend polls
`GET /api/jobs/{id}`, mirroring the spec.

## Prereqs

1. Python 3.11+
2. Node 18+
3. [Ollama](https://ollama.com) running locally:
   ```
   ollama pull gpt-oss:120b
   ollama serve
   ```

## Run

**Backend**
```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Config (env vars)

- `OLLAMA_BASE_URL` (default `http://localhost:11434`)
- `OLLAMA_MODEL` (default `gpt-oss:120b`)
- `PROBLEMS_PER_ACTIVITY` (default `3`)
- `DATABASE_URL` (default `sqlite:///./gateway.db`)

## API

Implements the Sprint 0 spec:

| Method | Path |
| --- | --- |
| POST | `/api/activities` |
| GET  | `/api/activities/{activity_id}/problems` |
| POST | `/api/activities/{activity_id}/submissions` |
| POST | `/api/submissions/{submission_id}/problems/{problem_id}/responses` |
| GET  | `/api/submissions/{submission_id}/problems/{problem_id}/responses` |
| POST | `/api/submissions/{submission_id}/report` |
| GET  | `/api/submissions/{submission_id}/report` |
| GET  | `/api/jobs/{job_id}` |
| POST | `/api/run` (helper: run python code) |
| POST | `/api/hint` (helper: request a hint) |

Interactive docs at http://localhost:8000/docs.
