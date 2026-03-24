"""IngestionAgent: orchestrates dataset ingestion and profiling."""
from __future__ import annotations

from typing import Dict, Any

from .base_agent import BaseAgent
from ..data.data_manager import DataManager
from ..state.session_state import SessionState


class IngestionAgent(BaseAgent):
    """Responsible for accepting a dataset from DataManager, generating profiles, and saving
    profile information to session state.

    The agent intentionally focuses on metadata and reasoning about the dataset rather than
    performing any data cleaning. Cleaning decisions belong to the PreprocessingAgent.
    """

    def __init__(self, session_id: str):
        super().__init__(name="ingestion_agent", description="Loads dataset and creates profile", session_id=session_id)

    def run(self) -> Dict[str, Any]:
        dm = DataManager(session_id=self.session_id)
        profile = dm.generate_profile()

        # Save profile to session state
        state = SessionState.get(self.session_id)
        state.set("profile", profile.to_dict())
        self.log_action("ingested_dataset", {"profile_summary": profile.to_dict()})
        return {"status": "success", "profile": profile.to_dict()}
