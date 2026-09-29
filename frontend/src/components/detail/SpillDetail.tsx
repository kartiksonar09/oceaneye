import React from 'react';
import { 
  Flame, 
  Satellite, 
  Target, 
  ShieldAlert, 
  Compass, 
  Clock, 
  ChevronRight,
  ExternalLink,
  Layers,
  FileSpreadsheet
} from 'lucide-react';
import { Spill, Suspect, Vessel } from '../../types/api';

interface SpillDetailProps {
  spill: Spill;
  suspects: Suspect[];
  vessels: Vessel[];
  onSelectVessel: (vessel: Vessel) => void;
  onExportReport: () => void;
}

export const SpillDetail: React.FC<SpillDetailProps> = ({
  spill,
  suspects,
  vessels,
  onSelectVessel,
  onExportReport,
}) => {
  // Find suspects linked to this spill
  const linkedSuspects = suspects.filter((s) => s.spill_id === spill.id);

  const getVesselByMmsi = (mmsi: string): Vessel | undefined => {
    return vessels.find((v) => v.mmsi === mmsi);
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Top Header Card */}
      <div className="bg-radar-850 border border-radar-700/80 p-3 rounded-xs">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-spill-amber animate-pulse" />
            <span className="text-[10px] text-radar-400 uppercase tracking-widest">SAR OIL SLICK ANOMALY</span>
          </div>
          <span className="px-2 py-0.5 rounded-xs bg-radar-900 border border-spill-amber/50 text-spill-amber font-bold uppercase text-[10px]">
            {spill.status}
          </span>
        </div>

        <h3 className="text-base font-bold text-radar-100 tracking-tight">{spill.id}</h3>
        <p className="text-[11px] text-radar-400 mt-0.5 flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-radar-500" />
          <span>ACQUIRED: {spill.detected_at}</span>
        </p>
      </div>

      {/* Numerical Evidence Matrix */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-radar-850 border border-radar-700/80 p-2.5 rounded-xs">
          <span className="text-[10px] text-radar-500 uppercase block">SLICK SURFACE AREA</span>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-bold text-radar-100">{spill.area_km2.toFixed(1)}</span>
            <span className="text-xs text-radar-400">km²</span>
          </div>
          <span className="text-[9px] text-radar-500 mt-1 block">95% Convex Hull Polygon</span>
        </div>

        <div className="bg-radar-850 border border-radar-700/80 p-2.5 rounded-xs">
          <span className="text-[10px] text-radar-500 uppercase block">SAR CONFIDENCE SCORE</span>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-bold text-spill-amber">{(spill.confidence * 100).toFixed(1)}</span>
            <span className="text-xs text-spill-amber/80">%</span>
          </div>
          <span className="text-[9px] text-radar-500 mt-1 block">XGBoost Look-Alike Screened</span>
        </div>
      </div>

      {/* Sensor & Spatial Parameters */}
      <div className="bg-radar-850 border border-radar-700/80 p-3 rounded-xs space-y-2">
        <div className="flex items-center gap-1.5 text-radar-300 text-[11px] font-bold border-b border-radar-750 pb-1.5">
          <Satellite className="w-3.5 h-3.5 text-radar-400" />
          <span>SENSOR & OBSERVATION METADATA</span>
        </div>

        <div className="grid grid-cols-2 gap-x-2 gap-y-1.5 text-[11px]">
          <div>
            <span className="text-[10px] text-radar-500 block">SATELLITE PLATFORM</span>
            <span className="text-radar-200">{spill.satellite_source}</span>
          </div>

          <div>
            <span className="text-[10px] text-radar-500 block">SENSOR MODE</span>
            <span className="text-radar-200">Interferometric Wide (IW)</span>
          </div>

          <div>
            <span className="text-[10px] text-radar-500 block">CENTROID LATITUDE</span>
            <span className="text-radar-200">{spill.centroid.lat.toFixed(5)}°</span>
          </div>

          <div>
            <span className="text-[10px] text-radar-500 block">CENTROID LONGITUDE</span>
            <span className="text-radar-200">{spill.centroid.lng.toFixed(5)}°</span>
          </div>

          <div className="col-span-2">
            <span className="text-[10px] text-radar-500 block">POLYGON VERTICES</span>
            <span className="text-radar-300 text-[10px]">{spill.polygon.length} boundary control nodes</span>
          </div>
        </div>
      </div>

      {/* Linked Suspect Vessels */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-radar-300 text-[11px] font-bold">
          <div className="flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-suspect-crimson" />
            <span>LINKED SUSPECT VESSELS ({linkedSuspects.length})</span>
          </div>
          <span className="text-[10px] text-radar-500 font-normal">ATTRIBUTION RANK</span>
        </div>

        {linkedSuspects.length === 0 ? (
          <div className="bg-radar-850 border border-radar-700/60 p-3 rounded-xs text-center text-radar-500 text-[11px]">
            NO CORRELATED AIS VESSELS WITHIN 48H DRIFT ENVELOPE
          </div>
        ) : (
          <div className="space-y-2">
            {linkedSuspects
              .sort((a, b) => b.suspicion_score - a.suspicion_score)
              .map((suspect, idx) => {
                const vessel = getVesselByMmsi(suspect.vessel_mmsi);
                const scorePercent = (suspect.suspicion_score * 100).toFixed(1);
                const isCritical = suspect.suspicion_score > 0.85;

                return (
                  <div
                    key={suspect.vessel_mmsi}
                    className="bg-radar-850 border border-radar-700/90 hover:border-radar-600 p-2.5 rounded-xs transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5">
                        <span className="w-4 h-4 rounded-xs bg-radar-800 border border-radar-700 text-radar-300 flex items-center justify-center text-[10px] font-bold">
                          #{idx + 1}
                        </span>
                        <span className="font-bold text-radar-100 text-xs">
                          {vessel ? vessel.name : `MMSI: ${suspect.vessel_mmsi}`}
                        </span>
                      </div>
                      <div className={`px-1.5 py-0.5 rounded-xs text-[10px] font-bold ${
                        isCritical 
                          ? 'bg-suspect-crimson/20 text-suspect-crimson border border-suspect-crimson/50' 
                          : 'bg-spill-amber/20 text-spill-amber border border-spill-amber/50'
                      }`}>
                        {scorePercent}%
                      </div>
                    </div>

                    <div className="text-[10px] text-radar-400 mb-1.5 flex items-center gap-2">
                      <span>MMSI: {suspect.vessel_mmsi}</span>
                      {vessel && <span>• {vessel.vessel_type}</span>}
                    </div>

                    {/* Top Reasoning Bullet */}
                    <div className="bg-radar-900/90 p-2 rounded-xs border border-radar-750 text-[11px] text-radar-300 mb-2">
                      <span className="text-[9px] text-radar-500 uppercase block mb-0.5 font-bold">KEY CORRELATION SIGNAL</span>
                      <p className="text-amber-200/90">{suspect.reasoning[0]}</p>
                    </div>

                    {vessel && (
                      <button
                        onClick={() => onSelectVessel(vessel)}
                        className="w-full flex items-center justify-center gap-1.5 py-1 px-2 bg-radar-800 hover:bg-radar-750 border border-radar-700 rounded-xs text-[11px] text-radar-200 transition-colors"
                      >
                        <span>DRILL INTO VESSEL EVIDENCE</span>
                        <ChevronRight className="w-3 h-3 text-radar-400" />
                      </button>
                    )}
                  </div>
                );
              })}
          </div>
        )}
      </div>

      {/* Export Dossier Button */}
      <button
        onClick={onExportReport}
        className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-radar-800 hover:bg-radar-750 border border-radar-600 rounded-xs text-xs text-radar-100 font-bold transition-colors shadow-md"
      >
        <FileSpreadsheet className="w-3.5 h-3.5 text-spill-amber" />
        <span>EXPORT INCIDENT EVIDENCE DOSSIER</span>
      </button>
    </div>
  );
};
