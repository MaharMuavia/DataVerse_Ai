"""DataManager: single source of truth for dataset lifecycle.

This implementation gets dataframes from persistent session state.
"""
from __future__ import annotations

import pandas as pd
from typing import Optional

from ..core.logger import logger
from ..core.exceptions import DataNotFoundError, DataLoadError
from .dataset_profile import DatasetProfile


class DataManager:
    """Manages dataset storage and lifecycle.

    Gets dataframes from persistent session state for production readiness.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    def save_raw(self, df: pd.DataFrame) -> None:
        """Save raw dataframe to session state."""
        if not isinstance(df, pd.DataFrame):
            raise DataLoadError("Provided data is not a pandas DataFrame")

        from ..state.persistent_session_state import session_manager
        session_state = session_manager.get_session(self.session_id)
        session_state.set("raw_dataframe", df.copy())
        logger.info("Raw dataset saved to session", extra={"session_id": self.session_id, "rows": len(df)})

    def get_raw(self) -> pd.DataFrame:
        """Get raw dataframe from session state."""
        from ..state.persistent_session_state import session_manager
        session_state = session_manager.get_session(self.session_id)
        df = session_state.get_value("raw_dataframe")
        if df is None:
            raise DataNotFoundError("Raw dataset not found for session")
        return df.copy()

    def save_cleaned(self, df: pd.DataFrame) -> None:
        """Save cleaned dataframe to session state."""
        if not isinstance(df, pd.DataFrame):
            raise DataLoadError("Provided data is not a pandas DataFrame")

        from ..state.persistent_session_state import session_manager
        session_state = session_manager.get_session(self.session_id)
        session_state.set("cleaned_dataframe", df.copy())
        logger.info("Cleaned dataset saved to session", extra={"session_id": self.session_id, "rows": len(df)})

    def get_cleaned(self) -> pd.DataFrame:
        """Get cleaned dataframe from session state, fallback to raw."""
        from ..state.persistent_session_state import session_manager
        session_state = session_manager.get_session(self.session_id)
        df = session_state.get_value("cleaned_dataframe")
        if df is None:
            # Fallback to raw if no cleaned version
            df = session_state.get_value("raw_dataframe")
        if df is None:
            raise DataNotFoundError("Dataset not found for session")
        return df.copy()
        return df.copy()

    def generate_profile(self) -> DatasetProfile:
        df = self.get_raw()
        profile = DatasetProfile(df)
        profile.compute_profile()
        logger.info("Profile generated", extra={"session_id": self.session_id})
        return profile
