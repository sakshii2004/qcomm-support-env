import os
import random
from uuid import uuid4
from typing import Optional, Dict, Any

from openenv.core.env_server.interfaces import Environment

try:
    from ..models import (
        QCommSupportAction, 
        QCommSupportObservation, 
        QCommSupportState
    )
except ImportError:
    from models import (
        QCommSupportAction, 
        QCommSupportObservation, 
        QCommSupportState
    )

class QcommSupportEnvironment(Environment):
    """
    QComm Support Agent Environment.
    Standardized High-Fidelity Logistic Support Simulation.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True
    
    # Class-level counter for round-robin task selection
    _task_counter: int = 0

    # Generic resolution families — NOT task-specific grading.
    # Groups resolutions that belong to the same logical outcome.
    RESOLUTION_FAMILIES = {
        "refund_source":  ["refund_source", "partial_refund"],
        "partial_refund": ["partial_refund", "refund_source"],
        "replacement":    ["replacement"],
        "reject":         ["reject", "warn"],
        "permaban":       ["permaban", "shadowban"],
    }

    def __init__(self):
        self._state = QCommSupportState(
            episode_id=str(uuid4()), 
            step_count=0,
            actual_truth_status=True,
            fraud_probability=0.0,
            task_difficulty="easy",
            tools_called=[],
        )
        self._reset_count = 0

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> QCommSupportObservation:
        """Reset the environment to one of 5 standardized scenarios."""
        tasks = ["very_easy", "easy", "medium", "hard", "very_hard"]
        difficulty = tasks[QcommSupportEnvironment._task_counter % 5]
        QcommSupportEnvironment._task_counter += 1

        self._state = QCommSupportState(
            episode_id=str(uuid4()), 
            step_count=0,
            task_difficulty=difficulty,
            tools_called=[],
            fraud_probability=0.0,
        )
        self._reset_count += 1
        
        # Base Coordinates (Middle of Bangalore, India)
        BASE_LAT, BASE_LON = 12.9716, 77.5946

        # --- UNIVERSAL KEY SCHEMA ---
        def create_telemetry(dist, geofence, rider_lat, rider_lon, tamper=False):
            return {
                "delivery_distance_m": dist,
                "rider_geofence_status": geofence,
                "raw_gps_delivery": [BASE_LAT, BASE_LON],
                "raw_gps_rider": [rider_lat, rider_lon],
                "device_tamper_flag": tamper
            }

        def create_context(gps_match, sentiment, labels=None):
            return {
                "photo_gps_match": gps_match,
                "sentiment": sentiment,
                "image_labels": labels or []
            }

        # --- SCENARIO DATA ---
        if difficulty == "very_easy":
            # Damaged Item (Legit)
            self._state.actual_truth_status = True
            self._current_profile = {"r2o_rate": 0.05, "tenure_days": 120, "device_trust": "medium"}
            # Jitter: ~8m offset
            self._current_telemetry = create_telemetry(7.5, "inside", BASE_LAT + 0.00007, BASE_LON + 0.00002)
            self._current_merchant = {"reliability_score": 0.95, "incident_rate": 0.02}
            self._current_content = create_context(True, "curious", ["leaking_milk"])
            ticket_text = (
                "The milk carton I received is leaking and the whole bag is wet. "
                "I tried requesting a replacement in the app but it said 'Manual verification required - please contact support'. "
                "The app said you need to verify my delivery details and the photo I uploaded. Can you do that and send a replacement?"
            )
            self._correct_resolution = "replacement"

        elif difficulty == "easy":
            # Missing Item (Legit) — but customer profile looks SUSPICIOUS.
            # High r2o (0.15), very low tenure (20 days), threatening tone.
            # GPS + photo confirm delivery. Correct: partial_refund (small ₹20 item,
            # borderline profile warrants caution — not a full source refund).
            self._state.actual_truth_status = True
            self._current_profile = {"r2o_rate": 0.15, "tenure_days": 20, "device_trust": "medium"}
            # Jitter: ~3m offset
            self._current_telemetry = create_telemetry(3.2, "inside", BASE_LAT - 0.00002, BASE_LON + 0.00001)
            self._current_merchant = {"reliability_score": 0.82, "incident_rate": 0.09}
            self._current_content = create_context(True, "angry", ["chips_packet_missing_among_items"])
            ticket_text = (
                "My ₹20 chips packet is missing from the order AGAIN. This is the THIRD time this month! "
                "I want a full refund right now or I will file a complaint with consumer court and post on social media!"
            )
            self._correct_resolution = "partial_refund"

        elif difficulty == "medium":
            # EXTREME RED HERRING: Customer looks like the WORST kind of fraudster.
            # BUT merchant is ABYSMAL. Correct: partial_refund (merchant fault, but customer's
            # extreme ₹15,000 carpet compensation demand is beyond a standard full refund).
            self._state.actual_truth_status = True
            self._current_profile = {"r2o_rate": 0.35, "tenure_days": 7, "device_trust": "low"}
            # Jitter: ~12m offset — GPS is still inside
            self._current_telemetry = create_telemetry(11.8, "inside", BASE_LAT + 0.0001, BASE_LON - 0.00005)
            self._current_merchant = {"reliability_score": 0.38, "incident_rate": 0.52}
            self._current_content = create_context(False, "threatening", ["soaked_blue_carpet"])
            ticket_text = (
                "The detergent bottle was COMPLETELY EMPTY when I received it and the liquid RUINED my ₹15,000 carpet! "
                "I DEMAND a full refund AND compensation for my carpet RIGHT NOW! "
                "If you don't resolve this I will SUE your company and take this to the media! "
                "This is the WORST service I have EVER seen!"
            )
            self._correct_resolution = "partial_refund"

        elif difficulty == "hard":
            # EMPATHY TRAP FRAUD: Customer sounds like a genuine, polite victim but is actually fraudulent.
            # Moderate profile (r2o 0.22, 25 days), 350m GPS offset, outside geofence, no photo match.
            # Customer tells a relatable story — model must resist empathy and reject.
            self._state.actual_truth_status = False 
            self._current_profile = {"r2o_rate": 0.22, "tenure_days": 25, "device_trust": "medium"}
            self._current_telemetry = create_telemetry(350.0, "outside", BASE_LAT + 0.003, BASE_LON - 0.001)
            self._current_merchant = {"reliability_score": 0.94, "incident_rate": 0.03}
            self._current_content = create_context(False, "sad", None)
            ticket_text = (
                "Hi, I'm a college student and I saved up to order birthday supplies for my roommate (₹800 order). "
                "The rider marked it as delivered but I was home the whole time and nothing arrived. "
                "I can't afford to reorder. Could you please help me with a refund? I'd really appreciate it."
            )
            self._correct_resolution = "reject"

        elif difficulty == "very_hard":
            # BORDERLINE LOCATION: Rider at the wrong gate. Subtle fraud.
            self._state.actual_truth_status = False # Potential Fraud or Lazy Rider
            self._current_profile = {"r2o_rate": 0.15, "tenure_days": 30, "device_trust": "medium"}
            # 110m Offset: Technically at the apartment gate, but not the door.
            self._current_telemetry = create_telemetry(110.0, "outside", BASE_LAT + 0.001, BASE_LON + 0.0002)
            self._current_merchant = {"reliability_score": 0.92, "incident_rate": 0.04}
            self._current_content = create_context(False, "neutral", None)
            ticket_text = "Rider never showed up but marked the order as delivered. I want my ₹400 refund back now."
            self._correct_resolution = "reject"
        
        return QCommSupportObservation(
            ticket_text=ticket_text,
            reward=0.0,
            done=False,
            metadata={"difficulty": difficulty, "message": "New support ticket received."}
        )

    def step(self, action: QCommSupportAction) -> QCommSupportObservation:
        self._state.step_count += 1
        
        obs = QCommSupportObservation(
            ticket_text="[Active Ticket]",
            reward=0.0,
            done=False,
            metadata={}
        )

        action_type = action.action_type
        
        # Universal Discovery Reward: +0.1 per unique tool
        investigation_tools = ["investigate_telemetry", "query_customer_history", "verify_content_evidence"]
        if action_type in investigation_tools:
            if action_type not in self._state.tools_called:
                self._state.tools_called.append(action_type)
                obs.reward = 0.1
            else:
                obs.reward = -0.05

        # Execute Tool Content
        if action_type == "investigate_telemetry":
            obs.telemetry_data = self._current_telemetry
        elif action_type == "query_customer_history":
            obs.customer_profile = self._current_profile
        elif action_type == "verify_content_evidence":
            obs.environment_context = self._current_content
            obs.merchant_stats = self._current_merchant
        
        # Universal Resolution Logic
        elif action_type == "issue_resolution":
            obs.done = True
            
            # --- Resolution Accuracy (family-based partial credit) ---
            family = self.RESOLUTION_FAMILIES.get(self._correct_resolution, [])
            if action.resolution_type == self._correct_resolution:
                obs.reward = 0.7   # Exact match
            elif action.resolution_type in family:
                obs.reward = 0.4   # Same family — partial credit
            else:
                obs.reward = 0.0   # Wrong family

            # --- Investigation Depth (graduated, replaces cliff penalty) ---
            tools_used = len(self._state.tools_called)
            if tools_used == 0:
                obs.reward -= 0.3   # Pure guess
            elif tools_used == 1:
                obs.reward -= 0.1   # Minimal investigation
            elif tools_used >= 3:
                obs.reward += 0.1   # Thorough investigation bonus
            # tools_used == 2 → no adjustment (acceptable)
            
            # Security Lockdown: Profit Leakage is a total failure
            is_fraud_scenario = (not self._state.actual_truth_status)
            if is_fraud_scenario and action.resolution_type in ["refund_source", "replacement", "partial_refund"]:
                obs.reward = -0.5
            
        return obs

    @property
    def state(self) -> QCommSupportState:
        return self._state
