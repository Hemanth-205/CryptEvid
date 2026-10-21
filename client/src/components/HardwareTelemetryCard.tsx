import React, { useState, useEffect, useCallback } from 'react';
import { 
  Usb, 
  ShieldCheck, 
  ShieldAlert, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  UserCheck, 
  AlertTriangle,
  Radio,
  Cpu,
  Layers,
  Fingerprint
} from 'lucide-react';
import { hardwareApi, type HardwareBridgeStatus, type HardwareEvent } from '../services/api';

export const HardwareTelemetryCard: React.FC = () => {
  const [bridgeStatus, setBridgeStatus] = useState<HardwareBridgeStatus | null>(null);
  const [events, setEvents] = useState<HardwareEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTelemetry = useCallback(async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      const [statusData, eventsData] = await Promise.all([
        hardwareApi.getBridgeStatus(),
        hardwareApi.getHardwareEvents(10)
      ]);
      setBridgeStatus(statusData);
      setEvents(eventsData?.events || []);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load hardware telemetry:', err);
      setError('Unable to query hardware bridge telemetry.');
    } finally {
      setLoading(false);
      if (isManual) setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchTelemetry();
    // Poll telemetry every 3 seconds for near real-time reactivity
    const interval = setInterval(() => {
      fetchTelemetry();
    }, 3000);

    return () => clearInterval(interval);
  }, [fetchTelemetry]);

  const latestEvent: HardwareEvent | null = bridgeStatus?.last_event || (events.length > 0 ? events[0] : null);

  const formatTimestamp = (isoStr?: string) => {
    if (!isoStr) return '--';
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' (' + d.toLocaleDateString() + ')';
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="ws-panel p-5 space-y-5 animate-fade-in-up">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 shadow-xs">
            <Usb className="w-4.5 h-4.5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider font-mono">
                Hardware Ingestion & Biometric Telemetry
              </h2>
              {/* Dynamic Status Badge */}
              {bridgeStatus?.status === 'Connected' ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                  CONNECTED ({bridgeStatus.port || 'COM5'})
                </span>
              ) : bridgeStatus?.status === 'Error' ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-red-100 text-red-800 border border-red-300">
                  <AlertTriangle className="w-3 h-3" />
                  ERROR ({bridgeStatus.port || 'COM5'})
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-600 border border-slate-300">
                  <Radio className="w-3 h-3 text-slate-400" />
                  DISCONNECTED
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              ESP32 USB Serial Bridge (COM5 @ 115200 baud) • MFRC522 RFID & R307 Optical Sensor
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchTelemetry(true)}
            disabled={refreshing}
            className="ws-btn ws-btn-secondary text-xs py-1.5 px-3"
            title="Refresh hardware bridge telemetry"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>{refreshing ? 'Polling...' : 'Sync Bridge'}</span>
          </button>
        </div>
      </div>

      {/* Error state alert */}
      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-red-500" />
            <span>{error}</span>
          </div>
          <button 
            onClick={() => fetchTelemetry(true)} 
            className="font-bold underline text-red-800 hover:text-red-900"
          >
            Retry
          </button>
        </div>
      )}

      {/* Main Grid: Latest Event Spotlight + Bridge Hardware Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Card 1: Latest Authentication Event Spotlight */}
        <div className="lg:col-span-2 p-4 rounded-xl border border-slate-200 bg-white shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-500" />
              Latest Hardware Authentication Event
            </span>
            {latestEvent && (
              <span className="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
                <Clock className="w-3 h-3" />
                {formatTimestamp(latestEvent.timestamp)}
              </span>
            )}
          </div>

          {loading ? (
            <div className="py-8 flex flex-col items-center justify-center text-xs text-slate-400 gap-2">
              <RefreshCw className="w-5 h-5 animate-spin text-indigo-500" />
              <span>Querying latest authentication records...</span>
            </div>
          ) : !latestEvent ? (
            <div className="py-8 text-center text-xs text-slate-400 bg-slate-50/50 rounded-lg border border-dashed border-slate-200">
              <Fingerprint className="w-8 h-8 text-slate-300 mx-auto mb-1" />
              <p className="font-semibold text-slate-600">No Hardware Events Received</p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Scan an authorized RFID card or verify fingerprint on the connected ESP32 terminal.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              {/* Event Outcome Badge Box */}
              <div className={`p-3.5 rounded-lg border flex flex-col justify-between ${
                latestEvent.status === 'GRANTED' 
                  ? 'bg-emerald-50/60 border-emerald-200' 
                  : 'bg-rose-50/60 border-rose-200'
              }`}>
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
                    Reported Result
                  </span>
                  {latestEvent.status === 'GRANTED' ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-emerald-600 text-white shadow-xs">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      GRANTED
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-rose-600 text-white shadow-xs">
                      <XCircle className="w-3.5 h-3.5" />
                      DENIED
                    </span>
                  )}
                </div>

                <div className="mt-3">
                  <div className="text-[11px] text-slate-500">Reason / Hardware Code</div>
                  <div className="text-xs font-mono font-bold text-slate-800">
                    {latestEvent.reason}
                  </div>
                </div>

                <div className="mt-2 text-[11px] text-slate-500">
                  UID: <span className="font-mono font-bold text-slate-900 bg-white/80 px-1.5 py-0.5 rounded border border-slate-200">{latestEvent.uid}</span>
                </div>
              </div>

              {/* Backend Identity Verification Box */}
              <div className={`p-3.5 rounded-lg border flex flex-col justify-between ${
                latestEvent.is_identity_verified 
                  ? 'bg-blue-50/60 border-blue-200' 
                  : 'bg-amber-50/60 border-amber-200'
              }`}>
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
                    Backend Verified Identity
                  </span>
                  {latestEvent.is_identity_verified ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-blue-100 text-blue-800 border border-blue-300">
                      <ShieldCheck className="w-3 h-3 text-blue-600" />
                      AUTHENTICATED
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                      <ShieldAlert className="w-3 h-3 text-amber-600" />
                      UNVERIFIED
                    </span>
                  )}
                </div>

                <div className="mt-3">
                  <div className="text-[11px] text-slate-500">Mapped Investigator</div>
                  {latestEvent.mapped_investigator ? (
                    <div>
                      <div className="text-xs font-bold text-slate-900 flex items-center gap-1">
                        <UserCheck className="w-3.5 h-3.5 text-blue-600" />
                        {latestEvent.mapped_investigator.name}
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        {latestEvent.mapped_investigator.email} ({latestEvent.mapped_investigator.role})
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs font-semibold text-amber-700 italic">
                      Unknown / Unregistered RFID UID
                    </div>
                  )}
                </div>

                <div className="mt-2 text-[10px] text-slate-500 truncate" title={latestEvent.verification_notes}>
                  {latestEvent.verification_notes || 'Processed via USB bridge protocol v1'}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Card 2: Bridge Diagnostics & Port Configuration */}
        <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 shadow-xs space-y-3 flex flex-col justify-between">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-indigo-500" />
              Serial Port Diagnostics
            </span>

            <div className="mt-3 space-y-2 text-xs">
              <div className="flex items-center justify-between pb-1.5 border-b border-slate-200">
                <span className="text-slate-500">Port Identifier</span>
                <span className="font-mono font-bold text-slate-800 bg-white px-1.5 py-0.5 rounded border border-slate-200">
                  {bridgeStatus?.port || 'COM5'}
                </span>
              </div>
              <div className="flex items-center justify-between pb-1.5 border-b border-slate-200">
                <span className="text-slate-500">Serial Baud Rate</span>
                <span className="font-mono font-bold text-slate-800">
                  {bridgeStatus?.baud_rate || 115200} bps
                </span>
              </div>
              <div className="flex items-center justify-between pb-1.5 border-b border-slate-200">
                <span className="text-slate-500">Bridge Heartbeat</span>
                <span className="font-mono text-slate-700 text-[11px]">
                  {bridgeStatus?.last_heartbeat ? formatTimestamp(bridgeStatus.last_heartbeat) : 'Awaiting heartbeat'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Protocol Spec</span>
                <span className="font-mono text-blue-700 text-[11px] font-semibold">
                  CRYPTEVID|1|STATUS|UID|REASON
                </span>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-500">
            {bridgeStatus?.status === 'Connected' ? (
              <span className="text-emerald-700 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Serial bridge active. Ready to ingest physical scans.
              </span>
            ) : (
              <span className="text-slate-500 flex items-center gap-1">
                <Radio className="w-3.5 h-3.5 text-amber-500" />
                Start bridge with: <code className="bg-slate-200 px-1 py-0.5 rounded text-[10px]">python hardware_serial_bridge.py</code>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Table: Recent Authentication Events History */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700 font-mono">
            Recent Hardware Authentication Events
          </span>
          <span className="text-[11px] text-slate-400">
            Showing latest {events.length} events
          </span>
        </div>

        <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
          <div className="table-responsive max-h-60 overflow-y-auto">
            <table className="ws-table min-w-[650px] text-xs">
              <thead className="bg-slate-50 sticky top-0 z-10">
                <tr>
                  <th className="py-2 px-3 text-left">Timestamp</th>
                  <th className="py-2 px-3 text-left">Status</th>
                  <th className="py-2 px-3 text-left">RFID UID</th>
                  <th className="py-2 px-3 text-left">Reason</th>
                  <th className="py-2 px-3 text-left">Mapped Investigator</th>
                  <th className="py-2 px-3 text-left">Verification</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {events.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-6 text-slate-400 font-mono text-xs">
                      {loading ? 'Fetching event logs...' : 'No hardware authentication events recorded yet.'}
                    </td>
                  </tr>
                ) : (
                  events.map((evt) => (
                    <tr key={evt.event_id || evt._id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-2 px-3 font-mono text-[11px] text-slate-500 whitespace-nowrap">
                        {formatTimestamp(evt.timestamp)}
                      </td>
                      <td className="py-2 px-3 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold ${
                          evt.status === 'GRANTED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}>
                          {evt.status}
                        </span>
                      </td>
                      <td className="py-2 px-3 font-mono font-bold text-slate-800 whitespace-nowrap">
                        {evt.uid}
                      </td>
                      <td className="py-2 px-3 font-mono text-slate-600 text-[11px] whitespace-nowrap">
                        {evt.reason}
                      </td>
                      <td className="py-2 px-3 whitespace-nowrap">
                        {evt.mapped_investigator ? (
                          <div className="font-semibold text-slate-800 flex items-center gap-1">
                            <span>{evt.mapped_investigator.name}</span>
                            <span className="text-[10px] text-slate-400 font-normal">({evt.mapped_investigator.role})</span>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic text-[11px]">Unregistered UID</span>
                        )}
                      </td>
                      <td className="py-2 px-3 whitespace-nowrap">
                        {evt.is_identity_verified ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-700">
                            <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                            Verified
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700">
                            <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
                            Unverified
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HardwareTelemetryCard;
