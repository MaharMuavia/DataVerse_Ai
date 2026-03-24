"""DataManager: single source of truth for dataset lifecycle.

This implementation stores dataframes in-memory keyed by session id. In production, replace with persistent storage.
"""
from __future__ import annotations

import pandas as pd
from typing import Optional

from ..core.logger import logger
from ..core.exceptions import DataNotFoundError, DataLoadError
from .dataset_profile import DatasetProfile


class DataManager:
    """Manages dataset storage and lifecycle.

    For the project scope we maintain in-memory storage for clarity and extensibility. The class
    provides methods to load CSVs, access raw/cleaned versions, and generate profiles.
    """

    _RAW_STORE: dict[str, pd.DataFrame] = {}
    _CLEAN_STORE: dict[str, pd.DataFrame] = {}

    def __init__(self, session_id: str):
        self.session_id = session_id

    def save_raw(self, df: pd.DataFrame) -> None:
        if not isinstance(df, pd.DataFrame):
            raise DataLoadError("Provided data is not a pandas DataFrame")
        # Make a defensive copy to avoid side-effects
        self._RAW_STORE[self.session_id] = df.copy()
        logger.info("Raw dataset saved", extra={"session_id": self.session_id, "rows": len(df)})

    def get_raw(self) -> pd.DataFrame:
        df = self._RAW_STORE.get(self.session_id)
        if df is None:
            raise DataNotFoundError("Raw dataset not found for session")
        return df.copy()

    def save_cleaned(self, df: pd.DataFrame) -> None:
        if not isinstance(df, pd.DataFrame):
            raise DataLoadError("Provided data is not a pandas DataFrame")
        self._CLEAN_STORE[self.session_id] = df.copy()
        logger.info("Cleaned dataset saved", extra={"session_id": self.session_id, "rows": len(df)})

    def get_cleaned(self) -> pd.DataFrame:
        df = self._CLEAN_STORE.get(self.session_id)
        if df is None:
            raise DataNotFoundError("Cleaned dataset not found for session")
        return df.copy()

    def generate_profile(self) -> DatasetProfile:
        df = self.get_raw()
        profile = DatasetProfile(df)
        profile.compute_profile()
        logger.info("Profile generated", extra={"session_id": self.session_id})
        return profile
