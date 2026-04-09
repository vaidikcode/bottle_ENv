from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel

from server.models import ClinicalAction
from client import ClinicalBenchClient


def _resolve_task_name(task_name: Optional[str]) -> str:
    if task_name in {"clinical_calc", "biostat_power", "biocoder"}:
        return task_name
    return "clinical_calc"


def _message_to_code(message: str) -> str:
    stripped = message.strip()
    if not stripped:
        return "print('')"

    code_markers = ("print(", "import ", "from ", "def ", "class ", "=")
    if "\n" in stripped or stripped.startswith(code_markers):
        return stripped

    return f"print({stripped!r})"


class MyEnvV4Action(BaseModel):
    message: str


@dataclass
class _MyEnvV4Observation:
    echoed_message: str


@dataclass
class _MyEnvV4Result:
    observation: _MyEnvV4Observation
    reward: float
    done: bool


class MyEnvV4Env:
    def __init__(self, client: ClinicalBenchClient, task_name: str) -> None:
        self._client = client
        self._task_name = task_name
        self._last_prompt = ""

    @classmethod
    async def create(cls, task_name: str, image_name: Optional[str] = None) -> "MyEnvV4Env":
        """Create an env using OPENENV_BASE_URL / ENV_BASE_URL / BASE_URL, falling back to the HF Space."""
        env_url = os.getenv("OPENENV_BASE_URL") or os.getenv("ENV_BASE_URL") or os.getenv("BASE_URL")
        space_id = os.getenv("HF_SPACE_ID") or os.getenv("SPACE_ID")

        if env_url:
            client: ClinicalBenchClient = ClinicalBenchClient(base_url=env_url)
        elif space_id:
            client = await ClinicalBenchClient.from_env(space_id)
        else:
            resolved_image = image_name or os.getenv("LOCAL_IMAGE_NAME") or "clinical-bench:latest"
            client = await ClinicalBenchClient.from_docker_image(resolved_image)

        resolved_task = _resolve_task_name(task_name)
        return cls(client=client, task_name=resolved_task)

    async def reset(self, task_index: Optional[int] = None, seed: Optional[int] = None) -> _MyEnvV4Result:
        result = await self._client.reset(
            task_name=self._task_name,
            task_index=task_index,
            seed=seed,
        )
        task_description = result.observation.task_description.strip()
        self._last_prompt = task_description
        return _MyEnvV4Result(
            observation=_MyEnvV4Observation(echoed_message=task_description),
            reward=float(result.reward or 0.0),
            done=bool(result.done),
        )

    async def step(self, action: MyEnvV4Action) -> _MyEnvV4Result:
        code = _message_to_code(action.message)
        try:
            result = await self._client.step(ClinicalAction(code=code))
        except RuntimeError as exc:
            # Some OpenEnv runtimes may return a terminal EXECUTION_ERROR instead of a
            # final done=True step if the episode already closed on the server.
            if "Episode is over. Call reset() first." not in str(exc):
                raise

            state = await self._client.state()
            if not getattr(state, "done", False):
                raise

            return _MyEnvV4Result(
                observation=_MyEnvV4Observation(
                    echoed_message=self._last_prompt or "Episode ended on server."
                ),
                reward=0.0,
                done=True,
            )

        obs = result.observation

        echoed_message = obs.execution_result.strip()
        if not echoed_message:
            echoed_message = obs.error or self._last_prompt

        self._last_prompt = echoed_message
        return _MyEnvV4Result(
            observation=_MyEnvV4Observation(echoed_message=echoed_message),
            reward=float(result.reward or 0.0),
            done=bool(result.done),
        )

    async def close(self) -> None:
        await self._client.close()
