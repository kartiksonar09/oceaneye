import React, { useState } from 'react';
import { 
  Ship, 
  X, 
  Search, 
  AlertTriangle, 
  Radio, 
  ChevronRight,
  Filter,
  Flag,
  Anchor,
  Loader2
} from 'lucide-react';
import { Suspect, Vessel } from '../../types/api';
import { useDebounce } from '../../utils/core';
import { VesselSilhouette } from '../common/VesselSilhouettes';

interface VesselDirectoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  vessels: Vessel[];
  suspects: Suspect[];
  onSelectVessel: (vessel: Vessel) => void;
  isLoading?: boolean;
}

const VesselCardThumbnail: React.FC<{
  vessel: Vessel;
  isSuspect: boolean;
}> = ({ vessel, isSuspect }) => {
  const [imgError, setImgError] = useState<boolean>(false);
  const photo = vessel.photo_url || `/ships/${vessel.mmsi}.jpg`;

  return (
    <div className="w-28 h-20 rounded-xs overflow-hidden shrink-0 border border-radar-700 bg-radar-950 relative flex items-center justify-center">
      {!imgError ? (
        <img 
          src={photo} 
          alt={vessel.name} 
          onError={() => setImgError(true)}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center bg-radar-900/90 p-1 text-center select-none">
          <VesselSilhouette vesselType={vessel.vessel_type} className="w-16 h-8 opacity-70" />
          <span className="text-[7.5px] font-mono text-radar-500 uppercase tracking-tight mt-0.5">
            NO PHOTO
          </span>
        </div>
      )}
      {isSuspect && (
        <span className="absolute top-1 left-1 px-1 py-0.2 rounded-xs bg-suspect-crimson text-white text-[8px] font-bold">
          SUSPECT
        </span>
      )}
    </div>
  );
};


export const VesselDirectoryModal: React.FC<VesselDirectoryModalProps> = React.memo(({
  isOpen,
  onClose,
  vessels,
  suspects,
  onSelectVessel,
  isLoading = false,
}) => {
  const [search, setSearch] = useState<string>('');
  const debouncedSearch = useDebounce(search, 300);
  const [filterType, setFilterType] = useState<string>('ALL');

  if (!isOpen) return null;

  const suspectMmsiSet = new Set(suspects.map((s) => s.vessel_mmsi));

  const filteredVessels = vessels.filter((v) => {
    const matchesSearch = 
      v.name.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
      v.mmsi.includes(debouncedSearch) ||
      (v.imo && v.imo.includes(debouncedSearch)) ||
      (v.flag && v.flag.toLowerCase().includes(debouncedSearch.toLowerCase()));

    if (!matchesSearch) return false;

    if (filterType === 'SUSPECT') return suspectMmsiSet.has(v.mmsi);
    if (filterType === 'GAP') return v.ais_gap_minutes !== null && v.ais_gap_minutes > 0;
    if (filterType === 'TANKER') return v.vessel_type.toLowerCase().includes('tanker');
    return true;
  });

  return (
    <div 
      onClick={onClose}
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-4 select-none"
    >
      <div 
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-4xl max-h-[85vh] bg-radar-900 border border-radar-700 rounded-xs shadow-2xl flex flex-col font-mono"
      >
        {/* Modal Header */}
        <div className="p-3 bg-radar-850 border-b border-radar-700/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-xs bg-vessel-teal/20 border border-vessel-teal/50 text-vessel-teal">
              <Ship className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-radar-100 tracking-tight">
                ACTIVE AIS VESSEL FLEET DIRECTORY
              </h3>
              <p className="text-[10px] text-radar-400">
                REAL-TIME TELEMETRY, SHIP PHOTOMETRY & SENSOR ATTRIBUTION RECORDS ({vessels.length} TARGETS)
              </p>
            </div>
          </div>

          <button 
            onClick={onClose}
            className="p-1 rounded-xs bg-radar-800 border border-radar-700 hover:bg-radar-750 text-radar-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="p-3 bg-radar-900 border-b border-radar-750 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-3.5 h-3.5 text-radar-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="SEARCH BY SHIP NAME, MMSI, IMO, OR FLAG..."
              className="w-full bg-radar-850 border border-radar-700 rounded-xs pl-8 pr-3 py-1.5 text-xs text-radar-200 placeholder-radar-500 focus:outline-none focus:border-vessel-teal"
            />
          </div>

          <div className="flex items-center gap-1 text-[11px]">
            {(['ALL', 'SUSPECT', 'GAP', 'TANKER'] as const).map((ft) => (
              <button
                key={ft}
                onClick={() => setFilterType(ft)}
                className={`px-2 py-1 rounded-xs border uppercase ${
                  filterType === ft
                    ? 'bg-radar-750 border-radar-500 text-radar-100 font-bold'
                    : 'bg-radar-850 border-radar-750 text-radar-400 hover:text-radar-200'
                }`}
              >
                {ft === 'GAP' ? 'AIS DARK' : ft}
              </button>
            ))}
          </div>
        </div>

        {/* Vessel Cards Grid */}
        <div className="flex-1 overflow-y-auto p-3 grid grid-cols-1 md:grid-cols-2 gap-3 bg-radar-950">
          {isLoading ? (
            <div className="col-span-2 p-12 flex flex-col items-center justify-center text-vessel-teal">
              <Loader2 className="w-8 h-8 animate-spin mb-4" />
              <span className="text-xs tracking-widest uppercase">Fetching Vessel Telemetry...</span>
            </div>
          ) : filteredVessels.length === 0 ? (
            <div className="col-span-2 p-8 text-center text-radar-500 text-xs">
              NO VESSELS MATCH SEARCH CRITERIA
            </div>
          ) : (
            filteredVessels.slice(0, 100).map((v) => {
              const isSuspect = suspectMmsiSet.has(v.mmsi);
              const hasGap = v.ais_gap_minutes !== null && v.ais_gap_minutes > 0;

              return (
                <div
                  key={v.mmsi}
                  role="button"
                  tabIndex={0}
                  aria-label={`Select vessel ${v.name}, MMSI ${v.mmsi}, type ${v.vessel_type}`}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onSelectVessel(v);
                      onClose();
                    }
                  }}
                  onClick={() => {
                    onSelectVessel(v);
                    onClose();
                  }}
                  className="bg-radar-900 border border-radar-750 hover:border-vessel-teal/70 p-2.5 rounded-xs cursor-pointer transition-all hover:shadow-lg flex gap-3 group focus:outline-none focus:ring-1 focus:ring-vessel-teal"
                >
                  {/* Photo Thumbnail with Silhouette Fallback */}
                  <VesselCardThumbnail vessel={v} isSuspect={isSuspect} />

                  {/* Vessel Information */}
                  <div className="flex-1 min-w-0 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold text-radar-100 truncate group-hover:text-vessel-teal">
                          {v.name}
                        </h4>
                        {v.flag && (
                          <span className="text-[10px] text-radar-400 shrink-0">
                            {v.flag}
                          </span>
                        )}
                      </div>

                      <div className="text-[10px] text-radar-400 mt-0.5">
                        MMSI: <span className="text-radar-200">{v.mmsi}</span> • IMO: <span className="text-radar-300">{v.imo || 'UNKNOWN'}</span>
                      </div>
                      <div className="text-[10px] text-radar-400">
                        {v.vessel_type}
                      </div>
                    </div>

                    {/* Bottom Status / Kinematics */}
                    <div className="flex items-center justify-between pt-1 border-t border-radar-800 text-[10px]">
                      <span className="text-radar-300">
                        {v.speed_knots}kt @ {v.heading}°
                      </span>

                      {hasGap ? (
                        <span className="text-amber-400 font-bold flex items-center gap-0.5">
                          <AlertTriangle className="w-3 h-3" />
                          <span>{v.ais_gap_minutes}m DARK</span>
                        </span>
                      ) : (
                        <span className="text-emerald-400">100% AIS</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-2.5 bg-radar-900 border-t border-radar-750 flex items-center justify-between text-[11px] text-radar-400">
          <span>Click any ship card to inspect full high-resolution photography & attribution analytics</span>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded-xs bg-radar-800 hover:bg-radar-750 border border-radar-700 text-radar-200"
          >
            CLOSE
          </button>
        </div>
      </div>
    </div>
  );
});
