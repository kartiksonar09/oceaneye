from datetime import datetime, timezone
import math

def calculate_ais_gap(last_ping: str, current_time: str = None) -> float:
    """Calculate the AIS gap in minutes between the last ping and now."""
    if not current_time:
        current_time = datetime.now(timezone.utc).isoformat()
        
    try:
        last_dt = datetime.fromisoformat(last_ping.replace("Z", "+00:00"))
        curr_dt = datetime.fromisoformat(current_time.replace("Z", "+00:00"))
        
        delta = (curr_dt - last_dt).total_seconds()
        return max(0.0, delta / 60.0)
    except Exception:
        return 0.0

def calculate_suspicion_score(ais_gap_minutes: float, distance_to_spill_km: float, is_tanker: bool) -> float:
    """
    Calculate a suspicion score between 0.0 and 1.0 based on:
    - AIS gap duration (> 30 mins is suspicious)
    - Distance to the origin of the spill (< 10 km is suspicious)
    - Vessel type (Tankers get a multiplier)
    """
    score = 0.0
    
    # Gap scoring (Max 0.4 points)
    if ais_gap_minutes > 120:
        score += 0.4
    elif ais_gap_minutes > 30:
        score += 0.4 * ((ais_gap_minutes - 30) / 90.0)
        
    # Distance scoring (Max 0.4 points)
    if distance_to_spill_km < 1.0:
        score += 0.4
    elif distance_to_spill_km < 10.0:
        score += 0.4 * (1.0 - (distance_to_spill_km - 1.0) / 9.0)
        
    # Vessel type scoring (Max 0.2 points)
    if is_tanker:
        score += 0.2
        
    return min(1.0, max(0.0, score))
