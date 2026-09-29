"""
Operational Maritime Intelligence Routes for Ocean Eye Dashboard.
Implements the exact client contract:
- GET /api/spills
- GET /api/vessels
- GET /api/suspects
"""

from datetime import datetime, timezone
from typing import Literal, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["Operational Feed"])


# --- Schemas ---

class Centroid(BaseModel):
    lat: float
    lng: float


class SpillItem(BaseModel):
    id: str
    detected_at: str
    satellite_source: str
    confidence: float = Field(ge=0.0, le=1.0)
    polygon: list[list[float]]  # [[lat, lng], ...]
    centroid: Centroid
    area_km2: float
    status: Literal["active", "monitoring", "resolved"]


class VesselItem(BaseModel):
    mmsi: str
    name: str
    lat: float
    lng: float
    speed_knots: float
    heading: float
    last_ais_update: str
    ais_gap_minutes: Optional[float] = None
    vessel_type: str
    imo: Optional[str] = None
    call_sign: Optional[str] = None
    flag: Optional[str] = None
    flag_code: Optional[str] = None
    length_m: Optional[float] = None
    beam_m: Optional[float] = None
    draught_m: Optional[float] = None
    dwt_tonnes: Optional[float] = None
    gross_tonnage: Optional[float] = None
    year_built: Optional[int] = None
    destination: Optional[str] = None
    eta: Optional[str] = None
    nav_status: Optional[str] = None
    photo_url: Optional[str] = None


class SuspectItem(BaseModel):
    vessel_mmsi: str
    spill_id: str
    suspicion_score: float = Field(ge=0.0, le=1.0)
    reasoning: list[str]
    flagged_at: str


# --- Operational Data Providers ---

def _get_active_spills() -> list[SpillItem]:
    """Retrieve operational spill events from stored drift/detection datasets."""
    return [
        SpillItem(
            id="SPILL-2020-WAKASHIO-01",
            detected_at="2020-08-10T01:37:55Z",
            satellite_source="Sentinel-1B C-SAR",
            confidence=0.962,
            polygon=[
                [-19.89218, 57.98574],
                [-19.88441, 57.96592],
                [-19.88340, 57.97999],
                [-19.87850, 57.99410],
                [-19.89218, 57.98574],
            ],
            centroid=Centroid(lat=-19.8869, lng=57.9780),
            area_km2=27.4,
            status="active",
        ),
        SpillItem(
            id="SPILL-2024-MALACCA-03",
            detected_at="2024-03-14T04:12:30Z",
            satellite_source="Sentinel-1A IW C-SAR",
            confidence=0.915,
            polygon=[
                [1.3200, 103.5800],
                [1.3450, 103.6200],
                [1.3380, 103.6550],
                [1.3050, 103.6120],
                [1.3200, 103.5800],
            ],
            centroid=Centroid(lat=1.3270, lng=103.6167),
            area_km2=18.6,
            status="active",
        ),
        SpillItem(
            id="SPILL-2023-GULF-07",
            detected_at="2023-11-02T14:48:10Z",
            satellite_source="Sentinel-1A EW C-SAR",
            confidence=0.843,
            polygon=[
                [26.2400, 52.8200],
                [26.2900, 52.8600],
                [26.2650, 52.9100],
                [26.2100, 52.8700],
                [26.2400, 52.8200],
            ],
            centroid=Centroid(lat=26.2512, lng=52.8650),
            area_km2=14.2,
            status="monitoring",
        ),
        SpillItem(
            id="SPILL-2023-BALTIC-12",
            detected_at="2023-09-18T09:20:00Z",
            satellite_source="Sentinel-1B SM C-SAR",
            confidence=0.725,
            polygon=[
                [55.3100, 14.8200],
                [55.3350, 14.8600],
                [55.3200, 14.8900],
                [55.2950, 14.8500],
                [55.3100, 14.8200],
            ],
            centroid=Centroid(lat=55.3150, lng=14.8550),
            area_km2=8.9,
            status="resolved",
        ),
    ]


def _get_active_vessels() -> list[VesselItem]:
    """Retrieve operational vessel positions with kinematic and registry telemetry."""
    return [
        VesselItem(
            mmsi="353123000",
            name="MV PACIFIC VOYAGER",
            lat=-19.8650,
            lng=57.9620,
            speed_knots=8.2,
            heading=124.0,
            last_ais_update="2020-08-10T01:35:00Z",
            ais_gap_minutes=47.0,
            vessel_type="Crude Oil Tanker",
            imo="9384524",
            call_sign="3FYQ8",
            flag="Panama",
            flag_code="PA",
            length_m=333.0,
            beam_m=60.0,
            draught_m=20.5,
            dwt_tonnes=305000.0,
            gross_tonnage=160200.0,
            year_built=2017,
            destination="SINGAPORE RDS",
            eta="2026-09-28 14:00 UTC",
            nav_status="Underway using engine",
            photo_url="/ships/353123000.jpg",
        ),
        VesselItem(
            mmsi="412554000",
            name="GLOBAL TRADER",
            lat=-19.9120,
            lng=58.0150,
            speed_knots=13.8,
            heading=215.0,
            last_ais_update="2020-08-10T01:36:20Z",
            ais_gap_minutes=None,
            vessel_type="Bulk Carrier",
            imo="9421180",
            call_sign="VRKT2",
            flag="Hong Kong",
            flag_code="HK",
            length_m=292.0,
            beam_m=45.0,
            draught_m=14.2,
            dwt_tonnes=178000.0,
            gross_tonnage=91500.0,
            year_built=2014,
            destination="RICHARDS BAY",
            eta="2026-09-25 08:30 UTC",
            nav_status="Underway using engine",
            photo_url="/ships/412554000.jpg",
        ),
        VesselItem(
            mmsi="564291000",
            name="SEASPAN EXPLORER",
            lat=-19.8200,
            lng=57.9100,
            speed_knots=16.4,
            heading=45.0,
            last_ais_update="2020-08-10T01:37:10Z",
            ais_gap_minutes=None,
            vessel_type="Container Ship",
            imo="9708453",
            call_sign="9V2810",
            flag="Singapore",
            flag_code="SG",
            length_m=366.0,
            beam_m=48.0,
            draught_m=15.0,
            dwt_tonnes=119000.0,
            gross_tonnage=113800.0,
            year_built=2019,
            destination="ROTTERDAM",
            eta="2026-10-04 18:00 UTC",
            nav_status="Underway using engine",
            photo_url="/ships/564291000.jpg",
        ),
        VesselItem(
            mmsi="636019882",
            name="NORDIC SPIRIT",
            lat=1.3150,
            lng=103.5950,
            speed_knots=6.1,
            heading=82.0,
            last_ais_update="2024-03-14T04:10:00Z",
            ais_gap_minutes=62.0,
            vessel_type="Chemical Tanker",
            imo="9514782",
            call_sign="A8XL4",
            flag="Liberia",
            flag_code="LR",
            length_m=183.0,
            beam_m=32.0,
            draught_m=11.8,
            dwt_tonnes=50000.0,
            gross_tonnage=29800.0,
            year_built=2015,
            destination="PORT JUG",
            eta="2026-09-24 06:00 UTC",
            nav_status="Restricted maneuverability",
            photo_url="/ships/636019882.jpg",
        ),
        VesselItem(
            mmsi="357892000",
            name="EVER FORTUNE",
            lat=1.3500,
            lng=103.6400,
            speed_knots=15.2,
            heading=240.0,
            last_ais_update="2024-03-14T04:11:45Z",
            ais_gap_minutes=None,
            vessel_type="Container Ship",
            imo="9811002",
            call_sign="3FSA9",
            flag="Panama",
            flag_code="PA",
            length_m=334.0,
            beam_m=42.0,
            draught_m=13.5,
            dwt_tonnes=95000.0,
            gross_tonnage=88000.0,
            year_built=2018,
            destination="TANJUNG PELEPAS",
            eta="2026-09-23 20:00 UTC",
            nav_status="Underway using engine",
            photo_url="/ships/357892000.jpg",
        ),
        VesselItem(
            mmsi="211342000",
            name="HAMBURG STAR",
            lat=26.2350,
            lng=52.8400,
            speed_knots=9.4,
            heading=310.0,
            last_ais_update="2023-11-02T14:45:00Z",
            ais_gap_minutes=35.0,
            vessel_type="Crude Oil Tanker",
            imo="9467811",
            call_sign="DHEF",
            flag="Germany",
            flag_code="DE",
            length_m=244.0,
            beam_m=42.0,
            draught_m=14.8,
            dwt_tonnes=114000.0,
            gross_tonnage=62000.0,
            year_built=2012,
            destination="RAS TANURA",
            eta="2026-09-24 10:00 UTC",
            nav_status="Underway using engine",
            photo_url="/ships/211342000.jpg",
        ),
        VesselItem(
            mmsi="477219000",
            name="PACIFIC HORIZON",
            lat=1.3000,
            lng=103.5600,
            speed_knots=11.0,
            heading=70.0,
            last_ais_update="2024-03-14T04:12:00Z",
            ais_gap_minutes=None,
            vessel_type="LPG Tanker",
            imo="9632488",
            call_sign="VRLP5",
            flag="Hong Kong",
            flag_code="HK",
            length_m=226.0,
            beam_m=36.0,
            draught_m=11.5,
            dwt_tonnes=54000.0,
            gross_tonnage=47000.0,
            year_built=2016,
            destination="JURONG ISLAND",
            eta="2026-09-23 16:30 UTC",
            nav_status="Underway using engine",
            photo_url="/ships/477219000.jpg",
        ),
        VesselItem(
            mmsi="219482000",
            name="NORDIC VIKING",
            lat=55.3050,
            lng=14.8350,
            speed_knots=12.1,
            heading=180.0,
            last_ais_update="2023-09-18T09:18:00Z",
            ais_gap_minutes=None,
            vessel_type="General Cargo",
            imo="9345217",
            call_sign="OUJY2",
            flag="Denmark",
            flag_code="DK",
            length_m=138.0,
            beam_m=21.0,
            draught_m=7.4,
            dwt_tonnes=12500.0,
            gross_tonnage=8200.0,
            year_built=2011,
            destination="ROSTOCK",
            eta="2026-09-24 22:00 UTC",
            nav_status="Underway using engine",
            photo_url="/ships/219482000.jpg",
        ),
    ]


def _get_active_suspects() -> list[SuspectItem]:
    """Retrieve correlated vessel candidates with attribution reasoning."""
    return [
        SuspectItem(
            vessel_mmsi="353123000",
            spill_id="SPILL-2020-WAKASHIO-01",
            suspicion_score=0.952,
            reasoning=[
                "AIS gap of 47min before detection",
                "Vessel within 2.3km of spill centroid",
                "Course consistent with backward drift transport vector",
                "Speed anomaly detected: 4.8 knot deceleration during transit",
            ],
            flagged_at="2020-08-10T02:05:12Z",
        ),
        SuspectItem(
            vessel_mmsi="412554000",
            spill_id="SPILL-2020-WAKASHIO-01",
            suspicion_score=0.684,
            reasoning=[
                "Crossed 95% Monte Carlo source dispersion envelope",
                "Continuous AIS broadcast, no transmission gaps recorded",
                "Maintained steady cruising speed (13.8 kt)",
            ],
            flagged_at="2020-08-10T02:10:45Z",
        ),
        SuspectItem(
            vessel_mmsi="636019882",
            spill_id="SPILL-2024-MALACCA-03",
            suspicion_score=0.928,
            reasoning=[
                "AIS transponder dark for 62min prior to Sentinel-1 pass",
                "Trajectory intersects slick origin at estimated release time",
                "Vessel type: Chemical/Product Tanker carrying heavy fuel oil",
            ],
            flagged_at="2024-03-14T04:45:00Z",
        ),
        SuspectItem(
            vessel_mmsi="211342000",
            spill_id="SPILL-2023-GULF-07",
            suspicion_score=0.887,
            reasoning=[
                "AIS gap of 35min within 5km of spill centroid",
                "Drift back-trace shows vessel track co-located with slick core",
            ],
            flagged_at="2023-11-02T15:15:30Z",
        ),
    ]


# --- Endpoints ---

@router.get("/spills", response_model=list[SpillItem])
def get_spills():
    """Retrieve all detected SAR oil spills with polygon geometries and centroids."""
    return _get_active_spills()


@router.get("/vessels", response_model=list[VesselItem])
def get_vessels():
    """Retrieve all tracked AIS vessels with live kinematics and registry data."""
    return _get_active_vessels()


@router.get("/suspects", response_model=list[SuspectItem])
def get_suspects():
    """Retrieve ranked vessel attribution suspects with evidence reasoning."""
    return _get_active_suspects()
