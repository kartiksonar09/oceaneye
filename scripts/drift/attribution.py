"""
OceanEye AIS Trajectory Correlation & Vessel Attribution Layer
Correlates vessel AIS tracks with backward drift trajectories and estimated source regions,
extracts convergence metrics, and integrates with the Phase 3 XGBoost ranking model.
"""

import datetime
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from common import setup_logging
from drift.geo import calculate_bearing, haversine_distance, point_to_trajectory_distance
from models.ranking.features import RANKING_FEATURE_NAMES
from models.ranking.inference import LEGAL_INVESTIGATORY_DISCLAIMER, load_ranking_model, predict_vessel_scores


def correlate_vessel_with_drift(
    vessel_points: pd.DataFrame | list[dict[str, Any]],
    backward_trajectory_df: pd.DataFrame,
    source_region_meta: dict[str, Any],
) -> dict[str, Any]:
    """
    Extract spatial, temporal, and kinematic correlation features between
    a vessel's AIS trajectory and the estimated backward drift trajectory / source region.
    """
    if isinstance(vessel_points, list):
        df_v = pd.DataFrame(vessel_points)
    else:
        df_v = vessel_points.copy()

    if df_v.empty or "latitude" not in df_v.columns or "longitude" not in df_v.columns:
        return {feat: 0.0 for feat in RANKING_FEATURE_NAMES}

    # Normalize vessel timestamps
    if "timestamp" in df_v.columns:
        df_v["dt"] = pd.to_datetime(df_v["timestamp"], utc=True)
    else:
        df_v["dt"] = pd.Timestamp.now(tz="UTC")

    # Source region parameters
    src_centroid = source_region_meta.get("centroid", {})
    src_lat = float(src_centroid.get("latitude", 0.0))
    src_lon = float(src_centroid.get("longitude", 0.0))
    src_radius_km = float(source_region_meta.get("dispersion_radius_95_km", 10.0))
    src_time_str = source_region_meta.get("estimated_release_timestamp")
    src_dt = pd.to_datetime(src_time_str, utc=True) if src_time_str else df_v["dt"].min()

    detection_point = source_region_meta.get("detection_point", {})
    spill_lat = float(detection_point.get("latitude", src_lat))
    spill_lon = float(detection_point.get("longitude", src_lon))

    # 1. Proximity to Estimated Backward Trajectory
    min_dist_to_traj_km = float("inf")
    closest_traj_time = None

    for _, v_row in df_v.iterrows():
        t_res = point_to_trajectory_distance(v_row["latitude"], v_row["longitude"], backward_trajectory_df)
        if t_res["min_distance_km"] < min_dist_to_traj_km:
            min_dist_to_traj_km = t_res["min_distance_km"]
            closest_traj_time = t_res["closest_timestamp"]

    if np.isinf(min_dist_to_traj_km):
        min_dist_to_traj_km = 999.0

    # 2. Proximity to Estimated Source Region
    distances_to_source = [
        haversine_distance(row["latitude"], row["longitude"], src_lat, src_lon)
        for _, row in df_v.iterrows()
    ]
    min_dist_to_src_km = float(min(distances_to_source))

    # Time difference to estimated release time
    time_diffs_source_hours = [
        abs((row["dt"] - src_dt).total_seconds()) / 3600.0
        for _, row in df_v.iterrows()
    ]
    min_time_offset_hours = float(min(time_diffs_source_hours))
    closest_src_idx = int(np.argmin(time_diffs_source_hours))
    dist_at_release_time = float(distances_to_source[closest_src_idx])

    # Time spent near source region (within 95% dispersion radius)
    near_source_rows = df_v[np.array(distances_to_source) <= src_radius_km]
    if len(near_source_rows) >= 2:
        t_span = (near_source_rows["dt"].max() - near_source_rows["dt"].min()).total_seconds() / 3600.0
        time_near_src_hours = float(round(t_span, 2))
    elif len(near_source_rows) == 1:
        time_near_src_hours = 0.5  # discrete ping approximation
    else:
        time_near_src_hours = 0.0

    # 3. Proximity Exponential Decay Scores
    traj_prox = float(np.exp(-min_dist_to_traj_km / 20.0))
    temp_prox = float(np.exp(-min_time_offset_hours / 12.0))
    src_prox = float(np.exp(-min_dist_to_src_km / max(src_radius_km, 5.0)))

    # 4. Kinematics (Speed & Heading)
    speed_col = "speed_knots" if "speed_knots" in df_v.columns else ("speed" if "speed" in df_v.columns else None)
    if speed_col and not df_v[speed_col].isna().all():
        speeds = df_v[speed_col].dropna().astype(float).values
        mean_spd = float(np.mean(speeds))
        var_spd = float(np.var(speeds))
        min_spd = float(np.min(speeds))
        max_spd = float(np.max(speeds))
        spd_anomaly = float((max_spd - min_spd) / (max_spd + 1e-3))
    else:
        mean_spd = 10.0
        var_spd = 0.0
        spd_anomaly = 0.0

    # Heading deviation relative to source region bearing
    course_col = "course_deg" if "course_deg" in df_v.columns else ("heading_deg" if "heading_deg" in df_v.columns else None)
    if course_col and not df_v[course_col].isna().all():
        closest_row = df_v.iloc[int(np.argmin(distances_to_source))]
        v_course = float(closest_row[course_col])
        bearing_to_src = calculate_bearing(closest_row["latitude"], closest_row["longitude"], src_lat, src_lon)
        heading_dev = float(abs((v_course - bearing_to_src + 180.0) % 360.0 - 180.0))
    else:
        heading_dev = 90.0

    return {
        # Phase 4 Detailed Correlation Metrics
        "min_distance_to_trajectory_km": round(min_dist_to_traj_km, 2),
        "min_distance_to_source_region_km": round(min_dist_to_src_km, 2),
        "distance_at_release_time_km": round(dist_at_release_time, 2),
        "temporal_offset_to_source_hours": round(min_time_offset_hours, 2),
        "time_spent_near_source_hours": time_near_src_hours,
        "is_inside_source_radius": bool(min_dist_to_src_km <= src_radius_km),
        "source_proximity_score": round(src_prox, 4),
        "closest_trajectory_time": closest_traj_time,

        # Phase 3 Model-Compatible Mappings (matching RANKING_FEATURE_NAMES)
        "min_distance_km": round(min_dist_to_traj_km, 2),
        "distance_at_spill_time_km": round(dist_at_release_time, 2),
        "temporal_offset_hours": round(min_time_offset_hours, 2),
        "trajectory_proximity_score": round(traj_prox, 4),
        "temporal_proximity_score": round(temp_prox, 4),
        "mean_speed_knots": round(mean_spd, 2),
        "speed_variance": round(var_spd, 2),
        "speed_anomaly_score": round(spd_anomaly, 4),
        "heading_deviation_deg": round(heading_dev, 1),
        "drift_corrected_distance_km": round(min_dist_to_src_km, 2),
        "ais_ping_count": float(len(df_v)),
    }


def correlate_and_rank_vessels(
    vessels_df: pd.DataFrame,
    backward_trajectory_df: pd.DataFrame,
    source_region_meta: dict[str, Any],
    model_path: Path | str | None = None,
    id_col: str = "mmsi",
    is_synthetic: bool = False,
    logger: logging.Logger | None = None,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """
    Main attribution entrypoint:
    1. Iterates across vessel tracks in vessels_df.
    2. Correlates each vessel with estimated backward trajectory and source region.
    3. Feeds features to the Phase 3 XGBoost ranking model.
    4. Produces ranked candidate vessel dossiers with mandatory investigatory disclaimers.
    """
    if logger is None:
        logger = setup_logging("drift.attribution")

    if vessels_df.empty:
        logger.warning("Empty AIS vessel dataset provided for attribution correlation.")
        return pd.DataFrame(), []

    # Detect synthetic mode from flag or DataFrame column
    is_syn = is_synthetic or (
        "data_mode" in vessels_df.columns
        and (vessels_df["data_mode"] == "synthetic").any()
    )

    vessel_id_column = id_col if id_col in vessels_df.columns else (
        "vessel_id" if "vessel_id" in vessels_df.columns else vessels_df.columns[0]
    )

    vessel_groups = vessels_df.groupby(vessel_id_column)
    logger.info("Correlating %d unique vessels with estimated drift trajectory...", len(vessel_groups))

    feature_rows = []
    candidates_list = []

    for v_id, group in vessel_groups:
        feats = correlate_vessel_with_drift(
            vessel_points=group,
            backward_trajectory_df=backward_trajectory_df,
            source_region_meta=source_region_meta,
        )

        v_name = (
            str(group["vessel_name"].dropna().iloc[0])
            if "vessel_name" in group.columns and not group["vessel_name"].dropna().empty
            else str(v_id)
        )

        row_dict = {"vessel_id": str(v_id), "vessel_name": v_name}
        row_dict.update(feats)
        feature_rows.append(row_dict)

        candidates_list.append({
            "vessel_id": str(v_id),
            "vessel_name": v_name,
            "features": feats,
        })

    df_features = pd.DataFrame(feature_rows)

    # Load Phase 3 Ranking Model
    try:
        model, meta = load_ranking_model(model_path=model_path, logger=logger)
        df_aligned = df_features[RANKING_FEATURE_NAMES]
        scores = predict_vessel_scores(model, df_aligned)
        logger.info("Scored candidate vessels using Phase 3 XGBoost attribution model.")
    except Exception as exc:
        logger.warning("Phase 3 model not available (%s). Using empirical heuristic scoring.", exc)
        # Fallback heuristic: 40% trajectory proximity + 30% temporal proximity + 30% speed anomaly
        scores = (
            0.40 * df_features["trajectory_proximity_score"].values
            + 0.30 * df_features["temporal_proximity_score"].values
            + 0.30 * df_features["speed_anomaly_score"].values
        )

    # Attach scores and sort
    for idx, c in enumerate(candidates_list):
        c["prioritization_score"] = round(float(scores[idx]), 4)
        c["min_distance_to_trajectory_km"] = c["features"]["min_distance_to_trajectory_km"]
        c["min_distance_to_source_region_km"] = c["features"]["min_distance_to_source_region_km"]
        c["temporal_offset_to_source_hours"] = c["features"]["temporal_offset_to_source_hours"]

    # Sort descending by prioritization score
    candidates_list.sort(key=lambda x: x["prioritization_score"], reverse=True)

    # Assign ranks and attach safety metadata and mandatory disclaimer
    ranked_candidates = []
    for rank_idx, cand in enumerate(candidates_list, 1):
        cand["rank"] = rank_idx
        cand["data_mode"] = "synthetic" if is_syn else "operational"
        cand["responsibility_confirmed"] = False
        cand["estimated_source_region"] = {
            "centroid": source_region_meta.get("centroid"),
            "estimated_release_timestamp": source_region_meta.get("estimated_release_timestamp"),
        }
        cand["disclaimer"] = LEGAL_INVESTIGATORY_DISCLAIMER
        ranked_candidates.append(cand)

    # Synchronize score and rank back to features DataFrame mapped by vessel_id
    score_map = {c["vessel_id"]: c["prioritization_score"] for c in candidates_list}
    rank_map = {c["vessel_id"]: c["rank"] for c in candidates_list}
    df_features["prioritization_score"] = df_features["vessel_id"].map(score_map)
    df_features["rank"] = df_features["vessel_id"].map(rank_map)
    df_features.sort_values(by="rank", inplace=True)
    df_features.reset_index(drop=True, inplace=True)

    logger.info("Attribution complete: %d vessels ranked.", len(ranked_candidates))
    return df_features, ranked_candidates
