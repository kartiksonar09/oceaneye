export interface Centroid {
  lat: number;
  lng: number;
}

export type SpillStatus = 'active' | 'monitoring' | 'resolved';

export interface Spill {
  id: string;
  detected_at: string; // ISO 8601
  satellite_source: string; // e.g. "Sentinel-1"
  confidence: number; // 0–1
  polygon: [number, number][]; // [[lat, lng], ...]
  centroid: Centroid;
  area_km2: number;
  status: SpillStatus;
}

export interface Vessel {
  mmsi: string;
  name: string;
  lat: number;
  lng: number;
  speed_knots: number;
  heading: number; // 0–360
  last_ais_update: string; // ISO 8601
  ais_gap_minutes: number | null; // null if continuous signal
  vessel_type: string;
  
  // Extended Maritime Intelligence Attributes
  imo?: string;
  call_sign?: string;
  flag?: string;
  flag_code?: string;
  length_m?: number;
  beam_m?: number;
  draught_m?: number;
  dwt_tonnes?: number;
  gross_tonnage?: number;
  year_built?: number;
  destination?: string;
  eta?: string;
  nav_status?: string;
  photo_url?: string;
}

export interface Suspect {
  vessel_mmsi: string;
  spill_id: string;
  suspicion_score: number; // 0–1
  reasoning: string[];
  flagged_at: string; // ISO 8601
}

export interface OperationalAlert {
  id: string;
  timestamp: string; // ISO 8601
  category: 'SAR_DETECT' | 'AIS_GAP' | 'SUSPECT_FLAG' | 'DRIFT_ALERT' | 'SYSTEM';
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  summary: string;
  detail?: string;
  targetId?: string; // Spill ID or Vessel MMSI
  targetType?: 'spill' | 'vessel';
}

export interface RegionZone {
  id: string;
  name: string;
  center: [number, number]; // [lat, lng]
  zoom: number;
  description: string;
}

export type BasemapType = 'dark' | 'satellite' | 'street';

export interface AisHistoryPoint {
  timestamp: string; // ISO 8601
  lat: number;
  lng: number;
  speed_knots: number;
  heading: number;
}

export type WebSocketMessageType = 
  | { type: 'vessel_update'; data: Vessel }
  | { type: 'spill_update'; data: Spill }
  | { type: 'suspect_flagged'; data: Suspect }
  | { type: 'spill_resolved'; data: { id: string } };

export type FeedStatus = 'connected' | 'reconnecting' | 'degraded' | 'mock';

