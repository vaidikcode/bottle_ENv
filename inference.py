"""
ClinicalBench Inference Script
================================
MANDATORY
- Before running, set the following environment variables:
    API_BASE_URL   The API endpoint for the LLM (e.g. https://router.huggingface.co/v1)
    MODEL_NAME     The model identifier (e.g. Qwen/Qwen2.5-72B-Instruct)
    HF_TOKEN       Your Hugging Face / API key

- Defaults (override via env vars):
    API_BASE_URL = "https://router.huggingface.co/v1"
    MODEL_NAME   = "Qwen/Qwen2.5-72B-Instruct"

STDOUT FORMAT
- The script emits exactly three line types:

    [START] task=<task_name> env=clinical_bench model=<model_name>
    [STEP]  step=<n> action=<code_preview> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

  Rules:
    - One [START] line at episode begin.
    - One [STEP] line per step, immediately after env.step() returns.
    - One [END] line after episode ends, always emitted (even on exception).
    - reward and rewards are formatted to 2 decimal places.
    - done and success are lowercase booleans: true or false.
    - error is the raw error string, or null if none.
    - All fields on a single line with no newlines within a line.
    - score is the final per-episode score in [0, 1].

Example:
    [START] task=clinical_calc env=clinical_bench model=Qwen2.5-72B-Instruct
    [STEP] step=1 action=print(25.0) reward=0.30 done=false error=null
    [STEP] step=2 action=print(25.2) reward=1.00 done=true error=null
    [END] success=true steps=2 score=1.00 rewards=0.30,1.00
"""

import os
import sys
import textwrap
from typing import Optional

from openai import OpenAI

# Import the environment directly (no Docker needed for local inference)
from clinical_bench.server.environment import ClinicalBenchEnvironment
from clinical_bench.models import ClinicalAction

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")  # Docker image if used
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
DATA_PATH = os.getenv("DATA_PATH", "./clinical_bench/data")

MAX_STEPS = 8
TEMPERATURE = 0.7
MAX_TOKENS = 512
SUCCESS_SCORE_THRESHOLD = 1.0  # reward must reach 1.0 to count as solved

# How many problems to evaluate per task (keep low for quick baseline)
PROBLEMS_PER_TASK = 3

# Fixed task indices for reproducibility
TASK_INDICES = {
    "clinical_calc": [0, 1, 2],
    "biostat_power": [0, 1, 2],
    "biocoder": [0, 1, 2],
}

BENCHMARK = "clinical_bench"

# ------------------------------------------------------------------
# System prompt
# ------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are a biomedical Python programmer. You will receive a problem description.
Write Python code that solves the problem and prints ONLY the final answer.
Rules:
- Use `answer` to store the result, then call `print(answer)`.
- For biocoder tasks: write only the function body starting with `def ...`.
- Do not include explanations or markdown fences — output pure Python code only.
"""


def _truncate(text: str, max_chars: int = 120) -> str:
    """Single-line preview of code for [STEP] logs."""
    single = text.replace("\n", "\\n").replace("\r", "")
    if len(single) > max_chars:
        single = single[:max_chars] + "..."
    return single


def run_episode(
    client: OpenAI,
    env: ClinicalBenchEnvironment,
    task_name: str,
    task_index: int,
    seed: int = 42,
) -> tuple[float, int, list[float]]:
    """
    Run one episode and return (final_score, steps_taken, per_step_rewards).

    Emits [START], [STEP]*, [END] to stdout.
    """
    rewards: list[float] = []
    steps_taken = 0
    final_score = 0.0
    success = False

    try:
        obs = env.reset(
            seed=seed,
            task_name=task_name,
            task_index=task_index,
        )

        print(
            f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}",
            flush=True,
        )

        conversation = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": obs.task_description},
        ]

        for step in range(1, MAX_STEPS + 1):
            # Agent generates code
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=conversation,
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                )
                code = response.choices[0].message.content or ""
                # Strip markdown code fences if the model adds them
                code = _strip_fences(code)
            except Exception as exc:
                code = f"# LLM error: {exc}\nprint(0)"

            action = ClinicalAction(code=code)
            step_result = env.step(action)

            reward = float(step_result.reward or 0.0)
            done = bool(step_result.done)
            error_str = step_result.error or "null"
            rewards.append(reward)
            steps_taken = step

            # Collapse multi-line errors to single line (spec requires it)
            error_oneline = error_str.replace("\n", " ").replace("\r", "") if error_str != "null" else "null"
            print(
                f"[STEP] step={step} "
                f"action={_truncate(code)} "
                f"reward={reward:.2f} "
                f"done={str(done).lower()} "
                f"error={error_oneline}",
                flush=True,
            )

            if done:
                break

            # Feed execution result back into conversation
            feedback = (
                f"Execution result:\n{step_result.execution_result}\n"
                + (f"Error: {step_result.error}\n" if step_result.error else "")
                + f"\nReward: {reward:.2f}. Try again if the answer is incorrect."
            )
            conversation.append({"role": "assistant", "content": code})
            conversation.append({"role": "user", "content": feedback})

        final_score = rewards[-1] if rewards else 0.0
        success = final_score >= SUCCESS_SCORE_THRESHOLD

    except Exception as exc:
        # Always emit [END] even on unexpected errors
        print(f"# Episode error: {exc}", file=sys.stderr, flush=True)

    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} "
        f"steps={steps_taken} "
        f"score={final_score:.2f} "
        f"rewards={rewards_str}",
        flush=True,
    )

    return final_score, steps_taken, rewards


def _strip_fences(code: str) -> str:
    """Remove markdown code fences (```python ... ```) if present."""
    lines = code.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)


def main() -> None:
    client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)
    env = ClinicalBenchEnvironment(data_path=DATA_PATH)

    all_scores: list[float] = []

    for task_name, indices in TASK_INDICES.items():
        task_scores: list[float] = []
        for idx in indices:
            score, steps, rewards = run_episode(
                client=client,
                env=env,
                task_name=task_name,
                task_index=idx,
                seed=42 + idx,
            )
            task_scores.append(score)
            all_scores.append(score)
            print(flush=True)  # blank line between episodes

        avg = sum(task_scores) / len(task_scores) if task_scores else 0.0
        print(
            f"# Task {task_name}: avg_score={avg:.2f} "
            f"({sum(1 for s in task_scores if s >= 1.0)}/{len(task_scores)} solved)",
            flush=True,
        )
        print(flush=True)

    overall = sum(all_scores) / len(all_scores) if all_scores else 0.0
    print(f"# Overall avg_score={overall:.2f}", flush=True)


if __name__ == "__main__":
    main()
