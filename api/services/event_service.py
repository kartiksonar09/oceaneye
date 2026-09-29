"""
Event Service.
Reads and validates event configurations from config/events.json.
"""

import json
from pathlib import Path
from typing import Any

from api.config import CONFIG_DIR, DATA_DIR, EVENTS_FILE
from api.schemas.events import EventDetail, EventSummary
from common import get_event_bbox


class EventService:
    """Service managing OceanEye incident events."""

    @staticmethod
    def load_raw_events() -> dict[str, dict[str, Any]]:
        """Load all events from config/events.json."""
        if not EVENTS_FILE.exists():
            return {}
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @classmethod
    def list_events(cls) -> list[EventSummary]:
        """Return list of all configured events."""
        raw_events = cls.load_raw_events()
        summaries = []
        for event_id, info in raw_events.items():
            summaries.append(
                EventSummary(
                    event_id=event_id,
                    name=info.get("name", event_id),
                    latitude=float(info.get("latitude", 0.0)),
                    longitude=float(info.get("longitude", 0.0)),
                    start_date=str(info.get("start_date", "")),
                    end_date=str(info.get("end_date", "")),
                    radius_km=float(info.get("radius_km", 100.0)),
                )
            )
        return summaries

    @classmethod
    def get_event(cls, event_id: str) -> EventDetail | None:
        """Get event details by ID, or None if not found."""
        raw_events = cls.load_raw_events()
        if event_id not in raw_events:
            return None

        info = raw_events[event_id]
        min_lon, max_lon, min_lat, max_lat = get_event_bbox(info)

        # Check data availability across pipelines
        sentinel_dir = DATA_DIR / "sentinel" / event_id / "processed"
        sentinel_meta = sentinel_dir / f"{event_id}_sentinel_metadata.json"
        
        cmems_dir = DATA_DIR / "cmems" / event_id / "processed"
        cmems_curr = cmems_dir / f"{event_id}_currents_processed.nc"
        
        drift_dir = DATA_DIR / "drift" / event_id / "processed"
        drift_fwd = drift_dir / "forward_trajectory.csv"
        
        attr_dir = DATA_DIR / "attribution" / event_id / "processed"
        attr_candidates = attr_dir / "vessel_candidates.json"

        data_avail = {
            "sentinel": sentinel_meta.exists(),
            "cmems": cmems_curr.exists(),
            "drift": drift_fwd.exists(),
            "attribution": attr_candidates.exists(),
        }

        return EventDetail(
            event_id=event_id,
            name=info.get("name", event_id),
            latitude=float(info.get("latitude", 0.0)),
            longitude=float(info.get("longitude", 0.0)),
            start_date=str(info.get("start_date", "")),
            end_date=str(info.get("end_date", "")),
            radius_km=float(info.get("radius_km", 100.0)),
            bounding_box={
                "min_lon": min_lon,
                "max_lon": max_lon,
                "min_lat": min_lat,
                "max_lat": max_lat,
            },
            data_availability=data_avail,
        )
