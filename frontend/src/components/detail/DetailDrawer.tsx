import React, { useState, useEffect } from 'react';
import { 
  X, 
  Flame, 
  Ship, 
  ShieldAlert, 
  Download, 
  Share2,
  Copy,
  Check,
  FileText
} from 'lucide-react';
import { Spill, Suspect, Vessel } from '../../types/api';
import { SpillDetail } from './SpillDetail';
import { VesselDetail } from './VesselDetail';
import { exportDossierPdf } from '../../utils/exportDossierPdf';
import { TrajectoryPoint } from '../../utils/vesselTrajectory';

interface DetailDrawerProps {
  selectedSpill: Spill | null;
  selectedVessel: Vessel | null;
  suspects: Suspect[];
  vessels: Vessel[];
  spills: Spill[];
  onSelectSpill: (spill: Spill) => void;
  onSelectVessel: (vessel: Vessel) => void;
  onClose: () => void;
  onScrubPoint?: (point: TrajectoryPoint | null) => void;
}

export const DetailDrawer: React.FC<DetailDrawerProps> = ({
  selectedSpill,
  selectedVessel,
  suspects,
  vessels,
  spills,
  onSelectSpill,
  onSelectVessel,
  onClose,
  onScrubPoint,
}) => {
  const [activeTab, setActiveTab] = useState<'spill' | 'vessel'>('spill');
  const [copied, setCopied] = useState<boolean>(false);

  // Synchronize active tab based on what was clicked most recently
  useEffect(() => {
    if (selectedVessel && !selectedSpill) {
      setActiveTab('vessel');
    } else if (selectedSpill && !selectedVessel) {
      setActiveTab('spill');
    }
  }, [selectedSpill, selectedVessel]);

  if (!selectedSpill && !selectedVessel) {
    return null;
  }

  const handleExportEvidence = () => {
    exportDossierPdf({
      spill: selectedSpill,
      vessel: selectedVessel,
      suspects,
      vessels,
    });
  };

  const handleCopyClipboard = () => {
    const text = selectedSpill 
      ? `OCEAN EYE INCIDENT REPORT:\nSpill ID: ${selectedSpill.id}\nArea: ${selectedSpill.area_km2} km²\nConfidence: ${(selectedSpill.confidence * 100).toFixed(1)}%\nCoordinates: ${selectedSpill.centroid.lat}, ${selectedSpill.centroid.lng}\nSatellite: ${selectedSpill.satellite_source}`
      : selectedVessel
      ? `OCEAN EYE VESSEL TELEMETRY:\nName: ${selectedVessel.name}\nMMSI: ${selectedVessel.mmsi}\nType: ${selectedVessel.vessel_type}\nSpeed: ${selectedVessel.speed_knots} kt @ ${selectedVessel.heading}°\nAIS Gap: ${selectedVessel.ais_gap_minutes ?? 0}m`
      : '';

    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <aside 
      aria-label="Target Details Drawer"
      className="w-96 bg-radar-900 border-l border-radar-700/80 flex flex-col h-full z-20 select-none shadow-2xl"
    >
      {/* Drawer Header Tabs */}
      <div className="bg-radar-850 border-b border-radar-700/80 px-3 pt-2 pb-0 flex items-center justify-between">
        <div className="flex items-center gap-1 font-mono text-xs">
          {selectedSpill && (
            <button
              type="button"
              onClick={() => setActiveTab('spill')}
              aria-label="View Spill Details"
              className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-bold transition-colors cursor-pointer ${
                activeTab === 'spill'
                  ? 'border-spill-amber text-spill-amber bg-radar-900'
                  : 'border-transparent text-radar-400 hover:text-radar-200'
              }`}
            >
              <Flame className="w-3.5 h-3.5" />
              <span>SPILL DETAIL</span>
            </button>
          )}

          {selectedVessel && (
            <button
              type="button"
              onClick={() => setActiveTab('vessel')}
              aria-label="View Vessel Details"
              className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-bold transition-colors cursor-pointer ${
                activeTab === 'vessel'
                  ? 'border-vessel-teal text-vessel-teal bg-radar-900'
                  : 'border-transparent text-radar-400 hover:text-radar-200'
              }`}
            >
              <Ship className="w-3.5 h-3.5" />
              <span>VESSEL DETAIL</span>
            </button>
          )}
        </div>

        {/* Action icons & Close */}
        <div className="flex items-center gap-1 pb-1">
          <button
            type="button"
            onClick={handleCopyClipboard}
            title="Copy operational summary"
            aria-label="Copy operational summary to clipboard"
            className="p-1 rounded-xs bg-radar-800 border border-radar-700 hover:bg-radar-750 text-radar-400 hover:text-radar-200 cursor-pointer"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <button
            type="button"
            onClick={handleExportEvidence}
            title="Download Official PDF Dossier (jsPDF)"
            aria-label="Download Official Intelligence Dossier PDF"
            className="p-1 rounded-xs bg-radar-800 border border-radar-700 hover:bg-radar-750 text-radar-400 hover:text-radar-200 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 text-spill-amber" />
          </button>
          <button
            type="button"
            onClick={onClose}
            title="Close Drawer"
            aria-label="Close detail drawer"
            className="p-1 rounded-xs bg-radar-800 border border-radar-700 hover:bg-radar-750 text-radar-400 hover:text-radar-200 ml-1 cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Drawer Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {activeTab === 'spill' && selectedSpill && (
          <SpillDetail
            spill={selectedSpill}
            suspects={suspects}
            vessels={vessels}
            onSelectVessel={onSelectVessel}
            onExportReport={handleExportEvidence}
          />
        )}

        {activeTab === 'vessel' && selectedVessel && (
          <VesselDetail
            vessel={selectedVessel}
            suspects={suspects}
            spills={spills}
            onSelectSpill={onSelectSpill}
            onExportReport={handleExportEvidence}
            onScrubPoint={onScrubPoint}
          />
        )}
      </div>
    </aside>
  );
};

