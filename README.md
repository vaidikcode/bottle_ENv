# ClinicalBench

An [OpenEnv](https://github.com/meta-pytorch/OpenEnv)-compliant RL environment for biomedical code-generation tasks.

See [`clinical_bench/README.md`](clinical_bench/README.md) for full documentation.

## Quick start

```bash
# Install dependencies
pip install -r requirements.txt

# Run server (port 8080)
DATA_PATH=./clinical_bench/data uvicorn clinical_bench.server.app:app --host 0.0.0.0 --port 8080

# Run baseline inference
export HF_TOKEN=your_token
export DATA_PATH=./clinical_bench/data
python inference.py

# Docker
docker build -t clinical-bench:latest .
docker run --rm -p 8080:8080 clinical-bench:latest
```

## Tasks

| Task | Difficulty | Problems |
|------|------------|----------|
| `clinical_calc` | Easy | 1 047 |
| `biostat_power` | Medium | 343 |
| `biocoder` | Hard | 157 |
