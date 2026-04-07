import json
from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

try:
    from .models import QCommSupportAction, QCommSupportObservation, QCommSupportState
except ImportError:
    from models import QCommSupportAction, QCommSupportObservation, QCommSupportState

class QcommSupportEnv(EnvClient[QCommSupportAction, QCommSupportObservation, QCommSupportState]):
    """Client for the QComm Support Env Environment."""

    def _step_payload(self, action: QCommSupportAction) -> Dict:
        # Convert Pydantic object to dict
        return action.model_dump()

    def _parse_result(self, payload: Dict) -> StepResult[QCommSupportObservation]:
        obs_data = payload.get("observation", {})
        
        # Extract fields matching QCommSupportObservation
        observation = QCommSupportObservation(
            ticket_text=obs_data.get("ticket_text", ""),
            customer_profile=obs_data.get("customer_profile", {}),
            telemetry_data=obs_data.get("telemetry_data", {}),
            merchant_stats=obs_data.get("merchant_stats", {}),
            environment_context=obs_data.get("environment_context", {}),
            available_tools=obs_data.get("available_tools", []),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> QCommSupportState:
        return QCommSupportState(
            episode_id=payload.get("episode_id", "none"),
            step_count=payload.get("step_count", 0),
            actual_truth_status=payload.get("actual_truth_status", True),
            fraud_probability=payload.get("fraud_probability", 0.0),
            task_difficulty=payload.get("task_difficulty", "easy"),
            tools_called=payload.get("tools_called", []),
        )
