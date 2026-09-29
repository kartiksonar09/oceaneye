"""
Drift Service.
Loads stored Phase 4 drift simulations and executes on-demand Lagrangian simulations.
"""

import json
from pathlib import Path
from typing import Any
import pandas as pd

from api.config import (
    DATA_DIR,
    DEFAULT_WINDAGE,
    DRIFT_SIMULATION_DISCLAIMER,
)
from api.schemas.drift import (
    DriftResponse,
    DriftSimulateRequest,
    DriftSimulateResponse,
)
from api.services.event_service import EventService
from api.utils.geojson import (
    source_region_to_polygon_feature,
    trajectory_to_linestring_feature,
)
from drift import (
    EnvironmentalForcing,
    simulate_backward_drift,
    simulate_forward_drift,
    simulate_particle_ensemble,
)


class DriftService:
    """Service managing Lagrangian drift trajectories and source estimation."""

    @classmethod
    def get_event_drift(cls, event_id: str) -> DriftResponse | None:
        """
        Load stored Phase 4 drift outputs for an event.
        Returns None if event or simulation outputs are missing.
        """
        # Validate event exists
        if not EventService.get_event(event_id):
            return None

        drift_dir = DATA_DIR / "drift" / event_id / "processed"
        fwd_file = drift_dir / "forward_trajectory.csv"
        bwd_file = drift_dir / "backward_trajectory.csv"
        src_file = drift_dir / "source_region.json"
        meta_file = drift_dir / "drift_metadata.json"

        if not fwd_file.exists() or not bwd_file.exists():
            return None

        # Read forward trajectory
        df_fwd = pd.read_csv(fwd_file)
        fwd_feature = trajectory_to_linestring_feature(
            df_fwd,
            properties={"event_id": event_id, "simulation_mode": "forward_drift"},
        )

        # Read backward trajectory
        df_bwd = pd.read_csv(bwd_file)
        bwd_feature = trajectory_to_linestring_feature(
            df_bwd,
            properties={"event_id": event_id, "simulation_mode": "backward_drift"},
        )

        # Read source region
        src_feature = None
        src_centroid = None
        dispersion_95 = None
        if src_file.exists():
            try:
                with open(src_file, "r", encoding="utf-8") as f:
                    src_data = json.load(f)
                hull_pts = src_data.get("polygon_convex_hull", [])
                src_feature = source_region_to_polygon_feature(
                    hull_pts,
                    properties={
                        "event_id": event_id,
                        "simulation_mode": "source_region_polygon",
                        "dispersion_radius_95_km": src_data.get("dispersion_radius_95_km"),
                    },
                )
                src_centroid = src_data.get("centroid")
                dispersion_95 = src_data.get("dispersion_radius_95_km")
            except Exception:
                pass

        # Read metadata if present
        timestep = 3600
        windage = DEFAULT_WINDAGE
        particles = 5
        fwd_hours = 6.0
        bwd_hours = 6.0
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                timestep = int(meta.get("timestep_seconds", timestep))
                windage = float(meta.get("windage_coefficient", windage))
                fwd_sim = meta.get("forward_simulation", {})
                bwd_sim = meta.get("backward_simulation", {})
                fwd_steps = fwd_sim.get("total_steps", 7)
                bwd_steps = bwd_sim.get("total_steps", 7)
                fwd_hours = round((fwd_steps - 1) * timestep / 3600.0, 1)
                bwd_hours = round((bwd_steps - 1) * timestep / 3600.0, 1)
            except Exception:
                pass

        return DriftResponse(
            event_id=event_id,
            forward_trajectory=fwd_feature,
            backward_trajectory=bwd_feature,
            source_region=src_feature,
            source_region_centroid=src_centroid,
            dispersion_radius_95_km=dispersion_95,
            timestep_seconds=timestep,
            windage_coefficient=windage,
            particle_count=particles,
            forward_duration_hours=fwd_hours,
            backward_duration_hours=bwd_hours,
            model_version="Phase 4 Lagrangian Transport v1.0",
            validation_data_mode="operational_forcing",
            disclaimer=DRIFT_SIMULATION_DISCLAIMER,
        )

    @classmethod
    def simulate_drift(cls, req: DriftSimulateRequest) -> DriftSimulateResponse:
        """
        Execute an on-demand Lagrangian forward and backward drift simulation.
        Safe, bounded execution with validated parameters.
        """
        # Resolve environmental forcing
        curr_path = None
        wind_path = None
        forcing_used = {"currents_available": False, "wind_available": False, "event_id": req.event_id}

        if req.event_id:
            cmems_proc = DATA_DIR / "cmems" / req.event_id / "processed"
            c_cand = cmems_proc / f"{req.event_id}_currents_processed.nc"
            w_cand = cmems_proc / f"{req.event_id}_wind_processed.nc"
            if c_cand.exists():
                curr_path = c_cand
                forcing_used["currents_available"] = True
            if w_cand.exists():
                wind_path = w_cand
                forcing_used["wind_available"] = True

        forcing = EnvironmentalForcing(currents_path=curr_path, wind_path=wind_path)

        # 1. Forward Drift
        df_fwd = simulate_forward_drift(
            start_lat=req.latitude,
            start_lon=req.longitude,
            start_time=req.timestamp,
            duration_hours=req.forward_duration_hours,
            timestep_seconds=req.timestep_seconds,
            forcing=forcing,
            windage=req.windage,
        )
        fwd_feature = trajectory_to_linestring_feature(
            df_fwd,
            properties={
                "type": "on_demand_forward_drift",
                "steps": len(df_fwd),
                "duration_hours": req.forward_duration_hours,
            },
        )

        # 2. Backward Drift
        df_bwd = simulate_backward_drift(
            start_lat=req.latitude,
            start_lon=req.longitude,
            start_time=req.timestamp,
            duration_hours=req.backward_duration_hours,
            timestep_seconds=req.timestep_seconds,
            forcing=forcing,
            windage=req.windage,
        )
        bwd_feature = trajectory_to_linestring_feature(
            df_bwd,
            properties={
                "type": "on_demand_backward_drift",
                "steps": len(df_bwd),
                "duration_hours": req.backward_duration_hours,
            },
        )

        # 3. Particle Ensemble for Source Region
        _, src_meta = simulate_particle_ensemble(
            start_lat=req.latitude,
            start_lon=req.longitude,
            start_time=req.timestamp,
            duration_hours=req.backward_duration_hours,
            timestep_seconds=req.timestep_seconds,
            forcing=forcing,
            num_particles=req.particle_count,
            windage_mean=req.windage,
        )

        hull_pts = src_meta.get("polygon_convex_hull", [])
        src_feature = source_region_to_polygon_feature(
            hull_pts,
            properties={
                "type": "on_demand_source_region_polygon",
                "particles": req.particle_count,
                "dispersion_radius_95_km": src_meta.get("dispersion_radius_95_km"),
            },
        )

        summary = {
            "forward_steps": len(df_fwd),
            "backward_steps": len(df_bwd),
            "ensemble_particles": req.particle_count,
            "source_centroid": src_meta.get("centroid"),
            "dispersion_radius_95_km": src_meta.get("dispersion_radius_95_km"),
        }

        return DriftSimulateResponse(
            is_simulation=True,
            simulation_type="on_demand_simulation",
            forward_trajectory=fwd_feature,
            backward_trajectory=bwd_feature,
            source_region=src_feature,
            summary=summary,
            forcing_used=forcing_used,
            disclaimer=DRIFT_SIMULATION_DISCLAIMER,
        )
