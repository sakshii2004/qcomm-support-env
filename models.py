# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Qcomm Support Env Environment.

This environment simulates a Quick Commerce Logistics and Fraud Prevention
customer support agent.
"""

from typing import Literal, Dict, Any, Optional
from pydantic import Field
from openenv.core.env_server.types import Action, Observation, State


class QCommSupportObservation(Observation):
    """Observation representing the agent's view of the support ticket."""
    ticket_text: str = Field(default="", description="Customer's complaint text")
    customer_profile: Dict[str, Any] = Field(default_factory=dict, description="Customer metadata (e.g., tenure, R2O)")
    telemetry_data: Dict[str, Any] = Field(default_factory=dict, description="GPS and timing data if investigated")
    merchant_stats: Dict[str, Any] = Field(default_factory=dict, description="Store/merchant metrics if queried")
    environment_context: Dict[str, Any] = Field(default_factory=dict, description="Weather and delivery conditions")
    available_tools: list[str] = Field(
        default_factory=lambda: [
            "investigate_telemetry",
            "query_customer_history",
            "verify_content_evidence",
            "issue_resolution"
        ]
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional environment metadata (e.g., difficulty, flags)")



class QCommSupportAction(Action):
    """Action for the QComm Support Env environment."""
    action_type: Literal[
        "investigate_telemetry",
        "query_customer_history",
        "verify_content_evidence",
        "issue_resolution"
    ] = Field(..., description="Type of action to perform")
    
    resolution_type: Literal[
        "none",
        "refund_source",
        "partial_refund",
        "waive_delivery_fees",
        "replacement",
        "reject",
        "warn",
        "shadowban",
        "permaban",
        "escalate_to_human"
    ] = Field(default="none", description="Specific resolution if action_type is issue_resolution")


class QCommSupportState(State):
    """Internal state hidden from the agent."""
    actual_truth_status: bool = Field(default=True, description="Is the customer's claim actually valid?")
    fraud_probability: float = Field(default=0.0, description="Internal fraud probability calculation")
    task_difficulty: str = Field(default="easy", description="The current scenario difficulty")
    tools_called: list[str] = Field(default_factory=list, description="List of tools the agent has executed")
