"""
generate_charts.py
==================
Lê o metrics.csv e gera os 4 gráficos obrigatórios + 1 extra (lead time).

Uso:
    python generate_charts.py [caminho_do_csv]

Saída:
    charts/chart_1_duration_by_run.png
    charts/chart_2_jobs_stacked.png
    charts/chart_3_success_rate.png
    charts/chart_4_tests_vs_duration.png
    charts/chart_5_lead_time.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # sem GUI

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COLORS = {
    "success": "#2ecc71",
    "failure": "#e74c3c",
    "cancelled": "#95a5a6",
    "other": "#3498db",
}

OUTPUT_DIR = Path("charts")
OUTPUT_DIR.mkdir(exist_ok=True)


def _status_color(status: str) -> str:
    return COLORS.get(str(status).lower(), COLORS["other"])


def _load(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["workflow_duration"] = pd.to_numeric(df["workflow_duration"], errors="coerce")
    df["job_duration"] = pd.to_numeric(df["job_duration"], errors="coerce")
    df["test_count"] = pd.to_numeric(df["test_count"], errors="coerce")
    df["lead_time_seconds"] = pd.to_numeric(df["lead_time_seconds"], errors="coerce")
    return df


def _run_label(row: pd.Series) -> str:
    sha = str(row.get("commit_sha", ""))[:7]
    msg = str(row.get("commit_message", ""))[:30]
    return f"#{row['run_number']} {sha} – {msg}"


# ---------------------------------------------------------------------------
# Gráfico 1 – Tempo total do pipeline por execução
# ---------------------------------------------------------------------------

def chart_duration_by_run(df: pd.DataFrame) -> None:
    runs = (
        df.groupby(["run_id", "commit_sha", "commit_message", "status", "workflow_duration"])
        .size()
        .reset_index(name="_count")
        .sort_values("run_id")
    )
    runs = runs.drop_duplicates("run_id").reset_index(drop=True)
    runs["run_number"] = range(1, len(runs) + 1)
    runs["label"] = runs.apply(_run_label, axis=1)

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = [_status_color(s) for s in runs["status"]]
    bars = ax.barh(runs["label"], runs["workflow_duration"], color=colors)

    ax.set_xlabel("Duração total (segundos)")
    ax.set_title("Gráfico 1 – Tempo total do pipeline por execução")
    ax.invert_yaxis()

    # Legenda de status
    from matplotlib.patches import Patch
    seen = {}
    for s, c in COLORS.items():
        if s in runs["status"].values:
            seen[s] = c
    legend_elems = [Patch(facecolor=c, label=s) for s, c in seen.items()]
    ax.legend(handles=legend_elems, loc="lower right")

    for bar, val in zip(bars, runs["workflow_duration"]):
        if pd.notna(val):
            ax.text(val + 1, bar.get_y() + bar.get_height() / 2, f"{val:.0f}s",
                    va="center", fontsize=8)

    plt.tight_layout()
    out = OUTPUT_DIR / "chart_1_duration_by_run.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  salvo: {out}")


# ---------------------------------------------------------------------------
# Gráfico 2 – Tempo por job (barras empilhadas)
# ---------------------------------------------------------------------------

def chart_jobs_stacked(df: pd.DataFrame) -> None:
    jobs_df = df.dropna(subset=["job_duration"]).copy()
    if jobs_df.empty:
        print("  aviso: sem dados de job_duration, pulando gráfico 2.")
        return

    pivot = (
        jobs_df.groupby(["run_id", "job_name"])["job_duration"]
        .mean()
        .unstack(fill_value=0)
        .reset_index()
    )
    # Ordenar por run_id
    pivot = pivot.sort_values("run_id").reset_index(drop=True)
    pivot["run_number"] = range(1, len(pivot) + 1)

    job_cols = [c for c in pivot.columns if c not in ("run_id", "run_number")]
    bottom = np.zeros(len(pivot))
    cmap = plt.cm.get_cmap("tab10", len(job_cols))

    fig, ax = plt.subplots(figsize=(12, 6))
    for i, col in enumerate(job_cols):
        vals = pivot[col].values
        ax.bar(pivot["run_number"], vals, bottom=bottom, label=col, color=cmap(i))
        bottom += vals

    ax.set_xlabel("Execução (#)")
    ax.set_ylabel("Duração (segundos)")
    ax.set_title("Gráfico 2 – Tempo por job por execução (barras empilhadas)")
    ax.set_xticks(pivot["run_number"])
    ax.legend(loc="upper right")

    plt.tight_layout()
    out = OUTPUT_DIR / "chart_2_jobs_stacked.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  salvo: {out}")


# ---------------------------------------------------------------------------
# Gráfico 3 – Taxa de sucesso e falha
# ---------------------------------------------------------------------------

def chart_success_rate(df: pd.DataFrame) -> None:
    runs = df.drop_duplicates("run_id")[["run_id", "status"]].copy()
    counts = runs["status"].value_counts()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Pizza
    ax = axes[0]
    colors = [_status_color(s) for s in counts.index]
    ax.pie(counts.values, labels=counts.index, colors=colors, autopct="%1.0f%%", startangle=90)
    ax.set_title("Distribuição de status")

    # Linha do tempo
    ax2 = axes[1]
    runs_sorted = runs.sort_values("run_id").reset_index(drop=True)
    runs_sorted["run_number"] = range(1, len(runs_sorted) + 1)
    run_colors = [_status_color(s) for s in runs_sorted["status"]]
    ax2.scatter(
        runs_sorted["run_number"],
        [1] * len(runs_sorted),
        c=run_colors,
        s=200,
        zorder=3,
    )
    ax2.set_yticks([])
    ax2.set_xlabel("Execução (#)")
    ax2.set_title("Linha do tempo: verde=sucesso, vermelho=falha")
    ax2.set_xlim(0, len(runs_sorted) + 1)
    ax2.grid(axis="x", linestyle="--", alpha=0.4)

    from matplotlib.patches import Patch
    legend_elems = [
        Patch(facecolor=COLORS["success"], label="success"),
        Patch(facecolor=COLORS["failure"], label="failure"),
    ]
    ax2.legend(handles=legend_elems)

    fig.suptitle("Gráfico 3 – Taxa de sucesso e falha", fontsize=13)
    plt.tight_layout()
    out = OUTPUT_DIR / "chart_3_success_rate.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  salvo: {out}")


# ---------------------------------------------------------------------------
# Gráfico 4 – Quantidade de testes × duração do pipeline
# ---------------------------------------------------------------------------

def chart_tests_vs_duration(df: pd.DataFrame) -> None:
    sub = df.dropna(subset=["test_count", "job_duration"]).copy()
    if sub.empty:
        print("  aviso: sem dados de test_count, pulando gráfico 4.")
        return

    test_jobs = sub[sub["job_name"].str.lower().str.contains("test", na=False)]
    if test_jobs.empty:
        test_jobs = sub

    fig, ax = plt.subplots(figsize=(9, 6))
    colors = [_status_color(s) for s in test_jobs["status"]]
    ax.scatter(test_jobs["test_count"], test_jobs["job_duration"], c=colors, s=80, alpha=0.8)

    # Regressão linear
    x = test_jobs["test_count"].values
    y = test_jobs["job_duration"].values
    if len(x) >= 2:
        coefs = np.polyfit(x, y, 1)
        poly = np.poly1d(coefs)
        xs = np.linspace(x.min(), x.max(), 100)
        ax.plot(xs, poly(xs), "k--", alpha=0.5,
                label=f"Regressão: y={coefs[0]:.3f}x + {coefs[1]:.2f}")
        ax.legend()

    ax.set_xlabel("Quantidade de testes")
    ax.set_ylabel("Duração do job de testes (segundos)")
    ax.set_title("Gráfico 4 – Relação entre quantidade de testes e duração")
    plt.tight_layout()
    out = OUTPUT_DIR / "chart_4_tests_vs_duration.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  salvo: {out}")


# ---------------------------------------------------------------------------
# Gráfico 5 (extra) – Lead time: commit → pipeline concluído
# ---------------------------------------------------------------------------

def chart_lead_time(df: pd.DataFrame) -> None:
    runs = df.drop_duplicates("run_id")[["run_id", "lead_time_seconds", "status"]].copy()
    runs = runs.dropna(subset=["lead_time_seconds"]).sort_values("run_id").reset_index(drop=True)
    if runs.empty:
        print("  aviso: sem dados de lead_time, pulando gráfico 5.")
        return

    runs["run_number"] = range(1, len(runs) + 1)
    colors = [_status_color(s) for s in runs["status"]]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(runs["run_number"], runs["lead_time_seconds"] / 60, color=colors)
    ax.axhline(5, color="orange", linestyle="--", alpha=0.7, label="SLA 5 min (referência DORA)")
    ax.set_xlabel("Execução (#)")
    ax.set_ylabel("Lead time (minutos)")
    ax.set_title("Gráfico 5 (extra) – Lead time: commit → pipeline concluído")
    ax.legend()
    plt.tight_layout()
    out = OUTPUT_DIR / "chart_5_lead_time.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  salvo: {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "metrics.csv"
    if not Path(csv_path).exists():
        print(f"ERRO: arquivo '{csv_path}' não encontrado. Execute collect_metrics.py primeiro.")
        sys.exit(1)

    df = _load(csv_path)
    print(f"CSV carregado: {len(df)} linhas, {df['run_id'].nunique()} runs únicas.")

    print("Gerando gráficos...")
    chart_duration_by_run(df)
    chart_jobs_stacked(df)
    chart_success_rate(df)
    chart_tests_vs_duration(df)
    chart_lead_time(df)
    print(f"\nTodos os gráficos salvos em '{OUTPUT_DIR}/'.")


if __name__ == "__main__":
    main()
