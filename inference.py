import asyncio
import os
import re
import textwrap
from dataclasses import dataclass
from typing import List, Optional

from openai import OpenAI

from my_env_v4 import MyEnvV4Action, MyEnvV4Env

IMAGE_NAME = os.getenv("IMAGE_NAME") or os.getenv("LOCAL_IMAGE_NAME")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
BENCHMARK = os.getenv("MY_ENV_V4_BENCHMARK", "clinical_bench")
# One episode per run (validator-friendly). Set RUN_ALL_TASKS=1 to loop all three locally.
TASK_NAME = os.getenv("MY_ENV_V4_TASK", "clinical_calc")
TASKS_ALL = ("clinical_calc", "biostat_power", "biocoder")
MAX_STEPS = int(os.getenv("MAX_STEPS", "8"))
SEED = int(os.getenv("SEED", "42"))
TASK_INDEX = int(os.getenv("TASK_INDEX", "0"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "700"))

SYSTEM_PROMPT = textwrap.dedent(
    """
    You solve biomedical coding tasks by writing executable Python only.

    Rules:
    - Return only Python code.
    - No markdown fences.
    - Print the final answer when the task expects numeric output.
    - If a prior attempt failed, correct the bug instead of repeating it.
    """
).strip()


@dataclass
class AttemptRecord:
    step: int
    code: str
    reward: float
    echoed: str


def _compact(value: Optional[str], limit: int = 240) -> str:
    if not value:
        return "null"
    one_line = re.sub(r"\s+", " ", value).strip()
    if not one_line:
        return "null"
    return one_line if len(one_line) <= limit else one_line[: limit - 3] + "..."


def _extract_code(text: str) -> str:
    block = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if block:
        return block.group(1).strip()
    lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
    return "\n".join(lines).strip()


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={_compact(action)} reward={reward:.2f} "
        f"done={str(done).lower()} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


def build_user_prompt(task_name: str, task_description: str, history: List[AttemptRecord], step: int) -> str:
    history_lines: List[str] = []
    for item in history[-3:]:
        history_lines.append(f"Step {item.step} reward={item.reward:.2f}")
        history_lines.append(f"Code: {_compact(item.code, 500)}")
        history_lines.append(f"Output: {_compact(item.echoed, 300)}")
    history_block = "\n".join(history_lines) if history_lines else "None"
    return textwrap.dedent(
        f"""
        Task family: {task_name}
        Step: {step}

        Problem:
        {task_description}

        Previous attempts:
        {history_block}

        Return only Python code for the next attempt.
        """
    ).strip()


def get_model_code(client: OpenAI, task_name: str, task_description: str, history: List[AttemptRecord], step: int) -> str:
    prompt = build_user_prompt(task_name, task_description, history, step)
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        content = (response.choices[0].message.content or "").strip()
        code = _extract_code(content)
        return code or "print('')"
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return "print('')"


async def run_task(client: OpenAI, task_name: str, benchmark: str) -> None:
    env: Optional[MyEnvV4Env] = None
    rewards: List[float] = []
    history: List[AttemptRecord] = []
    steps_taken = 0
    success = False
    score = 0.0

    log_start(task=task_name, env=benchmark, model=MODEL_NAME)

    try:
        env = await MyEnvV4Env.create(task_name=task_name, image_name=IMAGE_NAME)
        result = await env.reset(task_index=TASK_INDEX, seed=SEED)
        task_description = result.observation.echoed_message

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            code = get_model_code(client, task_name, task_description, history, step)
            result = await env.step(MyEnvV4Action(message=code))

            reward = float(result.reward or 0.0)
            done = bool(result.done)
            echoed = result.observation.echoed_message

            rewards.append(reward)
            steps_taken = step
            history.append(AttemptRecord(step=step, code=code, reward=reward, echoed=echoed))

            log_step(step=step, action=code, reward=reward, done=done, error=None)

            if done:
                break

        if rewards:
            score = min(max(sum(rewards) / len(rewards), 0.0), 1.0)
        success = bool(rewards) and rewards[-1] >= 1.0
    finally:
        if env is not None:
            try:
                await env.close()
            except Exception:
                pass
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


async def main() -> None:
    # Do not raise if HF_TOKEN is missing: the hackathon runner may inject it only for
    # some phases; model calls already fall back in get_model_code. OpenAI client needs a string.
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY or "unset")

    if os.getenv("RUN_ALL_TASKS", "").lower() in {"1", "true", "yes"}:
        for name in TASKS_ALL:
            await run_task(client, name, BENCHMARK)
    else:
        await run_task(client, TASK_NAME, BENCHMARK)


if __name__ == "__main__":
    asyncio.run(main())
