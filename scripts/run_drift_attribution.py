"""
OceanEye - Phase 4: Drift & Attribution Pipeline CLI Orchestrator
Connects Sentinel-1 spill detection with CMEMS currents/wind forcing, computes
forward/backward Lagrangian trajectories and ensemble source regions, correlates AIS
vessel movements, and scores candidate suspect vessels via the Phase 3 ranking model.
"""

import argparse
import datetime
import json
import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Add scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import PROJECT_ROOT, get_data_dir, get_event, setup_logging
from drift import (
    EnvironmentalForcing,
    calculate_trajectory_summary,
    correlate_and_rank_vessels,
    haversine_distance,
    simulate_backward_drift,
    simulate_forward_drift,
    simulate_particle_ensemble,
)
from processing.common import get_processed_dir, save_metadata


def print_header(event_name: str, event_info: dict[str, Any], spill_info: dict[str, Any]):
    print()
    print("=" * 80)
    print("OCEANEYE - DRIFT SIMULATION & VESSEL ATTRIBUTION PIPELINE (PHASE 4)")
    print("=" * 80)
    print(f"Target Event      : {event_info.get('name', event_name)} ({event_name})")
    print(f"Spill Coordinates : lat {spill_info['latitude']:.4f}, lon {spill_info['longitude']:.4f}")
    print(f"Detection Time    : {spill_info['timestamp']}")
    print(f"Detection Source  : {spill_info['detection_source']}")
    print("=" * 80)
    print()


def resolve_spill_detection(event_name: str, event_info: dict[str, Any], custom_source: str | None = None) -> dict[str, Any]:
    """
    Resolve detection coordinates and timestamp for the spill candidate.
    Prioritizes Sentinel-1 processed metadata, falls back to event config.
    """
    if custom_source:
        p = Path(custom_source)
        if p.exists() and p.suffix == ".json":
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "latitude": float(data.get("latitude", event_info["latitude"])),
                    "longitude": float(data.get("longitude", event_info["longitude"])),
                    "timestamp": data.get("timestamp") or f"{event_info['start_date']}T00:00:00Z",
                    "detection_source": f"Custom JSON ({p.name})",
                }

    # Check Sentinel-1 processed metadata
    sentinel_proc_dir = get_processed_dir("sentinel", event_name)
    sentinel_meta_file = sentinel_proc_dir / f"{event_name}_sentinel_metadata.json"

    if sentinel_meta_file.exists():
        try:
            with open(sentinel_meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                # Compute footprint center
                poly = meta.get("footprint_polygon", [])
                if poly:
                    avg_lat = float(np.mean([pt[0] for pt in poly]))
                    avg_lon = float(np.mean([pt[1] for pt in poly]))
                else:
                    avg_lat = float(event_info["latitude"])
                    avg_lon = float(event_info["longitude"])

                t_start = meta.get("temporal_coverage", {}).get("start")
                timestamp = t_start if t_start else f"{event_info['start_date']}T00:00:00Z"
                if not timestamp.endswith("Z") and "+" not in timestamp:
                    timestamp += "Z"

                return {
                    "latitude": round(avg_lat, 5),
                    "longitude": round(avg_lon, 5),
                    "timestamp": timestamp,
                    "detection_source": f"Sentinel-1 Metadata ({meta.get('product_id', 'SAFE')})",
                }
        except Exception:
            pass

    # Fallback to event configuration center
    return {
        "latitude": float(event_info["latitude"]),
        "longitude": float(event_info["longitude"]),
        "timestamp": f"{event_info['start_date']}T06:00:00Z",
        "detection_source": "Event Configuration (config/events.json)",
    }


def resolve_environmental_datasets(event_name: str) -> tuple[Path | None, Path | None]:
    """Resolve paths to processed CMEMS current and wind datasets."""
    cmems_proc_dir = get_processed_dir("cmems", event_name)

    curr_path = cmems_proc_dir / f"{event_name}_currents_processed.nc"
    if not curr_path.exists():
        raw_curr = get_data_dir("cmems", event_name) / f"{event_name}_currents.nc"
        curr_path = raw_curr if raw_curr.exists() else None

    wind_path = cmems_proc_dir / f"{event_name}_wind_processed.nc"
    if not wind_path.exists():
        raw_wind = get_data_dir("cmems", event_name) / f"{event_name}_wind.nc"
        wind_path = raw_wind if raw_wind.exists() else None

    return curr_path, wind_path


def load_or_generate_ais_data(
    event_name: str,
    event_info: dict[str, Any],
    spill_info: dict[str, Any],
    logger: logging.Logger,
) -> tuple[pd.DataFrame, bool]:
    """
    Load real cleaned AIS data if available.
    If unavailable or raw file contains API errors, generate a deterministic synthetic
    benchmark dataset for the event area to enable full pipeline verification.
    """
    ais_dir = get_data_dir("ais", event_name)
    candidates = list(ais_dir.glob("*.csv")) + list(ais_dir.glob("*.parquet"))

    valid_df: pd.DataFrame | None = None
    for cand in candidates:
        if cand.stat().st_size > 100:
            try:
                df = pd.read_csv(cand) if cand.suffix == ".csv" else pd.read_parquet(cand)
                if len(df) > 0 and "latitude" in df.columns and "longitude" in df.columns:
                    valid_df = df
                    break
            except Exception:
                continue

    if valid_df is not None:
        logger.info("Loaded operational AIS dataset with %d records from %s", len(valid_df), candidates[0])
        return valid_df, False

    # Deterministic synthetic benchmark generation for pipeline testing
    logger.info("No valid local AIS tabular records found. Generating synthetic test benchmark vessels.")
    rng = np.random.RandomState(42)

    spill_lat = spill_info["latitude"]
    spill_lon = spill_info["longitude"]
    spill_dt = pd.to_datetime(spill_info["timestamp"], utc=True)

    test_vessels = [
        # 1. Suspect vessel: traversed right through possible source zone around release time, sudden speed decrease
        {"mmsi": "353123000", "vessel_name": "MV PACIFIC VOYAGER", "behavior": "suspect"},
        # 2. Innocent transit vessel: passed 25 km north at constant cruising speed
        {"mmsi": "563987000", "vessel_name": "STAR HORIZON", "behavior": "transit_distant"},
        # 3. Loitering fishing vessel: erratic low speeds south of area
        {"mmsi": "645221000", "vessel_name": "OCEAN HARVESTER", "behavior": "fishing_near"},
        # 4. Cargo vessel: crossed area 36 hours prior to release window
        {"mmsi": "412554000", "vessel_name": "GLOBAL TRADER", "behavior": "transit_prior"},
    ]

    records = []
    for v in test_vessels:
        base_time = spill_dt - pd.Timedelta(hours=48)
        num_pings = rng.randint(25, 45)

        if v["behavior"] == "suspect":
            # Heading towards spill origin, drops speed from 14 knots to 2.5 knots near spill
            lats = np.linspace(spill_lat - 0.4, spill_lat + 0.1, num_pings)
            lons = np.linspace(spill_lon - 0.4, spill_lon + 0.1, num_pings)
            speeds = [13.5 if i < num_pings // 2 else 2.8 for i in range(num_pings)]
            courses = [42.0] * num_pings
        elif v["behavior"] == "transit_distant":
            # 25-35 km distant transit
            lats = np.linspace(spill_lat + 0.3, spill_lat + 0.35, num_pings)
            lons = np.linspace(spill_lon - 0.6, spill_lon + 0.6, num_pings)
            speeds = [16.2] * num_pings
            courses = [90.0] * num_pings
        elif v["behavior"] == "fishing_near":
            # Loitering 12 km south
            lats = spill_lat - 0.12 + rng.normal(0, 0.02, num_pings)
            lons = spill_lon + rng.normal(0, 0.02, num_pings)
            speeds = rng.uniform(2.0, 5.5, num_pings).tolist()
            courses = rng.uniform(0, 360, num_pings).tolist()
        else:
            # Crossed 36 hours earlier
            lats = np.linspace(spill_lat - 0.5, spill_lat + 0.5, num_pings)
            lons = np.linspace(spill_lon - 0.5, spill_lon + 0.5, num_pings)
            speeds = [14.0] * num_pings
            courses = [45.0] * num_pings

        for idx in range(num_pings):
            t_ping = base_time + pd.Timedelta(minutes=idx * 60)
            records.append({
                "mmsi": v["mmsi"],
                "vessel_name": v["vessel_name"],
                "latitude": round(float(lats[idx]), 5),
                "longitude": round(float(lons[idx]), 5),
                "timestamp": t_ping.isoformat(),
                "speed_knots": round(float(speeds[idx]), 2),
                "course_deg": round(float(courses[idx]), 1),
            })

    syn_df = pd.DataFrame(records)
    return syn_df, True


def run_pipeline(
    event_name: str = "wakashio",
    forward_hours: float = 24.0,
    backward_hours: float = 48.0,
    timestep_seconds: int = 1800,
    windage: float = 0.03,
    num_particles: int = 25,
    custom_source: str | None = None,
    overwrite: bool = False,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Execute complete Phase 4 Drift & Attribution Pipeline."""
    if logger is None:
        logger = setup_logging("run_drift_attribution")

    event_info = get_event(event_name)
    spill_info = resolve_spill_detection(event_name, event_info, custom_source)

    print_header(event_name, event_info, spill_info)

    # Output directories
    drift_out_dir = PROJECT_ROOT / "data" / "drift" / event_name / "processed"
    attr_out_dir = PROJECT_ROOT / "data" / "attribution" / event_name / "processed"
    drift_out_dir.mkdir(parents=True, exist_ok=True)
    attr_out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Environmental Forcing
    curr_file, wind_file = resolve_environmental_datasets(event_name)
    logger.info("Currents dataset path : %s", curr_file)
    logger.info("Wind dataset path     : %s", wind_file)

    forcing = EnvironmentalForcing(currents_path=curr_file, wind_path=wind_file, logger=logger)

    # 2. Forward Drift Simulation (Dispersion forecast)
    logger.info("Simulating forward drift trajectory (+%.1f hours)...", forward_hours)
    fwd_df = simulate_forward_drift(
        start_lat=spill_info["latitude"],
        start_lon=spill_info["longitude"],
        start_time=spill_info["timestamp"],
        duration_hours=forward_hours,
        timestep_seconds=timestep_seconds,
        forcing=forcing,
        windage=windage,
        logger=logger,
    )
    fwd_summary = calculate_trajectory_summary(fwd_df, mode="forward")
    fwd_path = drift_out_dir / "forward_trajectory.csv"
    fwd_df.to_csv(fwd_path, index=False)

    # 3. Backward Drift Simulation (Deterministic origin trace)
    logger.info("Simulating backward drift trajectory (-%.1f hours)...", backward_hours)
    bwd_df = simulate_backward_drift(
        start_lat=spill_info["latitude"],
        start_lon=spill_info["longitude"],
        start_time=spill_info["timestamp"],
        duration_hours=backward_hours,
        timestep_seconds=timestep_seconds,
        forcing=forcing,
        windage=windage,
        logger=logger,
    )
    bwd_summary = calculate_trajectory_summary(bwd_df, mode="backward")
    bwd_path = drift_out_dir / "backward_trajectory.csv"
    bwd_df.to_csv(bwd_path, index=False)

    # 4. Backward Particle Ensemble & Source Region Estimation
    logger.info("Simulating Monte Carlo ensemble (%d particles) for source localization...", num_particles)
    ensemble_df, source_region_meta = simulate_particle_ensemble(
        start_lat=spill_info["latitude"],
        start_lon=spill_info["longitude"],
        start_time=spill_info["timestamp"],
        duration_hours=backward_hours,
        timestep_seconds=timestep_seconds,
        forcing=forcing,
        num_particles=num_particles,
        windage_mean=windage,
        seed=42,
        logger=logger,
    )
    ens_path = drift_out_dir / "ensemble_trajectories.csv"
    ensemble_df.to_csv(ens_path, index=False)

    src_region_path = drift_out_dir / "source_region.json"
    with open(src_region_path, "w", encoding="utf-8") as f:
        json.dump(source_region_meta, f, indent=2)

    drift_metadata = {
        "event": event_name,
        "spill_detection": spill_info,
        "windage_coefficient": windage,
        "timestep_seconds": timestep_seconds,
        "forward_simulation": fwd_summary,
        "backward_simulation": bwd_summary,
        "source_region_centroid": source_region_meta["centroid"],
        "source_region_dispersion_radius_95_km": source_region_meta["dispersion_radius_95_km"],
        "environmental_forcing": {
            "currents_dataset": str(curr_file),
            "wind_dataset": str(wind_file),
            "currents_available": forcing.is_currents_available(),
            "wind_available": forcing.is_wind_available(),
        },
        "disclaimer": (
            "NOTICE: The forward/backward drift trajectories represent simplified Lagrangian transport "
            "(current + 3% wind leeway) for investigatory screening. They do not replace operational hydrodynamic modeling."
        ),
    }
    drift_meta_path = drift_out_dir / "drift_metadata.json"
    save_metadata(drift_metadata, drift_meta_path)

    # 5. AIS Vessel Correlation & Phase 3 Attribution Scoring
    logger.info("Correlating AIS vessel tracking data with estimated drift and source region...")
    ais_df, is_synthetic_ais = load_or_generate_ais_data(event_name, event_info, spill_info, logger)

    phase3_model_path = PROJECT_ROOT / "models" / "ranking" / "vessel_ranking_model.json"
    features_df, ranked_candidates = correlate_and_rank_vessels(
        vessels_df=ais_df,
        backward_trajectory_df=bwd_df,
        source_region_meta=source_region_meta,
        model_path=phase3_model_path if phase3_model_path.exists() else None,
        logger=logger,
    )

    vessel_feats_path = attr_out_dir / "vessel_features.csv"
    features_df.to_csv(vessel_feats_path, index=False)

    candidates_path = attr_out_dir / "vessel_candidates.json"
    with open(candidates_path, "w", encoding="utf-8") as f:
        json.dump(ranked_candidates, f, indent=2)

    attr_metadata = {
        "event": event_name,
        "spill_detection": spill_info,
        "is_synthetic_ais_data": is_synthetic_ais,
        "total_vessels_evaluated": len(ranked_candidates),
        "source_region_release_time": source_region_meta["estimated_release_timestamp"],
        "ranking_model_used": "Phase 3 XGBoost Attribution Model" if phase3_model_path.exists() else "Empirical Heuristic Fallback",
        "ranked_vessel_ids": [c["vessel_id"] for c in ranked_candidates],
        "top_ranked_vessel": ranked_candidates[0] if ranked_candidates else None,
        "disclaimer": (
            "LEGAL DISCLAIMER: Vessel prioritization scores indicate trajectory and kinematic correlation. "
            "A high score or top rank DOES NOT constitute proof of responsibility or legal fault for oil discharge."
        ),
    }
    attr_meta_path = attr_out_dir / "attribution_metadata.json"
    save_metadata(attr_metadata, attr_meta_path)

    forcing.close()

    # Summary Report
    print("=" * 80)
    print("PHASE 4 DRIFT & ATTRIBUTION SUMMARY REPORT")
    print("=" * 80)
    print(f"Forward Drift Distance  : {fwd_summary.get('cumulative_path_km', 0.0):.2f} km over {forward_hours:.1f} hours")
    print(f"Backward Backtrack Path : {bwd_summary.get('cumulative_path_km', 0.0):.2f} km over {backward_hours:.1f} hours")
    print(f"Possible Source Centroid: lat {source_region_meta['centroid']['latitude']:.4f}, lon {source_region_meta['centroid']['longitude']:.4f}")
    print(f"Estimated Release Time  : {source_region_meta['estimated_release_timestamp']}")
    print(f"Source 95% Dispersion   : {source_region_meta['dispersion_radius_95_km']:.2f} km radius")
    print("-" * 80)
    print(f"Vessels Evaluated       : {len(ranked_candidates)} ({'SYNTHETIC BENCHMARK' if is_synthetic_ais else 'REAL AIS'})")

    if ranked_candidates:
        print("\nTOP CANDIDATE VESSELS PRIORITIZATION:")
        print(f"{'Rank':<5} {'MMSI':<12} {'Vessel Name':<22} {'Score':<8} {'Dist to Traj':<14} {'Dist to Source':<15}")
        print("-" * 80)
        for cand in ranked_candidates[:5]:
            print(
                f"{cand['rank']:<5} {cand['vessel_id']:<12} {cand['vessel_name']:<22} "
                f"{cand['prioritization_score']:<8.4f} "
                f"{cand['min_distance_to_trajectory_km']:<14.2f} "
                f"{cand['min_distance_to_source_region_km']:<15.2f}"
            )

    print()
    print("Structured Artifacts Generated:")
    print(f"  - Forward Trajectory     : {fwd_path}")
    print(f"  - Backward Trajectory    : {bwd_path}")
    print(f"  - Ensemble Trajectories  : {ens_path}")
    print(f"  - Source Region Polygon  : {src_region_path}")
    print(f"  - Candidate Features CSV : {vessel_feats_path}")
    print(f"  - Ranked Candidates JSON : {candidates_path}")
    print("=" * 80)
    print("SCIENTIFIC SAFETY NOTICE:")
    print("All trajectories and source regions are research approximations. Prioritization ranks")
    print("serve solely to focus maritime authority inspections and do NOT establish causation.")
    print("=" * 80)

    return {
        "status": "success",
        "event": event_name,
        "forward_path": str(fwd_path),
        "backward_path": str(bwd_path),
        "source_region_path": str(src_region_path),
        "candidates_path": str(candidates_path),
        "ranked_candidates": ranked_candidates,
    }


def main():
    parser = argparse.ArgumentParser(
        description="OceanEye Phase 4: Drift Simulation & Vessel Attribution Pipeline"
    )

    parser.add_argument("--event", default="wakashio", help="Target event from config/events.json (default: wakashio)")
    parser.add_argument("--forward-hours", type=float, default=24.0, help="Forward simulation hours (default: 24.0)")
    parser.add_argument("--backward-hours", type=float, default=48.0, help="Backward simulation hours (default: 48.0)")
    parser.add_argument("--timestep", type=int, default=1800, help="Numerical integration timestep in seconds (default: 1800)")
    parser.add_argument("--windage", type=float, default=0.03, help="Windage leeway drift coefficient (default: 0.03)")
    parser.add_argument("--particles", type=int, default=25, help="Number of particles in Monte Carlo ensemble (default: 25)")
    parser.add_argument("--source", default=None, help="Custom spill detection JSON path")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing processed outputs")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level")

    args = parser.parse_args()

    logger = setup_logging("drift_attribution", args.log_level)

    try:
        run_pipeline(
            event_name=args.event,
            forward_hours=args.forward_hours,
            backward_hours=args.backward_hours,
            timestep_seconds=args.timestep,
            windage=args.windage,
            num_particles=args.particles,
            custom_source=args.source,
            overwrite=args.overwrite,
            logger=logger,
        )
    except Exception as exc:
        logger.error("Drift and attribution pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
