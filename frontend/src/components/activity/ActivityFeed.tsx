import React, { useState } from 'react';
import { 
  ChevronDown, 
  ChevronUp, 
  AlertCircle, 
  AlertTriangle, 
  Info, 
  Terminal, 
  Radio, 
  ExternalLink,
  Trash2,
  Loader2
} from 'lucide-react';
import { OperationalAlert, Spill, Vessel } from '../../types/api';
import { safeFormatTimestamp } from '../../utils/core';

interface ActivityFeedProps {
  alerts: OperationalAlert[];
  spills: Spill[];
  vessels: Vessel[];
  onSelectSpill: (spill: Spill) => void;
  onSelectVessel: (vessel: Vessel) => void;
  isLoading?: boolean;
}

export const ActivityFeed: React.FC<ActivityFeedProps> = React.memo(({
  alerts,
  spills,
  vessels,
  onSelectSpill,
  onSelectVessel,
  isLoading,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [filterSeverity, setFilterSeverity] = useState<'ALL' | 'CRITICAL' | 'WARNING' | 'INFO'>('ALL');

  const filteredAlerts = alerts.filter(
    (a) => filterSeverity === 'ALL' || a.severity === filterSeverity
  );

  const handleAlertClick = (alert: OperationalAlert) => {
    if (!alert.targetId) return;

    if (alert.targetType === 'spill') {
      const s = spills.find((sp) => sp.id === alert.targetId);
      if (s) onSelectSpill(s);
    } else if (alert.targetType === 'vessel') {
      const v = vessels.find((vs) => vs.mmsi === alert.targetId);
      if (v) onSelectVessel(v);
    }
  };

  return (
    <div className="bg-radar-900 border-t border-radar-700/80 z-20 select-none shadow-2xl transition-all">
      {/* Drawer Bar Header */}
      <div className="h-8 px-4 bg-radar-850 flex items-center justify-between font-mono text-xs border-b border-radar-800">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-expanded={isExpanded}
            aria-label={isExpanded ? "Collapse Operational Activity Log" : "Expand Operational Activity Log"}
            className="flex items-center gap-1.5 text-radar-200 hover:text-white font-bold cursor-pointer"
          >
            <Terminal className="w-3.5 h-3.5 text-spill-amber" />
            <span>OPERATIONAL ACTIVITY LOG</span>
            <span className="px-1.5 py-0.2 rounded-xs bg-radar-800 text-radar-400 border border-radar-700 text-[10px]">
              {alerts.length}
            </span>
            {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
          </button>

          {/* Quick preview of latest alert when collapsed */}
          {!isExpanded && alerts.length > 0 && (
            <div 
              role="button"
              tabIndex={0}
              aria-label={`Latest alert: ${alerts[0].summary}. Click to inspect.`}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleAlertClick(alerts[0]);
                }
              }}
              onClick={() => handleAlertClick(alerts[0])}
              className="hidden md:flex items-center gap-2 text-[11px] text-radar-300 truncate cursor-pointer hover:text-white max-w-xl focus:outline-none focus:underline"
            >
              <span className="text-radar-500 font-mono text-[10px]">{safeFormatTimestamp(alerts[0].timestamp)}</span>
              <span className={`px-1 py-0.2 rounded-xs text-[9px] font-bold ${
                alerts[0].severity === 'CRITICAL' ? 'bg-suspect-crimson/20 text-suspect-crimson' :
                alerts[0].severity === 'WARNING' ? 'bg-spill-amber/20 text-spill-amber' :
                'bg-radar-800 text-radar-400'
              }`}>
                [{alerts[0].category}]
              </span>
              <span className="truncate">{alerts[0].summary}</span>
            </div>
          )}
        </div>

        {/* Severity Filter Tabs */}
        {isExpanded && (
          <div className="flex items-center gap-1 text-[10px]" role="tablist" aria-label="Alert severity filters">
            {(['ALL', 'CRITICAL', 'WARNING', 'INFO'] as const).map((sev) => (
              <button
                type="button"
                key={sev}
                role="tab"
                aria-selected={filterSeverity === sev}
                onClick={() => setFilterSeverity(sev)}
                className={`px-2 py-0.5 rounded-xs border cursor-pointer ${
                  filterSeverity === sev
                    ? 'bg-radar-750 border-radar-600 text-radar-100 font-bold'
                    : 'bg-radar-850 border-radar-750 text-radar-400 hover:text-radar-200'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Expanded Table Feed */}
      {isExpanded && (
        <div className="h-48 overflow-y-auto font-mono text-xs divide-y divide-radar-800/80 bg-radar-950">
          {isLoading ? (
            <div className="p-12 flex flex-col items-center justify-center text-radar-400">
              <Loader2 className="w-6 h-6 animate-spin mb-3" />
              <span className="text-[10px] tracking-widest uppercase">Fetching Operational Logs...</span>
            </div>
          ) : filteredAlerts.length === 0 ? (
            <div className="p-4 text-center text-radar-500 text-[11px]">
              NO OPERATIONAL LOGS FOR THIS SEVERITY FILTER
            </div>
          ) : (
            filteredAlerts.slice(0, 100).map((alert) => {
              const hasTarget = Boolean(alert.targetId);

              return (
                <div
                  key={alert.id}
                  role={hasTarget ? "button" : undefined}
                  tabIndex={hasTarget ? 0 : undefined}
                  aria-label={hasTarget ? `Alert: ${alert.summary}. Click to view target ${alert.targetId}` : undefined}
                  onKeyDown={hasTarget ? (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleAlertClick(alert);
                    }
                  } : undefined}
                  onClick={() => handleAlertClick(alert)}
                  className={`px-4 py-2 flex items-start justify-between gap-4 transition-colors ${
                    hasTarget ? 'cursor-pointer hover:bg-radar-850/80 focus:outline-none focus:bg-radar-850' : ''
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {/* Timestamp */}
                    <span className="text-radar-500 text-[11px] shrink-0 pt-0.5">
                      {safeFormatTimestamp(alert.timestamp)}
                    </span>

                    {/* Category Badge */}
                    <span className={`px-1.5 py-0.5 rounded-xs text-[10px] font-bold shrink-0 ${
                      alert.severity === 'CRITICAL' ? 'bg-suspect-crimson/20 border border-suspect-crimson/50 text-suspect-crimson' :
                      alert.severity === 'WARNING' ? 'bg-spill-amber/20 border border-spill-amber/50 text-spill-amber' :
                      'bg-radar-800 border border-radar-700 text-radar-300'
                    }`}>
                      [{alert.category}]
                    </span>

                    {/* Content */}
                    <div>
                      <div className="font-semibold text-radar-200 text-xs flex items-center gap-2">
                        <span>{alert.summary}</span>
                        {hasTarget && (
                          <span className="text-[10px] text-spill-amber underline flex items-center gap-0.5">
                            INSPECT <ExternalLink className="w-2.5 h-2.5" />
                          </span>
                        )}
                      </div>
                      {alert.detail && (
                        <p className="text-radar-400 text-[11px] mt-0.5">{alert.detail}</p>
                      )}
                    </div>
                  </div>

                  <span className="text-radar-600 text-[10px] shrink-0 font-mono">
                    ID:{alert.id}
                  </span>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
});
