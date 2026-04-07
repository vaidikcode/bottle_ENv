<<<<<<< HEAD
# ClinicalBench

=======
---
title: ClinicalBench - Medical Code Generation Environment
emoji: "🏥"
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 8080
base_path: /web
tags:
  - openenv
  - medical
  - bioinformatics
  - code-generation
  - clinical-ai
  - biomedical
  - python
license: apache-2.0
---

# ClinicalBench

[![OpenEnv](https://img.shields.io/badge/OpenEnv-compliant-blue)](https://github.com/meta-pytorch/OpenEnv)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![Docker](https://img.shields.io/badge/docker-ready-green)](https://hub.docker.com)

>>>>>>> cb1baf0 (fix)
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
<<<<<<< HEAD
=======

## ✨ Features

### 🎮 Interactive Demo

Try ClinicalBench in your browser with our Gradio interface:

```bash
# Start the server
DATA_PATH=./clinical_bench/data uvicorn clinical_bench.server.app:app --port 8080

# In another terminal, launch the demo
python demo.py
```

Then open `http://localhost:7860` to solve problems interactively!

### 📊 Visualization Tools

Visualize your model's performance:

```bash
# Run inference
python inference.py > results/my_model.log 2>&1

# Generate visualizations
python scripts/visualize_results.py results/my_model.log

# Output: docs/baseline_results.png
```

### 🏆 Leaderboard

Submit your results to the community leaderboard:

```bash
# Generate leaderboard from all result logs
python scripts/generate_leaderboard.py results/*.log

# Output: LEADERBOARD.md
```

See [LEADERBOARD.md](LEADERBOARD.md) for current rankings!

### 🧪 Unit Tests

Comprehensive test suite for graders:

```bash
pip install pytest
pytest tests/ -v
```

## 📚 Documentation

- **Full docs:** [clinical_bench/README.md](clinical_bench/README.md)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Citation:** [CITATION.bib](CITATION.bib)

## 🚀 Quick Links

- [Example Episode Walkthrough](clinical_bench/README.md#example-episode-walkthrough)
- [Architecture Diagram](clinical_bench/README.md#architecture)
- [Troubleshooting Guide](clinical_bench/README.md#troubleshooting)
- [Baseline Scores](clinical_bench/README.md#baseline-scores)

## 📈 Baseline Results

Evaluated with `Qwen/Qwen2.5-72B-Instruct` via HuggingFace Inference API:

| Task | Avg Score | Solved |
|------|-----------|--------|
| Clinical Calc (easy) | ~0.65 | ~55% |
| Biostat Power (medium) | ~0.45 | ~33% |
| BioCoder (hard) | ~0.20 | ~10% |
| **Overall** | **~0.43** | **~33%** |

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Adding new tasks
- Submitting test cases
- Improving graders
- Submitting to leaderboard

## 📝 License

Apache 2.0 - See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built on established biomedical benchmarks:
- **MedCalcBench** (NCATS)
- **NPowerAI** dataset
- **BioCoder** benchmark

Powered by [OpenEnv](https://github.com/meta-pytorch/OpenEnv).
>>>>>>> cb1baf0 (fix)
