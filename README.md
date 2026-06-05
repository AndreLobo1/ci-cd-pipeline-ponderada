# CI/CD Pipeline — Experimento de Métricas

Repositório criado para a atividade de **instrumentação de pipeline CI/CD com GitHub Actions**, como parte da disciplina de Engenharia de Software.

## Sobre o projeto

Este repositório contém um sistema Python de **gerenciamento de endereçamento de armazém** com lógica de alocação de produtos em slots de estoque. O código conta com:

- **74 testes unitários** organizados em 14 módulos (`tests/`)
- Lógica de alocação inteligente de produtos (`core/agent_tools.py`)
- Pipeline ETL de dados de estoque (`core/enrichment_pipeline.py`)
- Geração de relatórios de movimentação (`core/reports.py`)

## Pipeline CI/CD

O pipeline (`.github/workflows/ci.yml`) executa automaticamente a cada push e contém:

| Job | Descrição |
|-----|-----------|
| `lint` | Análise estática com `ruff` |
| `test` | Execução dos testes com `pytest` + geração de artefato XML/JSON |

## Como reproduzir o experimento

### Pré-requisitos

```bash
python -m pip install -r requirements.txt
```

### Rodar testes localmente

```bash
pytest tests/ -v --junit-xml=test-results.xml
```

### Coletar métricas das runs do GitHub Actions

```bash
# O script detecta automaticamente owner/repo via git remote
python collect_metrics.py
# Saída: metrics.csv e metrics_runs.json
```

Com variáveis explícitas:

```bash
GITHUB_TOKEN=seu_token REPO_OWNER=AndreLobo1 REPO_NAME=ci-cd-pipeline-ponderada \
  python collect_metrics.py
```

### Gerar gráficos

```bash
python generate_charts.py
# Saída: charts/chart_1_*.png ... chart_5_*.png
```

## Estrutura do repositório

```
.
├── .github/workflows/ci.yml   # Pipeline GitHub Actions
├── core/                      # Módulos Python do sistema
├── tests/                     # 14 módulos de testes unitários
├── collect_metrics.py         # Script de coleta de métricas via API GitHub
├── generate_charts.py         # Script de geração de gráficos
├── requirements.txt
├── pytest.ini
├── REPORT.md                  # Relatório técnico completo
└── charts/                    # Gráficos gerados (após execução)
```

## Relatório

O relatório técnico completo está em [`REPORT.md`](./REPORT.md).
