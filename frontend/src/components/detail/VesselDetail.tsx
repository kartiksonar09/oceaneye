import React from 'react';
import { 
  Radio, 
  AlertTriangle, 
  ShieldAlert, 
  Compass, 
  Gauge, 
  Clock, 
  Flame, 
  ChevronRight,
  CheckCircle2,
  FileSpreadsheet,
  Anchor,
  Flag,
  Navigation,
  Ruler,
  Calendar
} from 'lucide-react';
import { Spill, Suspect, Vessel } from '../../types/api';
import { VesselPhotoPanel } from '../common/VesselPhotoPanel';
import { TimelineScrubber } from './TimelineScrubber';
import { TrajectoryPoint } from '../../utils/vesselTrajectory';

interface VesselDetailProps {
  vessel: Vessel;
  suspects: Suspect[];
  spills: Spill[];
  onSelectSpill: (spill: Spill) => void;
  onExportReport: () => void;
  onScrubPoint?: (point: TrajectoryPoint | null) => void;
}

export const VesselDetail: React.FC<VesselDetailProps> = ({
  vessel,
  suspects,
  spills,
  onSelectSpill,
  onExportReport,
  onScrubPoint,
}) => {
  // Check if vessel is flagged as suspect
  const suspectRecord = suspects.find((s) => s.vessel_mmsi === vessel.mmsi);
  const linkedSpill = suspectRecord 
    ? spills.find((s) => s.id === suspectRecord.spill_id) 
    : undefined;

  const isFlagged = Boolean(suspectRecord);
  const hasAisGap = vessel.ais_gap_minutes !== null && vessel.ais_gap_minutes > 0;

  return (
    <div className="space-y-3 font-mono text-xs">
      {/* Vessel Photograph Showcase */}
      <VesselPhotoPanel
        mmsi={vessel.mmsi}
        imo={vessel.imo}
        vesselName={vessel.name}
        vesselType={vessel.vessel_type}
        isFlagged={isFlagged}
      />

      {/* Primary Registry Identification */}
      <div className={`p-3 rounded-xs border ${
        isFlagged 
          ? 'bg-suspect-crimson/10 border-suspect-crimson/60' 
          : 'bg-radar-850 border-radar-700/80'
      }`}>
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-base font-bold text-radar-100 tracking-tight">{vessel.name}</h3>
          {vessel.flag && (
            <span className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-xs bg-radar-900 border border-radar-700 text-radar-200">
              <Flag className="w-3 h-3 text-radar-400" />
              <span>{vessel.flag}</span>
            </span>
          )}
        </div>

        <div className="grid grid-cols-3 gap-2 mt-2 pt-2 border-t border-radar-750 text-[11px]">
          <div>
            <span className="text-[9px] text-radar-500 block uppercase">MMSI NUMBER</span>
            <span className="text-radar-100 font-bold">{vessel.mmsi}</span>
          </div>

          <div>
            <span className="text-[9px] text-radar-500 block uppercase">IMO NUMBER</span>
            <span className="text-radar-200">{vessel.imo || 'UNKNOWN'}</span>
          </div>

          <div>
            <span className="text-[9px] text-radar-500 block uppercase">CALL SIGN</span>
            <span className="text-radar-200">{vessel.call_sign || 'UNKNOWN'}</span>
          </div>
        </div>
      </div>

      {/* AIS Transponder Integrity Warning (CRITICAL SIGNAL) */}
      {hasAisGap ? (
        <div className="bg-amber-950/40 border border-amber-600/70 p-3 rounded-xs space-y-1.5 shadow-sm">
          <div className="flex items-center gap-2 text-spill-amber font-bold text-xs">
            <AlertTriangle className="w-4 h-4 text-spill-amber animate-bounce" />
            <span>AIS SIGNAL LOSS ANOMALY DETECTED</span>
          </div>
          <p className="text-[11px] text-amber-200/90 leading-relaxed">
            Transponder was dark for <strong className="text-white underline">{vessel.ais_gap_minutes} minutes</strong> directly preceding SAR spill detection window. Indicates potential deliberate transponder shutdown.
          </p>
          <div className="text-[10px] text-amber-400/80 pt-1 border-t border-amber-800/60 flex items-center justify-between">
            <span>SIGNAL STATUS: DISCONTINUOUS</span>
            <span>GAP DURATION: {vessel.ais_gap_minutes} MIN</span>
          </div>
        </div>
      ) : (
        <div className="bg-radar-850 border border-radar-700/80 p-2 rounded-xs flex items-center justify-between text-radar-300">
          <div className="flex items-center gap-2 text-[11px]">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Continuous AIS broadcast verified (no transmission gaps)</span>
          </div>
          <span className="text-[10px] text-emerald-400 font-bold">100% SIGNAL</span>
        </div>
      )}

      {/* AIS Historical Trajectory Timeline Scrubber */}
      <TimelineScrubber vessel={vessel} onScrubPoint={onScrubPoint} />

      {/* Vessel Dimensions & Structural Specifications */}
      <div className="bg-radar-850 border border-radar-700/80 p-3 rounded-xs space-y-2">
        <div className="flex items-center gap-1.5 text-radar-300 text-[11px] font-bold border-b border-radar-750 pb-1.5">
          <Anchor className="w-3.5 h-3.5 text-radar-400" />
          <span>VESSEL PARTICULARS & TONNAGE</span>
        </div>

        <div className="grid grid-cols-3 gap-2 text-[11px]">
          <div>
            <span className="text-[9px] text-radar-500 block uppercase">LENGTH (LOA)</span>
            <span className="text-radar-200 font-semibold">{vessel.length_m ? `${vessel.length_m} m` : 'UNKNOWN'}</span>
          </div>

          <div>
            <span className="text-[9px] text-radar-500 block uppercase">BEAM (WIDTH)</span>
            <span className="text-radar-200 font-semibold">{vessel.beam_m ? `${vessel.beam_m} m` : 'UNKNOWN'}</span>
          </div>

          <div>
            <span className="text-[9px] text-radar-500 block uppercase">DRAUGHT</span>
            <span className="text-radar-200 font-semibold">{vessel.draught_m ? `${vessel.draught_m} m` : 'UNKNOWN'}</span>
          </div>

          <div>
            <span className="text-[9px] text-radar-500 block uppercase">DEADWEIGHT</span>
            <span className="text-radar-200 font-semibold">{vessel.dwt_tonnes ? `${vessel.dwt_tonnes.toLocaleString()} DWT` : 'UNKNOWN'}</span>
          </div>

          <div>
            <span className="text-[9px] text-radar-500 block uppercase">GROSS TONNAGE</span>
            <span className="text-radar-200 font-semibold">{vessel.gross_tonnage ? `${vessel.gross_tonnage.toLocaleString()} GT` : 'UNKNOWN'}</span>
          </div>

          <div>
            <span className="text-[9px] text-radar-500 block uppercase">YEAR BUILT</span>
            <span className="text-radar-200 font-semibold">{vessel.year_built || 'UNKNOWN'}</span>
          </div>
        </div>

        {/* Voyage & Destination */}
        <div className="pt-2 border-t border-radar-750 grid grid-cols-2 gap-2 text-[11px]">
          <div>
            <span className="text-[9px] text-radar-500 block uppercase">DESTINATION PORT</span>
            <span className="text-spill-amber font-semibold">{vessel.destination || 'UNKNOWN'}</span>
          </div>
          <div>
            <span className="text-[9px] text-radar-500 block uppercase">ESTIMATED ARRIVAL</span>
            <span className="text-radar-200">{vessel.eta || 'UNKNOWN'}</span>
          </div>
        </div>
      </div>

      {/* Kinematics Telemetry Grid */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-radar-850 border border-radar-700/80 p-2.5 rounded-xs">
          <span className="text-[10px] text-radar-500 uppercase block">SPEED OVER GROUND</span>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-bold text-radar-100">{vessel.speed_knots.toFixed(1)}</span>
            <span className="text-xs text-radar-400">knots</span>
          </div>
        </div>

        <div className="bg-radar-850 border border-radar-700/80 p-2.5 rounded-xs">
          <span className="text-[10px] text-radar-500 uppercase block">COURSE / HEADING</span>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-bold text-radar-100">{vessel.heading.toFixed(0)}</span>
            <span className="text-xs text-radar-400">° TRUE</span>
          </div>
        </div>

        <div className="bg-radar-850 border border-radar-700/80 p-2.5 rounded-xs">
          <span className="text-[10px] text-radar-500 uppercase block">CURRENT LATITUDE</span>
          <span className="text-xs font-bold text-radar-200 mt-1 block">{vessel.lat.toFixed(5)}°</span>
        </div>

        <div className="bg-radar-850 border border-radar-700/80 p-2.5 rounded-xs">
          <span className="text-[10px] text-radar-500 uppercase block">CURRENT LONGITUDE</span>
          <span className="text-xs font-bold text-radar-200 mt-1 block">{vessel.lng.toFixed(5)}°</span>
        </div>
      </div>

      {/* Suspect Attribution Analysis (if suspect) */}
      {isFlagged && suspectRecord && (
        <div className="bg-radar-850 border border-suspect-crimson/50 p-3 rounded-xs space-y-3">
          <div className="flex items-center justify-between border-b border-radar-750 pb-2">
            <div className="flex items-center gap-1.5 text-suspect-crimson font-bold">
              <ShieldAlert className="w-4 h-4" />
              <span>ATTRIBUTION CORRELATION MODEL</span>
            </div>
            <div className="text-right">
              <span className="text-[10px] text-radar-500 block uppercase">PRIORITIZATION SCORE</span>
              <span className="text-base font-bold text-suspect-crimson">
                {(suspectRecord.suspicion_score * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Linked Spill Link */}
          {linkedSpill && (
            <div className="bg-radar-900 border border-radar-700 p-2 rounded-xs flex items-center justify-between">
              <div>
                <span className="text-[9px] text-radar-500 uppercase block font-bold">LINKED SAR SPILL</span>
                <span className="text-xs font-bold text-spill-amber">{linkedSpill.id}</span>
                <span className="text-[10px] text-radar-400 block mt-0.5">Area: {linkedSpill.area_km2} km²</span>
              </div>
              <button
                onClick={() => onSelectSpill(linkedSpill)}
                className="flex items-center gap-1 px-2 py-1 bg-radar-800 hover:bg-radar-750 border border-radar-700 rounded-xs text-[10px] text-radar-200"
              >
                <span>FOCUS SPILL</span>
                <ChevronRight className="w-3 h-3 text-spill-amber" />
              </button>
            </div>
          )}

          {/* Algorithmic Evidence Bullets */}
          <div>
            <span className="text-[10px] text-radar-400 uppercase tracking-wider block mb-1.5 font-bold">
              INVESTIGATIVE REASONING CRITERIA:
            </span>
            <ul className="space-y-1.5">
              {suspectRecord.reasoning.map((reason, idx) => (
                <li 
                  key={idx} 
                  className="bg-radar-900/80 p-2 rounded-xs border-l-2 border-suspect-crimson text-[11px] text-radar-200"
                >
                  {reason}
                </li>
              ))}
            </ul>
          </div>

          <div className="text-[9px] text-radar-500 italic border-t border-radar-800 pt-2 leading-normal">
            * NOTICE: Attribution scores represent statistical spatio-temporal correlation with estimated spill origin. A high score is an investigative prioritization metric, not legal proof of fault.
          </div>
        </div>
      )}

      {/* Export Report Action */}
      <button
        type="button"
        onClick={onExportReport}
        aria-label="Export official intelligence dossier PDF"
        className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-radar-800 hover:bg-radar-750 border border-radar-600 rounded-xs text-xs text-radar-100 font-bold transition-colors shadow-md cursor-pointer"
      >
        <FileSpreadsheet className="w-3.5 h-3.5 text-spill-amber" />
        <span>EXPORT OFFICIAL DOSSIER (PDF)</span>
      </button>
    </div>
  );
};
