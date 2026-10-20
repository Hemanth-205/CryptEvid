import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw, 
  Search, 
  Shield, 
  Activity, 
  Terminal, 
  Lock, 
  Globe 
} from 'lucide-react';
import { securityApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { formatIsoDateSafe } from '../utils/date';

interface SecurityAlert {
  alert_id: string;
  timestamp: string;
  severity: string;
  status: 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'DISMISSED';
  title: string;
  description: string;
  source_ip: string;
  related_event_ids: string[];
  resolved_by?: string;
  resolved_at?: string;
  resolution_notes?: string;
}

interface SecurityEvent {
  event_id: string;
  timestamp: string;
  event_type: string;
  ip_address: string;
  ip_source: string;
  method?: string;
  device_info: {
    user_agent: string;
    client_type: string;
    browser: string;
    os: string;
    mac_address?: string;
  };
  target_resource: {
    resource_type: string;
    resource_id?: string;
    action: string;
    path: string;
  };
  auth_context: {
    is_authenticated: boolean;
    user_id?: string;
    email?: string;
    role?: string;
  };
  case_id?: string;
  evidence_id?: string;
  result: string;
  failure_reason: string;
  severity: string;
}

interface SecurityStats {
  total_events: number;
  open_alerts: number;
  blocked_attempts: number;
  unique_ips: number;
  events_by_type: Record<string, number>;
}

export const SecurityAlertsPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'alerts' | 'events'>('alerts');
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [stats, setStats] = useState<SecurityStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [updatingAlertId, setUpdatingAlertId] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsRes, alertsRes, eventsRes] = await Promise.all([
        securityApi.getStats().catch(() => null),
        securityApi.getAlerts({
          status: statusFilter !== 'ALL' ? statusFilter : undefined,
          limit: 100
        }).catch(() => ({ alerts: [], total: 0 })),
        securityApi.getEvents({
          limit: 100
        }).catch(() => ({ events: [], total: 0 }))
      ]);

      if (statsRes) setStats(statsRes);
      if (alertsRes) setAlerts(alertsRes.alerts || []);
      if (eventsRes) setEvents(eventsRes.events || []);
    } catch (err) {
      console.error('Failed to load security data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter]);

  const handleUpdateStatus = async (alertId: string, newStatus: string) => {
    setUpdatingAlertId(alertId);
    try {
      await securityApi.updateAlertStatus(alertId, {
        status: newStatus,
        notes: `Status changed to ${newStatus}`
      });
      await fetchData();
    } catch (err) {
      console.error('Failed to update alert status', err);
    } finally {
      setUpdatingAlertId(null);
    }
  };

  const filteredEvents = events.filter(e => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (e.ip_address && e.ip_address.toLowerCase().includes(q)) ||
      (e.event_type && e.event_type.toLowerCase().includes(q)) ||
      (e.target_resource?.path && e.target_resource.path.toLowerCase().includes(q)) ||
      (e.failure_reason && e.failure_reason.toLowerCase().includes(q)) ||
      (e.auth_context?.email && e.auth_context.email.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6 relative z-10">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center text-red-600 shadow-xs">
              <ShieldAlert className="w-4.5 h-4.5" />
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight font-sans">
              Security Operations Center
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1 font-sans">
            Real-time security events, unauthorized intrusion telemetry, and forensic audit alerts.
          </p>
        </div>

        <button
          onClick={fetchData}
          disabled={loading}
          className="ws-btn ws-btn-secondary"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Sync Live Feed</span>
        </button>
      </div>

      {/* Primary KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="ws-panel p-4.5 space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
            <span>Blocked Intrusions</span>
            <div className="w-7 h-7 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center text-red-600">
              <Lock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-red-600 font-mono tracking-tight">
            {stats?.blocked_attempts ?? 0}
          </div>
          <div className="text-[11px] text-slate-500">100% Intercepted & Isolated</div>
        </div>

        <div className="ws-panel p-4.5 space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
            <span>Active Incidents</span>
            <div className="w-7 h-7 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-amber-600 font-mono tracking-tight">
            {stats?.open_alerts ?? 0}
          </div>
          <div className="text-[11px] text-slate-500">Pending Investigator Triage</div>
        </div>

        <div className="ws-panel p-4.5 space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
            <span>Threat Origin IPs</span>
            <div className="w-7 h-7 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
              <Globe className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-blue-600 font-mono tracking-tight">
            {stats?.unique_ips ?? 0}
          </div>
          <div className="text-[11px] text-slate-500">Remote & Forwarded Endpoints</div>
        </div>

        <div className="ws-panel p-4.5 space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
            <span>Audit Events Stream</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-emerald-600 font-mono tracking-tight">
            {stats?.total_events ?? 0}
          </div>
          <div className="text-[11px] text-slate-500">Cryptographic Event Ledger</div>
        </div>
      </div>

      {/* Tabs & Controls */}
      <div className="ws-panel p-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('alerts')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'alerts'
                ? 'bg-red-50 text-red-700 border border-red-200 font-bold'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Incident Alerts ({alerts.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('events')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'events'
                ? 'bg-blue-50 text-blue-700 border border-blue-200 font-bold'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Telemetry Access Stream ({events.length})</span>
          </button>
        </div>

        {activeTab === 'alerts' && (
          <div className="flex items-center gap-1.5 text-xs font-mono">
            <span className="text-slate-500 text-[11px] mr-1">STATUS:</span>
            {['ALL', 'OPEN', 'INVESTIGATING', 'RESOLVED', 'DISMISSED'].map(s => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-2.5 py-1 rounded text-[11px] uppercase font-mono transition-colors ${
                  statusFilter === s
                    ? 'bg-slate-900 text-white font-bold'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="relative w-full sm:w-72">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter IP, route, reason..."
              className="ws-input w-full pl-9 py-1.5 text-xs font-mono"
            />
          </div>
        )}
      </div>

      {/* Tab 1: Security Alerts */}
      {activeTab === 'alerts' && (
        <div className="space-y-3.5">
          {loading ? (
            <div className="ws-panel p-12 text-center text-slate-500 text-xs font-mono flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
              <span>Querying security alerts...</span>
            </div>
          ) : alerts.length === 0 ? (
            <div className="ws-panel p-12 text-center">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
              <div className="text-slate-800 font-bold text-sm">No Security Incidents Detected</div>
              <div className="text-xs text-slate-500 mt-1">
                All evidentiary vaults and API routes operate within nominal security parameters.
              </div>
            </div>
          ) : (
            alerts.map(alert => (
              <div
                key={alert.alert_id}
                className="ws-panel p-4.5 space-y-3 border-l-4 border-l-amber-500 shadow-xs"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-3">
                  <div className="flex items-center gap-2.5">
                    <span className={`ws-badge ${
                      alert.severity === 'CRITICAL' ? 'ws-badge-tampered' :
                      alert.severity === 'HIGH' ? 'ws-badge-amber' :
                      'ws-badge-subtle'
                    }`}>
                      {alert.severity}
                    </span>
                    <span className="text-sm font-bold text-slate-900">{alert.title}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className={`ws-badge ${
                      alert.status === 'OPEN' ? 'ws-badge-tampered' :
                      alert.status === 'INVESTIGATING' ? 'ws-badge-amber' :
                      alert.status === 'RESOLVED' ? 'ws-badge-verified' :
                      'ws-badge-subtle'
                    }`}>
                      {alert.status}
                    </span>
                    <span className="text-xs text-slate-500 font-mono">
                      {formatIsoDateSafe(alert.timestamp, 19)} UTC
                    </span>
                  </div>
                </div>

                <div className="text-xs text-slate-600 leading-relaxed font-sans">
                  {alert.description}
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 pt-3 text-xs border-t border-slate-100">
                  <div className="flex items-center gap-4 text-slate-600">
                    <span>Source IP: <strong className="text-blue-600 font-mono">{alert.source_ip}</strong></span>
                    <span>•</span>
                    <span>Correlated Events: <strong className="text-slate-900">{alert.related_event_ids?.length || 0}</strong></span>
                    {alert.resolved_by && (
                      <>
                        <span>•</span>
                        <span>Resolved by: <strong className="text-slate-900">{alert.resolved_by}</strong></span>
                      </>
                    )}
                  </div>

                  {user?.role === 'admin' && (
                    <div className="flex items-center gap-2">
                      {alert.status !== 'INVESTIGATING' && alert.status !== 'RESOLVED' && (
                        <button
                          onClick={() => handleUpdateStatus(alert.alert_id, 'INVESTIGATING')}
                          disabled={updatingAlertId === alert.alert_id}
                          className="ws-btn ws-btn-secondary text-xs py-1 px-3 text-blue-700"
                        >
                          Investigate
                        </button>
                      )}
                      {alert.status !== 'RESOLVED' && (
                        <button
                          onClick={() => handleUpdateStatus(alert.alert_id, 'RESOLVED')}
                          disabled={updatingAlertId === alert.alert_id}
                          className="ws-btn ws-btn-secondary text-xs py-1 px-3 text-emerald-700"
                        >
                          Mark Resolved
                        </button>
                      )}
                      {alert.status !== 'DISMISSED' && alert.status !== 'RESOLVED' && (
                        <button
                          onClick={() => handleUpdateStatus(alert.alert_id, 'DISMISSED')}
                          disabled={updatingAlertId === alert.alert_id}
                          className="ws-btn ws-btn-secondary text-xs py-1 px-3 text-slate-600"
                        >
                          Dismiss
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab 2: Intercepted Events Stream */}
      {activeTab === 'events' && (
        <div className="ws-panel overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-slate-500 text-xs font-mono flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
              <span>Querying intercepted events...</span>
            </div>
          ) : filteredEvents.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <Shield className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <div className="text-slate-800 font-bold text-sm">No Events Logged</div>
              <div className="text-xs text-slate-500 mt-1">Zero security violations matching current query filter.</div>
            </div>
          ) : (
            <div className="divide-y divide-slate-200">
              {filteredEvents.map(event => (
                <div key={event.event_id} className="p-4 hover:bg-slate-50/70 transition-colors space-y-2.5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="ws-badge ws-badge-tampered text-[10px]">
                        {event.result}
                      </span>
                      <span className="font-bold text-slate-900">{event.event_type}</span>
                      <span className="text-slate-500 font-mono text-[11px]">
                        [{event.method || 'REQ'} {event.target_resource?.path || '/'}]
                      </span>
                    </div>
                    <div className="text-slate-500 font-mono text-[11px]">
                      {formatIsoDateSafe(event.timestamp, 19)} UTC
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs bg-slate-50 p-3 rounded-lg border border-slate-200 font-mono">
                    <div>
                      <span className="text-slate-500 block text-[11px] font-sans">Threat Origin:</span>
                      <span className="text-blue-600 font-bold">{event.ip_address}</span>
                      <span className="text-slate-400 ml-1 text-[11px]">({event.ip_source})</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[11px] font-sans">Actor Identity:</span>
                      {event.auth_context?.is_authenticated ? (
                        <span className="text-amber-700 font-semibold">
                          {event.auth_context.email} ({event.auth_context.role})
                        </span>
                      ) : (
                        <span className="text-red-600 font-semibold">Unauthenticated / Anonymous</span>
                      )}
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[11px] font-sans">Client Environment:</span>
                      <span className="text-slate-700">
                        {event.device_info?.browser || 'Browser'} on {event.device_info?.os || 'OS'} ({event.device_info?.client_type || 'HTTP'})
                      </span>
                      {event.device_info?.mac_address && (
                        <span className="text-slate-500 block text-[10px]">
                          MAC: {event.device_info.mac_address}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="text-xs text-slate-600 flex items-center gap-2 pt-0.5">
                    <span className="text-red-600 font-semibold">Violation:</span>
                    <span>{event.failure_reason}</span>
                    {event.case_id && (
                      <span className="ml-auto text-slate-400 font-mono text-[11px]">
                        Target Case: {event.case_id}
                      </span>
                    )}
                    {event.evidence_id && (
                      <span className="ml-2 text-slate-400 font-mono text-[11px]">
                        Evidence: {event.evidence_id}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SecurityAlertsPage;
