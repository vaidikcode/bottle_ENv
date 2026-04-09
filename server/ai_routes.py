"""
AI-driven inference routes for the ClinicalBench frontend observer.

POST /api/reset    - Start a new episode; returns session_id + task description
POST /api/ai-step  - LLM generates Python, env executes it, returns result
"""

from __future__ import annotations

import os
import re
import textwrap
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from .models import ClinicalAction
from .environment import ClinicalBenchEnvironment, DATA_PATH

router = APIRouter(prefix="/api")

# In-memory session store: session_id -> session dict
_SESSIONS: Dict[str, Dict[str, Any]] = {}

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "unsloth/Meta-Llama-3.1-8B-Instruct:featherless-ai")

_SYSTEM_PROMPT = textwrap.dedent("""
    You are a biomedical AI assistant solving clinical coding problems.
    You must write Python code that computes the correct answer and prints it.

    Rules:
    - Write ONLY executable Python code
    - Your code must end with a print() statement that outputs the answer
    - Do not include markdown code fences, explanations, or prose
    - If previous attempts had errors, fix them
    - Keep the code concise and correct

    Output ONLY Python code, nothing else.
""").strip()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ResetRequest(BaseModel):
    task_name: str
    task_index: Optional[int] = None
    seed: Optional[int] = 42


class ResetResponse(BaseModel):
    session_id: str
    task_description: str
    task_name: str
    difficulty: str
    max_steps: int


class StepRequest(BaseModel):
    session_id: str


class StepResponse(BaseModel):
    generated_code: str
    execution_result: str
    error: Optional[str]
    reward: float
    done: bool
    step_number: int
    max_steps: int
    metadata: dict


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _build_user_prompt(
    task_description: str,
    history: List[Dict[str, Any]],
    step: int,
) -> str:
    history_lines = []
    for h in history[-4:]:
        history_lines.append(f"--- Step {h['step']} ---")
        history_lines.append(f"Code submitted:\n{h['code'][:400]}")
        history_lines.append(f"Output: {h['execution_result'][:300]}")
        if h.get("error"):
            history_lines.append(f"Error: {h['error'][:300]}")
        history_lines.append(f"Reward: {h['reward']:.2f}")

    history_block = "\n".join(history_lines) if history_lines else "None"

    return textwrap.dedent(f"""
        Step {step} — solve this task by printing the answer:

        {task_description}

        Previous attempts:
        {history_block}

        Write Python code to solve this. Print the final answer.
    """).strip()


def _extract_code(text: str) -> str:
    """Strip markdown fences from LLM output if present."""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    lines = [l for l in text.strip().splitlines() if not l.strip().startswith("```")]
    return "\n".join(lines).strip()


def _call_llm(task_description: str, history: List[Dict[str, Any]], step: int) -> str:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    user_prompt = _build_user_prompt(task_description, history, step)

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=512,
        )
        raw = (completion.choices[0].message.content or "").strip()
        code = _extract_code(raw)
        return code if code else "print('no output')"
    except Exception as exc:
        return f"# LLM call failed: {exc}\nprint('error')"


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

@router.post("/reset", response_model=ResetResponse)
def reset_episode(req: ResetRequest) -> ResetResponse:
    env = ClinicalBenchEnvironment(data_path=DATA_PATH)
    obs = env.reset(
        task_name=req.task_name,
        task_index=req.task_index,
        seed=req.seed,
    )

    session_id = str(uuid.uuid4())[:12]
    _SESSIONS[session_id] = {
        "env": env,
        "history": [],
        "task_description": obs.task_description,
    }

    return ResetResponse(
        session_id=session_id,
        task_description=obs.task_description,
        task_name=obs.metadata.get("task_name", req.task_name),
        difficulty=obs.metadata.get("difficulty", "easy"),
        max_steps=obs.max_steps,
    )


@router.post("/ai-step", response_model=StepResponse)
def ai_step(req: StepRequest) -> StepResponse:
    session = _SESSIONS.get(req.session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please reset first.",
        )

    env: ClinicalBenchEnvironment = session["env"]
    history: List[Dict[str, Any]] = session["history"]
    task_description: str = session["task_description"]
    step = len(history) + 1

    code = _call_llm(task_description, history, step)
    obs = env.step(ClinicalAction(code=code))

    history.append({
        "step": step,
        "code": code,
        "execution_result": obs.execution_result,
        "error": obs.error,
        "reward": obs.reward,
    })

    if obs.done:
        _SESSIONS.pop(req.session_id, None)

    return StepResponse(
        generated_code=code,
        execution_result=obs.execution_result,
        error=obs.error,
        reward=obs.reward,
        done=obs.done,
        step_number=obs.step_number,
        max_steps=obs.max_steps,
        metadata=obs.metadata,
    )
