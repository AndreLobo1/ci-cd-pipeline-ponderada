"""
collect_metrics.py
==================
Coleta métricas das execuções do GitHub Actions via API REST e gera um CSV estruturado.

Uso:
    python collect_metrics.py

Variáveis de ambiente:
    GITHUB_TOKEN  – Personal Access Token com escopo 'repo' (obrigatório)
    REPO_OWNER    – Dono do repositório (padrão: detectado pelo git)
    REPO_NAME     – Nome do repositório (padrão: detectado pelo git)

Saída:
    metrics.csv   – Uma linha por job, com todas as métricas coletadas
    metrics_runs.json – Dados brutos das runs (para auditoria)
"""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

REPO_OWNER = os.environ.get("REPO_OWNER", "")
REPO_NAME = os.environ.get("REPO_NAME", "")


def _get_gh_token() -> str:
    """Tenta obter token via gh CLI se GITHUB_TOKEN não estiver definido."""
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _detect_repo() -> tuple[str, str]:
    """Detecta owner e repo a partir do git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
        if match:
            return match.group(1), match.group(2).removesuffix(".git")
    except Exception:
        pass
    return "", ""


# ---------------------------------------------------------------------------
# Cliente HTTP
# ---------------------------------------------------------------------------

class GitHubClient:
    BASE = "https://api.github.com"

    def __init__(self, token: str, owner: str, repo: str):
        self.owner = owner
        self.repo = repo
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self.BASE}{path}"
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def list_workflow_runs(self, per_page: int = 100) -> list[dict]:
        """Retorna todas as runs do workflow de CI."""
        runs = []
        page = 1
        while True:
            data = self._get(
                f"/repos/{self.owner}/{self.repo}/actions/runs",
                params={"per_page": per_page, "page": page},
            )
            batch = data.get("workflow_runs", [])
            if not batch:
                break
            runs.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
        return runs

    def list_jobs(self, run_id: int) -> list[dict]:
        """Retorna os jobs de uma run."""
        data = self._get(
            f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/jobs"
        )
        return data.get("jobs", [])

    def list_artifacts(self, run_id: int) -> list[dict]:
        """Retorna os artefatos de uma run."""
        data = self._get(
            f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/artifacts"
        )
        return data.get("artifacts", [])


# ---------------------------------------------------------------------------
# Coleta e transformação
# ---------------------------------------------------------------------------

def _duration_seconds(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    try:
        s = datetime.strptime(start, fmt).replace(tzinfo=timezone.utc)
        e = datetime.strptime(end, fmt).replace(tzinfo=timezone.utc)
        return max(0.0, (e - s).total_seconds())
    except ValueError:
        return None


def _lead_time_seconds(run: dict) -> float | None:
    """Tempo entre o commit e o fim da run (lead time de feedback)."""
    commit_ts = run.get("head_commit", {}).get("timestamp")
    completed_at = run.get("updated_at")
    if not commit_ts or not completed_at:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            s = datetime.strptime(commit_ts, fmt)
            e = datetime.strptime(completed_at, fmt)
            if s.tzinfo is None:
                s = s.replace(tzinfo=timezone.utc)
            if e.tzinfo is None:
                e = e.replace(tzinfo=timezone.utc)
            return max(0.0, (e - s).total_seconds())
        except ValueError:
            continue
    return None


def collect(client: GitHubClient) -> list[dict]:
    """Coleta todas as métricas e retorna lista de registros (uma linha por job)."""
    print("Buscando runs do workflow...")
    runs = client.list_workflow_runs()
    print(f"  {len(runs)} runs encontradas.")

    records = []

    for run in runs:
        run_id = run["id"]
        commit_sha = run.get("head_sha", "")[:12]
        commit_msg = (run.get("head_commit") or {}).get("message", "").splitlines()[0][:80]
        status = run.get("conclusion") or run.get("status") or "unknown"
        timestamp = run.get("created_at", "")
        workflow_duration = _duration_seconds(run.get("created_at"), run.get("updated_at"))
        lead_time = _lead_time_seconds(run)

        print(f"  run {run_id} | {status} | {commit_sha} | '{commit_msg[:40]}'")

        jobs = client.list_jobs(run_id)
        artifacts = client.list_artifacts(run_id)
        artifact_size = sum(a.get("size_in_bytes", 0) for a in artifacts)

        # Métricas de teste extraídas do nome/step dos jobs
        test_count = None
        test_failures = None
        test_duration = None

        for job in jobs:
            job_name = job.get("name", "")
            job_status = job.get("conclusion") or job.get("status") or "unknown"
            job_duration = _duration_seconds(job.get("started_at"), job.get("completed_at"))

            # Extrair métricas de teste do step summary do job de test
            steps = job.get("steps", [])
            for step in steps:
                step_name = step.get("name", "").lower()
                if "pytest" in step_name or "run tests" in step_name or step_name == "run tests":
                    # Tentativa de extrair count dos logs (melhor esforço)
                    pass

            records.append(
                {
                    "run_id": run_id,
                    "commit_sha": commit_sha,
                    "commit_message": commit_msg,
                    "status": status,
                    "workflow_duration": round(workflow_duration, 1) if workflow_duration is not None else "",
                    "lead_time_seconds": round(lead_time, 1) if lead_time is not None else "",
                    "job_name": job_name,
                    "job_status": job_status,
                    "job_duration": round(job_duration, 1) if job_duration is not None else "",
                    "test_count": test_count if test_count is not None else "",
                    "test_failures": test_failures if test_failures is not None else "",
                    "test_avg_duration": "",
                    "artifact_size_bytes": artifact_size,
                    "timestamp": timestamp,
                }
            )

    return records


# ---------------------------------------------------------------------------
# Enriquecimento com dados do test-results.json (se baixado manualmente)
# ---------------------------------------------------------------------------

def enrich_from_json_reports(records: list[dict]) -> None:
    """
    Se existirem arquivos test-results-{run_id}.json na pasta 'artifacts/',
    enriquece os registros com test_count, test_failures e test_avg_duration.
    """
    artifacts_dir = Path("artifacts")
    if not artifacts_dir.exists():
        return

    for fpath in artifacts_dir.glob("test-results-*.json"):
        try:
            run_id_str = fpath.stem.replace("test-results-", "")
            run_id = int(run_id_str)
            data = json.loads(fpath.read_text())
            summary = data.get("summary", {})
            total = summary.get("total", None)
            failed = summary.get("failed", 0)
            durations = [
                t.get("duration", 0)
                for t in data.get("tests", [])
                if t.get("duration") is not None
            ]
            avg_dur = round(sum(durations) / len(durations), 4) if durations else None

            for rec in records:
                if rec["run_id"] == run_id and "test" in rec["job_name"].lower():
                    rec["test_count"] = total
                    rec["test_failures"] = failed
                    rec["test_avg_duration"] = avg_dur if avg_dur is not None else ""
        except Exception as exc:
            print(f"  aviso: não foi possível processar {fpath}: {exc}")


# ---------------------------------------------------------------------------
# Escrita do CSV
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "run_id",
    "commit_sha",
    "commit_message",
    "status",
    "workflow_duration",
    "lead_time_seconds",
    "job_name",
    "job_status",
    "job_duration",
    "test_count",
    "test_failures",
    "test_avg_duration",
    "artifact_size_bytes",
    "timestamp",
]


def write_csv(records: list[dict], path: str = "metrics.csv") -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    print(f"\nCSV salvo em '{path}' com {len(records)} linhas.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    global GITHUB_TOKEN, REPO_OWNER, REPO_NAME

    GITHUB_TOKEN = GITHUB_TOKEN or _get_gh_token()
    if not GITHUB_TOKEN:
        print("ERRO: GITHUB_TOKEN não encontrado. Defina a variável de ambiente ou instale o gh CLI.")
        sys.exit(1)

    if not REPO_OWNER or not REPO_NAME:
        detected_owner, detected_repo = _detect_repo()
        REPO_OWNER = REPO_OWNER or detected_owner
        REPO_NAME = REPO_NAME or detected_repo

    if not REPO_OWNER or not REPO_NAME:
        print("ERRO: não foi possível detectar o repositório. Defina REPO_OWNER e REPO_NAME.")
        sys.exit(1)

    print(f"Repositório: {REPO_OWNER}/{REPO_NAME}")

    client = GitHubClient(GITHUB_TOKEN, REPO_OWNER, REPO_NAME)
    records = collect(client)

    enrich_from_json_reports(records)

    # Salvar JSON bruto para auditoria
    raw_path = "metrics_runs.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"JSON bruto salvo em '{raw_path}'.")

    write_csv(records)
    print("Coleta concluída.")


if __name__ == "__main__":
    main()
