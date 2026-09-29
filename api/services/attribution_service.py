"""
Attribution Service.
Retrieves and validates Phase 4 candidate suspect vessel prioritization data.
"""

import json
from pathlib import Path
from typing import Any

from api.config import DATA_DIR, LEGAL_DISCLAIMER
from api.schemas.attribution import AttributionResponse, VesselCandidate
from api.services.event_service import EventService


class AttributionService:
    """Service managing vessel candidate attribution reports."""

    @classmethod
    def get_event_attribution(cls, event_id: str) -> AttributionResponse | None:
        """
        Load stored Phase 4 attribution results for an event.
        Returns None if event or attribution files do not exist.
        """
        if not EventService.get_event(event_id):
            return None

        attr_dir = DATA_DIR / "attribution" / event_id / "processed"
        cand_file = attr_dir / "vessel_candidates.json"
        meta_file = attr_dir / "attribution_metadata.json"

        if not cand_file.exists():
            return None

        try:
            with open(cand_file, "r", encoding="utf-8") as f:
                raw_candidates = json.load(f)

            is_synth = True
            model_used = "Phase 3 XGBoost Attribution Model"
            release_time = None

            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    is_synth = bool(meta.get("is_synthetic_ais_data", True))
                    model_used = str(meta.get("ranking_model_used", model_used))
                    release_time = meta.get("source_region_release_time")
                except Exception:
                    pass

            candidates: list[VesselCandidate] = []
            for cand in raw_candidates:
                candidates.append(
                    VesselCandidate(
                        vessel_id=str(cand.get("vessel_id", "")),
                        vessel_name=str(cand.get("vessel_name", "UNKNOWN")),
                        prioritization_score=float(cand.get("prioritization_score", 0.0)),
                        rank=int(cand.get("rank", len(candidates) + 1)),
                        min_distance_to_trajectory_km=float(cand.get("min_distance_to_trajectory_km", 0.0)),
                        min_distance_to_source_region_km=float(cand.get("min_distance_to_source_region_km", 0.0)),
                        temporal_offset_to_source_hours=float(cand.get("temporal_offset_to_source_hours", 0.0)),
                        data_mode=str(cand.get("data_mode", "synthetic" if is_synth else "operational")),
                        responsibility_confirmed=False,  # Explicit contract: legal confirmation is strictly false
                        features=cand.get("features", {}),
                        estimated_source_region=cand.get("estimated_source_region"),
                        disclaimer=LEGAL_DISCLAIMER,
                    )
                )

            return AttributionResponse(
                event_id=event_id,
                total_vessels_evaluated=len(candidates),
                is_synthetic_ais_data=is_synth,
                ranking_model_used=model_used,
                source_region_release_time=release_time,
                candidates=candidates,
                disclaimer=LEGAL_DISCLAIMER,
            )
        except Exception:
            return None
