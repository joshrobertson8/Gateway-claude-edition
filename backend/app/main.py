from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .routers import activities, jobs, submissions

app = FastAPI(title="Gateway API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(activities.router)
app.include_router(jobs.router)
app.include_router(submissions.router)
