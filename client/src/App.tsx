import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';

import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import HorizontalNavbar from './components/HorizontalNavbar';
import ErrorBoundary from './components/ErrorBoundary';
import Cases from './pages/Cases';
import CaseDetail from './pages/CaseDetail';
import EvidenceGraphPage from './pages/EvidenceGraphPage';
import AIAnalysisPage from './pages/AIAnalysisPage';
import ChainOfCustodyPage from './pages/ChainOfCustodyPage';
import SecurityAlertsPage from './pages/SecurityAlertsPage';
import ReportsPage from './pages/ReportsPage';
import Settings from './pages/Settings';
import PortalManagerDashboard from './pages/PortalManagerDashboard';
import HardwareTelemetryCard from './components/HardwareTelemetryCard';

import { 
  FolderLock, 
  FileCheck, 
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Network,
  Radar,
  FileText,
  Activity,
  ArrowUpRight,
  History,
  Settings as SettingsIcon
} from 'lucide-react';

import api, { caseApi, evidenceApi, analyticsApi, securityApi } from './services/api';
import type { CaseStats, EvidenceStats, GlobalRiskStats } from './types';

// Command Center Dashboard
const DashboardView: React.FC = () => {
  const [stats, setStats] = useState<CaseStats | null>(null);
  const [evidenceStats, setEvidenceStats] = useState<EvidenceStats | null>(null);
  const [riskStats, setRiskStats] = useState<GlobalRiskStats | null>(null);
  const [securityStats, setSecurityStats] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [caseData, evData, riskData, secData] = await Promise.all([
        caseApi.getCaseStats(),
        evidenceApi.getEvidenceStats(),
        analyticsApi.getGlobalRiskStats().catch(() => null),
        securityApi.getStats().catch(() => null)
      ]);
      setStats(caseData);
      setEvidenceStats(evData);
      if (riskData) setRiskStats(riskData);
      if (secData) setSecurityStats(secData);
    } catch (err) {
      console.error('Failed to load dashboard statistics', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  return (
    <div className="space-y-6 relative z-10 animate-fade-in-up">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight font-sans">
              Forensic Command Center
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1 font-sans">
            Central operational overview for active cases and evidence vault.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadDashboardData}
            className="ws-btn ws-btn-secondary"
            title="Refresh statistics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Telemetry</span>
          </button>
          <Link to="/cases" className="ws-btn ws-btn-amber">
            <FolderLock className="w-3.5 h-3.5" />
            <span>Browse Case Files</span>
          </Link>
        </div>
      </div>

      {/* Primary Metric Grid with Clean Light Cards & Smooth Micro-lift */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="ws-panel ws-panel-interactive p-4.5 space-y-2 relative overflow-hidden group">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
            <span>Active Investigations</span>
            <div className="w-7 h-7 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shadow-xs transition-transform duration-200 group-hover:scale-110">
              <FolderLock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
            {stats?.active_cases ?? '--'}
          </div>
          <div className="text-[11px] text-slate-500 flex items-center gap-1.5 pt-1">
            <span>Total: <strong className="text-slate-800">{stats?.total_cases ?? 0}</strong></span>
            <span>•</span>
            <span className="text-red-600 font-medium">{stats?.critical_cases ?? 0} Critical</span>
          </div>
        </div>

        <div className="ws-panel ws-panel-interactive p-4.5 space-y-2 relative overflow-hidden group">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
            <span>Evidence Exhibits</span>
            <div className="w-7 h-7 rounded-lg bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600 shadow-xs transition-transform duration-200 group-hover:scale-110">
              <FileCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
            {evidenceStats?.total_evidence ?? '--'}
          </div>
          <div className="text-[11px] text-slate-500 flex items-center gap-1.5 pt-1">
            <span className="text-emerald-600 font-medium">{evidenceStats?.verified_evidence ?? 0} Verified</span>
            <span>•</span>
            <span className={evidenceStats?.tampered_evidence ? 'text-red-600 font-bold' : 'text-slate-500'}>
              {evidenceStats?.tampered_evidence ?? 0} Tampered
            </span>
          </div>
        </div>

        <div className="ws-panel ws-panel-interactive p-4.5 space-y-2 relative overflow-hidden group">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
            <span>Cryptographic Integrity</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shadow-xs transition-transform duration-200 group-hover:scale-110">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-emerald-600 font-mono tracking-tight">
            {evidenceStats?.integrity_rate !== undefined ? `${evidenceStats.integrity_rate}%` : '--'}
          </div>
          <div className="text-[11px] text-slate-500 pt-1">
            SHA-256 seal verified across vaults
          </div>
        </div>

        <div className="ws-panel ws-panel-interactive p-4.5 space-y-2 relative overflow-hidden group">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
            <span>Active Threat Alerts</span>
            <div className="w-7 h-7 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center text-red-600 shadow-xs transition-transform duration-200 group-hover:scale-110">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-red-600 font-mono tracking-tight">
            {securityStats?.open_alerts ?? (riskStats?.critical_risk_cases ?? 0)}
          </div>
          <div className="text-[11px] text-slate-500 flex items-center gap-1.5 pt-1">
            <span>{securityStats?.unauthorized_attempts_24h ?? 0} Unauthorized attempts (24h)</span>
          </div>
        </div>
      </div>

      {/* Hardware USB Ingestion & Biometric Telemetry */}
      <HardwareTelemetryCard />

      {/* Operational Workstation Launchpad */}
      <div className="ws-panel p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shadow-xs">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider font-mono">
                Forensic Workstation Modules
              </h2>
              <p className="text-xs text-slate-500">
                Direct access to investigation workflows, analytics engines, and evidence repositories.
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          <Link
            to="/cases"
            className="flex items-center justify-between p-3.5 rounded-xl bg-white border border-slate-200 hover:border-amber-400 hover:bg-amber-50/30 text-xs transition-all duration-200 hover:-translate-y-1 hover:shadow-md group shadow-xs"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shrink-0 group-hover:scale-105 transition-transform">
                <FolderLock className="w-4.5 h-4.5" />
              </div>
              <div>
                <div className="font-bold text-slate-800 group-hover:text-amber-700 transition-colors">Cases Register</div>
                <div className="text-[11px] text-slate-500">Active dossiers & case files</div>
              </div>
            </div>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-amber-600 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 shrink-0" />
          </Link>

          <Link
            to="/graph"
            className="flex items-center justify-between p-3.5 rounded-xl bg-white border border-slate-200 hover:border-cyan-400 hover:bg-cyan-50/30 text-xs transition-all duration-200 hover:-translate-y-1 hover:shadow-md group shadow-xs"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-600 shrink-0 group-hover:scale-105 transition-transform">
                <Network className="w-4.5 h-4.5" />
              </div>
              <div>
                <div className="font-bold text-slate-800 group-hover:text-cyan-700 transition-colors">Topological Graph</div>
                <div className="text-[11px] text-slate-500">Entity relation & correlation</div>
              </div>
            </div>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-cyan-600 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 shrink-0" />
          </Link>

          <Link
            to="/ai-analysis"
            className="flex items-center justify-between p-3.5 rounded-xl bg-white border border-slate-200 hover:border-purple-400 hover:bg-purple-50/30 text-xs transition-all duration-200 hover:-translate-y-1 hover:shadow-md group shadow-xs"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-600 shrink-0 group-hover:scale-105 transition-transform">
                <Radar className="w-4.5 h-4.5" />
              </div>
              <div>
                <div className="font-bold text-slate-800 group-hover:text-purple-700 transition-colors">Threat Intel</div>
                <div className="text-[11px] text-slate-500">Risk scoring & hypotheses</div>
              </div>
            </div>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-purple-600 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 shrink-0" />
          </Link>

          <Link
            to="/security-alerts"
            className="flex items-center justify-between p-3.5 rounded-lg bg-white border border-slate-200 hover:border-red-400 hover:bg-slate-50 text-xs transition-all group shadow-xs"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center text-red-600 shrink-0">
                <AlertTriangle className="w-4.5 h-4.5" />
              </div>
              <div>
                <div className="font-bold text-slate-800 group-hover:text-red-700 transition-colors">Security Alerts</div>
                <div className="text-[11px] text-slate-500">Intrusion & access telemetry</div>
              </div>
            </div>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-red-600 transition-colors shrink-0" />
          </Link>

          <Link
            to="/custody"
            className="flex items-center justify-between p-3.5 rounded-lg bg-white border border-slate-200 hover:border-amber-400 hover:bg-slate-50 text-xs transition-all group shadow-xs"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shrink-0">
                <History className="w-4.5 h-4.5" />
              </div>
              <div>
                <div className="font-bold text-slate-800 group-hover:text-amber-700 transition-colors">Chain of Custody</div>
                <div className="text-[11px] text-slate-500">Handoff ledger & audit logs</div>
              </div>
            </div>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-amber-600 transition-colors shrink-0" />
          </Link>

          <Link
            to="/cases"
            className="flex items-center justify-between p-3.5 rounded-lg bg-white border border-slate-200 hover:border-amber-400 hover:bg-slate-50 text-xs transition-all group shadow-xs"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shrink-0">
                <FileText className="w-4.5 h-4.5" />
              </div>
              <div>
                <div className="font-bold text-slate-800 group-hover:text-amber-700 transition-colors">Case Reports</div>
                <div className="text-[11px] text-slate-500">Export sealed PDF inside cases</div>
              </div>
            </div>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-amber-600 transition-colors shrink-0" />
          </Link>

          <Link
            to="/settings"
            className="flex items-center justify-between p-3.5 rounded-lg bg-white border border-slate-200 hover:border-slate-400 hover:bg-slate-50 text-xs transition-all group shadow-xs"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 shrink-0">
                <SettingsIcon className="w-4.5 h-4.5" />
              </div>
              <div>
                <div className="font-bold text-slate-800 group-hover:text-slate-900 transition-colors">Workstation Settings</div>
                <div className="text-[11px] text-slate-500">Security & audit preferences</div>
              </div>
            </div>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-slate-800 transition-colors shrink-0" />
          </Link>
        </div>
      </div>
    </div>
  );
};

// Hardware Ingestion Terminals View
const DevicesView: React.FC = () => {
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const res = await api.get('/hardware/devices');
        const list = Array.isArray(res.data) ? res.data : (res.data?.devices || []);
        setDevices(list);
      } catch (err) {
        console.error('Failed to load devices', err);
      } finally {
        setLoading(false);
      }
    };
    fetchDevices();
  }, []);

  return (
    <div className="space-y-6 relative z-10">
      <div className="flex items-center justify-between border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 font-sans tracking-tight">Hardware Ingestion Terminals</h1>
          <p className="text-xs text-slate-500 mt-1">
            Physical ESP32 ingestion nodes, biometric readers, and forensic extraction workstations.
          </p>
        </div>
      </div>

      <HardwareTelemetryCard />

      <div className="ws-panel overflow-hidden">
        <div className="table-responsive">
          <table className="ws-table min-w-[640px]">
            <thead>
              <tr>
                <th>Device ID</th>
                <th>Terminal Label</th>
                <th>Status</th>
                <th>MAC Address</th>
                <th>Firmware</th>
                <th>Registered At</th>
                <th>Last Heartbeat</th>
              </tr>
            </thead>
            <tbody>
              {devices.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-10 text-slate-500 font-mono">
                    {loading ? 'Querying hardware nodes...' : 'No hardware terminals registered.'}
                  </td>
                </tr>
              ) : (
                devices.map(d => (
                  <tr key={d._id || d.device_id}>
                    <td className="font-mono text-xs font-bold text-blue-600">{d.device_id}</td>
                    <td className="font-semibold text-slate-800">{d.name}</td>
                    <td>
                      <span className={`ws-badge ${d.status === 'online' ? 'ws-badge-green' : 'ws-badge-red'}`}>
                        {d.status?.toUpperCase()}
                      </span>
                    </td>
                    <td className="font-mono text-xs text-slate-500">{d.mac_address}</td>
                    <td className="font-mono text-xs text-slate-500">{d.firmware_version}</td>
                    <td className="text-xs text-slate-500">{d.registered_at ? new Date(d.registered_at).toLocaleString() : '--'}</td>
                    <td className="text-xs text-slate-500">{d.last_seen ? new Date(d.last_seen).toLocaleString() : '--'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// Professional Main Dashboard Shell Layout with Horizontal Top Navigation
const DashboardLayout = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  return (
    <div className="min-h-screen flex flex-col font-sans relative bg-slate-50 text-slate-900">
      {/* Modern Horizontal Navigation Bar */}
      <HorizontalNavbar />

      {/* Main Content Area - Full width with max bound */}
      <main className="flex-1 w-full max-w-[1920px] mx-auto p-4 sm:p-6 lg:p-8 relative z-10">
        <ErrorBoundary fallbackTitle="Forensic Module Error">
          <Routes>
            {/* Root and Dashboard: Admin lands on Portal Users, caseworkers & Chief Investigator land on Command Center */}
            <Route path="/" element={<Navigate to={isAdmin ? "/portal-manager" : "/dashboard"} replace />} />
            <Route path="/dashboard" element={isAdmin ? <Navigate to="/portal-manager" replace /> : <DashboardView />} />

            {/* Portal Users page: ONLY displayed for Admin. Non-admins are redirected */}
            <Route path="/portal-manager" element={isAdmin ? <PortalManagerDashboard /> : <Navigate to="/dashboard" replace />} />

            {/* In Admin login: ONLY Portal Users and Settings are visible/accessible */}
            <Route path="/cases" element={isAdmin ? <Navigate to="/portal-manager" replace /> : <Cases />} />
            <Route path="/cases/:caseId" element={isAdmin ? <Navigate to="/portal-manager" replace /> : <CaseDetail />} />
            <Route path="/evidence" element={<Navigate to={isAdmin ? "/portal-manager" : "/cases"} replace />} />
            <Route path="/graph" element={isAdmin ? <Navigate to="/portal-manager" replace /> : <EvidenceGraphPage />} />
            <Route path="/ai-analysis" element={isAdmin ? <Navigate to="/portal-manager" replace /> : <AIAnalysisPage />} />
            <Route path="/ai-analysis/:caseId" element={isAdmin ? <Navigate to="/portal-manager" replace /> : <AIAnalysisPage />} />
            <Route path="/security-alerts" element={isAdmin ? <Navigate to="/portal-manager" replace /> : <SecurityAlertsPage />} />
            <Route path="/reports" element={isAdmin ? <Navigate to="/portal-manager" replace /> : <ReportsPage />} />
            <Route path="/custody" element={isAdmin ? <Navigate to="/portal-manager" replace /> : <ChainOfCustodyPage />} />
            <Route path="/logs" element={<Navigate to={isAdmin ? "/portal-manager" : "/custody"} replace />} />
            <Route path="/devices" element={isAdmin ? <Navigate to="/portal-manager" replace /> : <DevicesView />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to={isAdmin ? "/portal-manager" : "/dashboard"} replace />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  );
};

const AppRoutes = () => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const isAdmin = user?.role === 'admin';

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center font-mono text-xs text-slate-600 gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
        <span className="tracking-wider">INITIALIZING FORENSIC WORKSTATION...</span>
      </div>
    );
  }

  return (
    <ErrorBoundary fallbackTitle="Application Shell Error">
      <Routes>
        {/* Root Route: If authenticated, redirect to /portal-manager for admin; otherwise show /dashboard */}
        <Route
          path="/"
          element={isAuthenticated ? <Navigate to={isAdmin ? "/portal-manager" : "/dashboard"} replace /> : <LandingPage />}
        />

        {/* Dedicated Login / Register Portal Route */}
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to={isAdmin ? "/portal-manager" : "/dashboard"} replace /> : <Login />}
        />

        {/* Dedicated Hardware Authentication Portal Route */}
        <Route
          path="/hardware-auth"
          element={isAuthenticated ? <Navigate to={isAdmin ? "/portal-manager" : "/dashboard"} replace /> : <Login />}
        />

        {/* Landing Route alias: always viewable */}
        <Route
          path="/landing"
          element={<LandingPage />}
        />

        {/* Authenticated Workstation Shell */}
        {isAuthenticated ? (
          <Route path="/*" element={<DashboardLayout />} />
        ) : (
          <Route path="/*" element={<Navigate to="/" replace />} />
        )}
      </Routes>
    </ErrorBoundary>
  );
};

export const App = () => {
  return (
    <Router>
      <ThemeProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </ThemeProvider>
    </Router>
  );
};

export default App;
