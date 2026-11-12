"""HTTP API: POST a batch of job ads, get a verdict and the signals for each one.

Run: uv run uvicorn detector_golpe.api:app --reload  (docs at /docs)
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field

from detector_golpe.rules import analyze

app = FastAPI(title="Detector de golpe em vagas", version="0.1.0",
              description="Regras que apontam sinais comuns de golpe em anúncios de emprego no Brasil.")


class Job(BaseModel):
    id: str = Field(max_length=200)
    title: str = Field("", max_length=300)
    text: str = Field(min_length=1, max_length=50_000)


class Batch(BaseModel):
    jobs: list[Job] = Field(min_length=1, max_length=500)


class Signal(BaseModel):
    code: str
    match: str
    meaning: str


class Result(BaseModel):
    id: str
    title: str
    verdict: str
    signals: list[Signal]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=list[Result])
def analyze_jobs(batch: Batch):
    """Analyze the whole batch at once, so ads with copied text (A2) are compared with each other."""
    return analyze([(j.id, j.title, j.text) for j in batch.jobs])
