---
title: ClinicalBench (OpenEnv)
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8080
tags:
  - openenv
---

# ClinicalBench

An [OpenEnv](https://github.com/meta-pytorch/OpenEnv)-compliant RL environment for biomedical code-generation tasks.

See [`clinical_bench/README.md`](clinical_bench/README.md) for full documentation.

## Quick start

Requires **Python 3.11+** (OpenEnv / `openenv-core` 0.2.x). macOS `/usr/bin/python3` is often **3.9** — use **Homebrew** Python (`brew install python`) and a venv.

### One-time: Homebrew Python + venv + deps

```bash
brew install python          # latest 3.x (e.g. 3.14) — skip if already installed
cd /path/to/bottle_ENv
/opt/homebrew/bin/python3 -m venv .venv    # Intel Mac: /usr/local/bin/python3
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt            # includes openenv-core → `openenv` CLI
```

### Daily use (after `source .venv/bin/activate`)

```bash
openenv validate clinical_bench -v

DATA_PATH=./clinical_bench/data uvicorn clinical_bench.server.app:app --host 0.0.0.0 --port 8080

export HF_TOKEN=your_token
export DATA_PATH=./clinical_bench/data
python inference.py
```

Or prefix with `.venv/bin/` instead of activating.

### Docker

Build from the **repository root** (context `.`, Dockerfile under `clinical_bench/`):

```bash
docker build -f clinical_bench/Dockerfile -t clinical-bench:latest .
docker run --rm -p 8080:8080 clinical-bench:latest
```

**Hugging Face Space:** in Space **Settings**, set Dockerfile path to `clinical_bench/Dockerfile` and build context to `.` (repo root). After deploy, confirm **`/health`** returns 200 (validators use that, not necessarily `/`). **`/docs`** is the FastAPI OpenAPI UI.

## Tasks

| Task | Difficulty | Problems |
|------|------------|----------|
| `clinical_calc` | Easy | 1 047 |
| `biostat_power` | Medium | 343 |
| `biocoder` | Hard | 157 |

## Action, Observation, State

Action:

```json
{
  "code": "Python code to execute in the sandbox"
}
```

Observation:

```json
{
  "task_description": "Full problem text",
  "execution_result": "stdout from the last execution",
  "error": "error string or null",
  "reward": "float in [0.0, 1.0]",
  "done": "boolean",
  "step_number": "integer",
  "max_steps": "integer",
  "metadata": {
    "task_name": "clinical_calc | biostat_power | biocoder",
    "task_index": "integer",
    "difficulty": "easy | medium | hard",
    "episode_id": "string"
  }
}
```

State:

```json
{
  "episode_id": "string",
  "task_name": "string",
  "task_index": "integer",
  "step_count": "integer",
  "total_reward": "float",
  "done": "boolean"
}
```

## Reward and Grading

Each task has a deterministic programmatic grader and returns partial progress on every step:

| Outcome | Reward |
|---------|--------|
| Correct answer | 1.0 |
| Close answer | 0.5 |
| Code runs but answer is wrong | 0.3 |
| Syntax/runtime error | 0.1 |
| No output or timeout | 0.0 |
| `biocoder` token-overlap partial match | 0.6 |

The environment penalizes repeated failures after 3 consecutive low-reward steps.

## Baseline Inference

`inference.py` is in the project root and uses `from openai import OpenAI`.

Required environment variables:

```bash
export HF_TOKEN=your_token
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
```

Only `API_BASE_URL` and `MODEL_NAME` have defaults. `HF_TOKEN` has no default and must be supplied by the runner.

The script emits structured stdout records only:

```text
[START] task=<task_name> env=clinical_bench model=<model_name>
[STEP] step=<n> action=<code_preview> reward=<0.00> done=<true|false> error=<msg|null>
[END] success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
```

Indicative baseline scores for 3 fixed problems per task with `Qwen/Qwen2.5-72B-Instruct`, 8 steps, and temperature 0.7:

| Task | Avg Score | Solved |
|------|-----------|--------|
| `clinical_calc` | ~0.65 | ~55% |
| `biostat_power` | ~0.45 | ~33% |
| `biocoder` | ~0.20 | ~10% |
| Overall | ~0.43 | ~33% |

## Validation

```bash
openenv validate
docker build -t clinical-bench:latest .
docker run --rm -p 8080:8080 clinical-bench:latest
curl http://localhost:8080/health
python inference.py
```
