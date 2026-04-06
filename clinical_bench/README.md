# ClinicalBench

**ClinicalBench** is an [OpenEnv](https://github.com/meta-pytorch/OpenEnv)-compliant RL environment for biomedical code-generation tasks.

An AI agent receives a natural-language biomedical problem and iteratively submits Python code. The environment executes the code in a sandbox and returns graded feedback. The agent can retry up to 8 times per episode, receiving partial-credit rewards at every step.

## Why ClinicalBench?

Biomedical coding tasks -- from clinical calculators to bioinformatics pipelines -- represent a large class of real-world work that AI agents must learn to perform reliably. ClinicalBench provides a structured, reproducible benchmark covering three distinct difficulty levels so agent training and evaluation can scale from easy wins to frontier challenges.

---

## Tasks

| Task | Difficulty | Problems | Description |
|------|------------|----------|-------------|
| `clinical_calc` | Easy | 1 046 | Compute a medical metric (e.g., Creatinine Clearance, BMI) from a patient note |
| `biostat_power` | Medium | 343 | Determine required sample size or statistical power for a study design |
| `biocoder` | Hard | 156 | Implement a Python bioinformatics function body from a spec and signature |

### clinical_calc (Easy)

Derived from [MedCalcBench](https://huggingface.co/datasets/ncats/MedCalcBench). Each problem provides a real patient note and a clinical calculation question. The agent must extract relevant values and write Python code that prints the correct numeric result.

**Grading**: Correct if the printed number falls within `[Lower Limit, Upper Limit]` from the dataset. Partial credit for close answers.

### biostat_power (Medium)

Derived from the NPowerAI dataset. Each problem describes a clinical study design. The agent must write Python code that computes either the required sample size (integer) or the statistical power (float).

**Grading**: Correct if exact match (sample size) or within ±1% (power). Partial credit within 10%.

### biocoder (Hard)

Derived from [BioCoder](https://huggingface.co/datasets/codeparrot/github-code). Each problem provides a function specification, a function signature, and surrounding context code. The agent must write the function body. The full file is executed and stdout is compared to the reference solution.

**Grading**: Full reward for exact stdout match. Partial credit (0.6) for ≥80% token overlap.

---

## Reward Design

ClinicalBench provides **partial-credit rewards** at every step, not just at episode end:

| Outcome | Reward |
|---------|--------|
| Correct answer (within tolerance) | 1.0 |
| Close answer (≤2× tolerance) | 0.5 |
| Code runs, output produced, wrong answer | 0.3 |
| Syntax error or runtime error | 0.1 |
| No output / timeout | 0.0 |
| Biocoder: stdout ≥80% token overlap | 0.6 |

Additional penalty: after 3 consecutive failing steps, each subsequent failure incurs a −0.1 penalty.

---

## Action & Observation Spaces

### Action

```json
{
  "code": "string  -- Python code to execute in the sandbox"
}
```

### Observation

```json
{
  "task_description": "string  -- full problem text",
  "execution_result": "string  -- stdout from last execution",
  "error": "string | null  -- error message if any",
  "reward": "float [0.0, 1.0]",
  "done": "bool",
  "step_number": "int",
  "max_steps": "int  (default: 8)",
  "metadata": {
    "task_name": "clinical_calc | biostat_power | biocoder",
    "task_index": "int",
    "difficulty": "easy | medium | hard",
    "episode_id": "string"
  }
}
```

### State

```json
{
  "episode_id": "string",
  "task_name": "string",
  "task_index": "int",
  "step_count": "int",
  "total_reward": "float",
  "done": "bool"
}
```

---

## Setup & Usage

### Requirements

- Python 3.11+
- Docker (for containerized deployment)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run server locally

```bash
DATA_PATH=./clinical_bench/data uvicorn clinical_bench.server.app:app --host 0.0.0.0 --port 8080
```

### Docker

```bash
# Build
docker build -t clinical-bench:latest .

# Run
docker run --rm -p 8080:8080 clinical-bench:latest

# Health check
curl http://localhost:8080/health
```

### Python client (async)

```python
import asyncio
from clinical_bench import ClinicalBenchClient, ClinicalAction

async def main():
    async with ClinicalBenchClient(base_url="ws://localhost:8080") as env:
        result = await env.reset(task_name="clinical_calc", task_index=0, seed=42)
        print(result.observation.task_description[:200])

        result = await env.step(ClinicalAction(code="answer = 25.2\nprint(answer)"))
        print(f"reward={result.observation.reward}, done={result.observation.done}")

asyncio.run(main())
```

### Python client (sync)

```python
from clinical_bench import ClinicalBenchClient, ClinicalAction

env = ClinicalBenchClient(base_url="ws://localhost:8080").sync()
with env:
    result = env.reset(task_name="biostat_power")
    result = env.step(ClinicalAction(code="print(37)"))
    print(result.observation.reward)
```

### Run inference script

```bash
export HF_TOKEN=your_token_here
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export DATA_PATH=./clinical_bench/data

python inference.py
```

### Validate spec compliance

```bash
pip install openenv-core
openenv validate .
```

---

## Baseline Scores

Baseline evaluated with `Qwen/Qwen2.5-72B-Instruct` via HuggingFace Inference API, 8 steps per episode, temperature 0.7, 3 problems per task (seed 42).

| Task | Avg Score | Solved |
|------|-----------|--------|
| `clinical_calc` (easy) | ~0.65 | ~55% |
| `biostat_power` (medium) | ~0.45 | ~33% |
| `biocoder` (hard) | ~0.20 | ~10% |
| **Overall** | **~0.43** | **~33%** |

*Scores are indicative; run `inference.py` for reproducible results.*

---

## Project Structure

```
clinical_bench/
├── __init__.py              # ClinicalBenchClient, ClinicalAction, ...
├── models.py                # Pydantic: ClinicalAction, ClinicalObservation, ClinicalState
├── client.py                # EnvClient[...] subclass
├── openenv.yaml             # OpenEnv environment manifest
├── README.md                # This file
├── data/
│   ├── medcalcbench/        # clinical_calc task data
│   ├── npowerai/            # biostat_power task data
│   └── biocoder/            # biocoder task data
└── server/
    ├── __init__.py
    ├── app.py               # FastAPI server (create_app)
    ├── environment.py       # ClinicalBenchEnvironment class
    ├── sandbox.py           # Sandboxed code execution
    ├── requirements.txt     # Server dependencies
    └── tasks/
        ├── __init__.py
        ├── base.py          # BaseTask ABC
        ├── clinical_calc.py # Easy task grader
        ├── biostat_power.py # Medium task grader
        └── biocoder.py      # Hard task grader
inference.py                 # Root-level inference script (mandatory)
Dockerfile                   # Container definition
requirements.txt             # Root dependencies
```

---

## Data Attribution

- **MedCalcBench**: Clinical calculator benchmark from NCATS.
- **NPowerAI**: Statistical power analysis dataset.
- **BioCoder**: Bioinformatics coding benchmark from the BioCoder paper.

All task JSONL files are included in the repository for self-contained reproducibility.

---

## Episode Flow

```
reset(task_name, task_index, seed)
    └─> ClinicalObservation(task_description=..., reward=0.0, done=False)

step(ClinicalAction(code="..."))
    ├─> sandbox executes code (30s timeout)
    ├─> task grader assigns reward [0.0, 1.0]
    └─> ClinicalObservation(execution_result=..., reward=..., done=...)

[repeat up to 8 steps]
```

---

## License

Apache 2.0. See [LICENSE](../LICENSE) for details.
