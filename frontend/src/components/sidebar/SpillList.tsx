import React, { useState } from 'react';
import { 
  Flame, 
  ChevronLeft, 
  ChevronRight, 
  Filter, 
  ArrowUpDown, 
  Satellite, 
  ShieldAlert,
  Search,
  Loader2
} from 'lucide-react';
import { Spill, SpillStatus } from '../../types/api';
import { useDebounce, formatTimeAgo } from '../../utils/core';

interface SpillListProps {
  spills: Spill[];
  selectedSpill: Spill | null;
  onSelectSpill: (spill: Spill) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isLoading?: boolean;
}

type SortField = 'confidence' | 'recency' | 'area';

export const SpillList: React.FC<SpillListProps> = React.memo(({
  spills,
  selectedSpill,
  onSelectSpill,
  isCollapsed,
  onToggleCollapse,
  isLoading = false,
}) => {
  const [filterStatus, setFilterStatus] = useState<SpillStatus | 'all'>('all');
  const [minConfidence, setMinConfidence] = useState<number>(0);
  const [sortField, setSortField] = useState<SortField>('confidence');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const debouncedSearch = useDebounce(searchQuery, 300);

  // Filter and sort
  const filteredSpills = spills
    .filter((s) => {
      if (filterStatus !== 'all' && s.status !== filterStatus) return false;
      if (s.confidence < minConfidence) return false;
      if (debouncedSearch) {
        const q = debouncedSearch.toLowerCase();
        return s.id.toLowerCase().includes(q) || s.satellite_source.toLowerCase().includes(q);
      }
      return true;
    })
    .sort((a, b) => {
      if (sortField === 'confidence') return b.confidence - a.confidence;
      if (sortField === 'area') return b.area_km2 - a.area_km2;
      return new Date(b.detected_at || 0).getTime() - new Date(a.detected_at || 0).getTime();
    });


  if (isCollapsed) {
    return (
      <div className="w-10 bg-radar-900 border-r border-radar-700/80 flex flex-col items-center py-3 z-20 select-none">
        <button
          onClick={onToggleCollapse}
          title="Expand Spills Panel"
          className="p-1.5 rounded-xs bg-radar-800 border border-radar-700 hover:bg-radar-750 text-radar-300"
        >
          <ChevronRight className="w-4 h-4" />
        </button>

        <div className="mt-6 flex flex-col items-center gap-4 text-xs font-mono">
          <div className="p-1.5 rounded-xs bg-spill-amber/15 border border-spill-amber/40 text-spill-amber relative">
            <Flame className="w-4 h-4" />
            <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-spill-amber text-radar-950 text-[9px] font-bold flex items-center justify-center">
              {spills.length}
            </span>
          </div>
          <span className="text-[10px] text-radar-500 uppercase tracking-widest writing-mode-vertical rotate-180">
            SAR SPILLS
          </span>
        </div>
      </div>
    );
  }

  return (
    <aside className="w-80 bg-radar-900 border-r border-radar-700/80 flex flex-col h-full z-20 select-none shadow-xl">
      {/* Panel Header */}
      <div className="p-3 border-b border-radar-700/80 bg-radar-850 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-xs bg-spill-amber/15 text-spill-amber border border-spill-amber/40">
            <Flame className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-xs font-mono font-bold tracking-tight text-radar-100 flex items-center gap-1.5">
              <span>ACTIVE SPILLS</span>
              <span className="px-1.5 py-0.2 rounded-xs bg-radar-800 text-spill-amber border border-radar-700 text-[10px]">
                {filteredSpills.length}
              </span>
            </h2>
            <p className="text-[9px] font-mono text-radar-500 uppercase tracking-wider">
              SENTINEL-1 SAR DETECTIONS
            </p>
          </div>
        </div>

        <button
          onClick={onToggleCollapse}
          title="Collapse Panel"
          className="p-1 rounded-xs bg-radar-800 border border-radar-700 hover:bg-radar-750 text-radar-400 hover:text-radar-200"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* Filter and Sort Toolbar */}
      <div className="p-2 border-b border-radar-700/80 bg-radar-900 space-y-1.5 text-xs font-mono">
        {/* Search Input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-radar-500 absolute left-2 top-2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="FILTER BY ID / SENSOR..."
            className="w-full bg-radar-850 border border-radar-700/80 rounded-xs pl-7 pr-2 py-1 text-[11px] text-radar-200 placeholder-radar-500 focus:outline-none focus:border-radar-500"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center justify-between gap-1 text-[10px]">
          <div className="flex items-center gap-1">
            {(['all', 'active', 'monitoring', 'resolved'] as const).map((st) => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                className={`px-1.5 py-0.5 rounded-xs border uppercase ${
                  filterStatus === st
                    ? 'bg-radar-750 border-radar-500 text-radar-100 font-semibold'
                    : 'bg-radar-850 border-radar-700/70 text-radar-400 hover:text-radar-200'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          {/* Confidence Filter & Sort Selector */}
          <div className="flex items-center gap-1.5 text-radar-400">
            <select
              aria-label="Filter Spills By Minimum Confidence"
              value={minConfidence}
              onChange={(e) => setMinConfidence(Number(e.target.value))}
              className="bg-radar-850 border border-radar-700 rounded-xs text-[10px] text-radar-300 py-0.5 px-1 focus:outline-none cursor-pointer"
            >
              <option value="0">ALL CONF</option>
              <option value="0.75">≥75% CONF</option>
              <option value="0.85">≥85% CONF</option>
              <option value="0.90">≥90% HIGH</option>
              <option value="0.95">≥95% ULTRA</option>
            </select>

            <div className="flex items-center gap-0.5">
              <ArrowUpDown className="w-3 h-3 text-radar-400" />
              <select
                aria-label="Sort Spills By"
                value={sortField}
                onChange={(e) => setSortField(e.target.value as SortField)}
                className="bg-radar-850 border border-radar-700 rounded-xs text-[10px] text-radar-300 py-0.5 px-1 focus:outline-none cursor-pointer"
              >
                <option value="confidence">CONF</option>
                <option value="area">AREA</option>
                <option value="recency">TIME</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Spill Items List */}
      <div className="flex-1 overflow-y-auto divide-y divide-radar-800/80">
        {isLoading ? (
          <div className="p-12 flex flex-col items-center justify-center text-spill-amber">
            <Loader2 className="w-6 h-6 animate-spin mb-3" />
            <span className="text-[10px] tracking-widest uppercase">Fetching SAR Feed...</span>
          </div>
        ) : filteredSpills.length === 0 ? (
          <div className="p-6 text-center text-xs font-mono text-radar-500">
            NO SPILLS MATCH SELECTION
          </div>
        ) : (
          filteredSpills.slice(0, 100).map((spill) => {
            const isSelected = selectedSpill?.id === spill.id;
            const statusColor = 
              spill.status === 'active' ? 'bg-spill-amber' :
              spill.status === 'monitoring' ? 'bg-sky-400' : 'bg-emerald-400';

            return (
              <div
                key={spill.id}
                role="button"
                tabIndex={0}
                aria-label={`Select spill ${spill.id}, confidence ${(spill.confidence * 100).toFixed(1)} percent`}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectSpill(spill);
                  }
                }}
                onClick={() => onSelectSpill(spill)}
                className={`p-2.5 cursor-pointer font-mono transition-colors border-l-2 focus:outline-none focus:ring-1 focus:ring-spill-amber ${
                  isSelected
                    ? 'bg-radar-800/90 border-spill-amber text-radar-100 shadow-inner'
                    : 'hover:bg-radar-850 border-transparent text-radar-300'
                }`}
              >
                {/* Header row: Status Dot, ID, Age */}
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5 overflow-hidden">
                    <span className={`w-2 h-2 rounded-full ${statusColor} shrink-0 ${spill.status === 'active' ? 'animate-pulse' : ''}`} />
                    <span className="font-bold text-xs tracking-tight truncate text-radar-100">
                      {spill.id}
                    </span>
                  </div>
                  <span className="text-[10px] text-radar-500 shrink-0">
                    {formatTimeAgo(spill.detected_at)}
                  </span>
                </div>

                {/* Metrics Row: Area, Confidence, Satellite Platform */}
                <div className="grid grid-cols-3 gap-1 text-[11px] mt-1 pt-1 border-t border-radar-800/60 text-radar-400">
                  <div>
                    <span className="text-[9px] text-radar-500 block uppercase">AREA</span>
                    <span className="text-radar-200 font-semibold">{spill.area_km2.toFixed(1)} km²</span>
                  </div>

                  <div>
                    <span className="text-[9px] text-radar-500 block uppercase">CONFIDENCE</span>
                    <span className={`font-semibold ${spill.confidence > 0.9 ? 'text-spill-amber' : 'text-radar-200'}`}>
                      {(spill.confidence * 100).toFixed(1)}%
                    </span>
                  </div>

                  <div className="text-right">
                    <span className="text-[9px] text-radar-500 block uppercase">SENSOR</span>
                    <span className="text-radar-300 text-[10px] truncate block" title={spill.satellite_source}>
                      {spill.satellite_source.split(' ')[0]}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer System Status */}
      <div className="p-2 bg-radar-950 border-t border-radar-700/80 text-[10px] font-mono text-radar-500 flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Satellite className="w-3 h-3 text-radar-400" />
          <span>CDSE OData Sentinel-1</span>
        </div>
        <span className="text-emerald-400">INGESTION OK</span>
      </div>
    </aside>
  );
});
