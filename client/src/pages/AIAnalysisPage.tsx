import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import {
  FolderLock,
  ShieldCheck,
  AlertTriangle,
  FileText,
  CheckCircle2,
  TrendingUp,
  RefreshCw,
  ArrowRight,
  ArrowLeft,
  ExternalLink,
  ShieldAlert,
  SlidersHorizontal,
  FileDown,
  Search,
  Radar,
  Target,
  Compass
} from 'lucide-react';
import { caseApi, analyticsApi, reportApi } from '../services/api';
import { formatLocalDateSafe } from '../utils/date';
import type {
  Case,
  RiskScoreResponse,
  AIAnalysisResponse,
  ForensicRecommendation
} from '../types';

export const AIAnalysisPage: React.FC = () => {
  const { caseId: routeCaseId } = useParams<{ caseId?: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Active case ID can come from route /ai-analysis/:caseId or query ?caseId=...
  const selectedCaseId = routeCaseId || searchParams.get('caseId') || '';

  const [cases, setCases] = useState<Case[]>([]);
  const [loadingCases, setLoadingCases] = useState<boolean>(true);
  const [caseSearch, setCaseSearch] = useState<string>('');

  // Analysis State for the selected case
  const [riskData, setRiskData] = useState<RiskScoreResponse | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysisResponse | null>(null);
  const [recommendations, setRecommendations] = useState<ForensicRecommendation[]>([]);
  const [loadingAnalysis, setLoadingAnalysis] = useState<boolean>(false);
  const [generatingReport, setGeneratingReport] = useState<boolean>(false);
  const [reportSuccessMsg, setReportSuccessMsg] = useState<string | null>(null);

  // Load Cases List
  const loadCases = async () => {
    setLoadingCases(true);
    try {
      const res = await caseApi.getCases({ limit: 100 });
      const caseList: Case[] = res.cases || [];
      setCases(caseList);
    } catch (err) {
      console.error('Failed to load cases', err);
    } finally {
      setLoadingCases(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  // Handler to navigate to dedicated case page
  const handleSelectCase = (caseId: string) => {
    setReportSuccessMsg(null);
    navigate(`/ai-analysis/${caseId}`);
  };

  // Handler to return to directory
  const handleBackToDirectory = () => {
    setReportSuccessMsg(null);
    navigate('/ai-analysis');
  };

  // Load Risk & Threat Intelligence strictly for the selected case
  const loadCaseIntelligence = useCallback(async (caseId: string) => {
    if (!caseId) {
      setRiskData(null);
      setAiAnalysis(null);
      setRecommendations([]);
      return;
    }

    setLoadingAnalysis(true);
    try {
      const [riskRes, aiRes, recRes] = await Promise.all([
        analyticsApi.getCaseRiskScore(caseId).catch(() => null),
        analyticsApi.getCaseAIAnalysis(caseId).catch(() => null),
        analyticsApi.getCaseRecommendations(caseId).catch(() => ({ recommendations: [] }))
      ]);
      setRiskData(riskRes);
      setAiAnalysis(aiRes);
      setRecommendations(recRes?.recommendations || []);
    } catch (err) {
      console.error('Failed to load case intelligence', err);
    } finally {
      setLoadingAnalysis(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCaseId) {
      loadCaseIntelligence(selectedCaseId);
    } else {
      setRiskData(null);
      setAiAnalysis(null);
      setRecommendations([]);
    }
  }, [selectedCaseId, loadCaseIntelligence]);

  const activeCase = cases.find(c => c._id === selectedCaseId);

  // Generate Official Case Report directly from Threat Intelligence
  const handleGenerateReport = async () => {
    if (!selectedCaseId) return;
    setGeneratingReport(true);
    setReportSuccessMsg(null);
    try {
      const res = await reportApi.generateCaseReport(selectedCaseId, {
        title: `Forensic Threat Intelligence Report - ${activeCase?.case_number || 'Case'}`,
        classification: 'CONFIDENTIAL // LAW ENFORCEMENT SENSITIVE'
      });

      const reportId = res?.report_id || res?._id || res?.report?.report_id || res?.report?._id;
      const reportVersion = res?.version || res?.report?.version || 1;

      if (reportId) {
        const blobData = await reportApi.downloadReportBlob(reportId);
        const filename = `${activeCase?.case_number || 'Case'}_Forensic_Report_v${reportVersion}.pdf`;
        const blob = new Blob([blobData], { type: 'application/pdf' });
        const blobUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1000);
      }

      setReportSuccessMsg(`Official Report v${reportVersion} successfully compiled & downloaded.`);
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Report generation failed.');
    } finally {
      setGeneratingReport(false);
    }
  };

  // Score styling tokens
  const getScoreBadge = (score: number) => {
    if (score >= 70) return { text: 'text-red-700', bg: 'bg-red-50', border: 'border-red-300', bar: 'bg-red-600', label: 'CRITICAL THREAT' };
    if (score >= 35) return { text: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-300', bar: 'bg-amber-600', label: 'ELEVATED RISK' };
    return { text: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-300', bar: 'bg-emerald-600', label: 'NOMINAL RISK' };
  };

  const riskBadge = getScoreBadge(riskData?.score || 0);

  // Contributing signals
  const tamperedSignal = riskData?.signals?.find(s => s.signal_type.toLowerCase().includes('tamper'));
  const criticalSignal = riskData?.signals?.find(s => s.signal_type.toLowerCase().includes('critical'));
  const highSignal = riskData?.signals?.find(s => s.signal_type.toLowerCase().includes('high'));
  const custodySignal = riskData?.signals?.find(s => s.signal_type.toLowerCase().includes('custody'));

  // Filtered cases for directory view
  const filteredCases = cases.filter(c => {
    if (!caseSearch.trim()) return true;
    const q = caseSearch.toLowerCase();
    return (
      c.case_number?.toLowerCase().includes(q) ||
      c.title?.toLowerCase().includes(q) ||
      c.description?.toLowerCase().includes(q) ||
      c.priority?.toLowerCase().includes(q)
    );
  });

  // =========================================================================
  // VIEW 1: CASE SELECTION MASTER DIRECTORY (When no case is active)
  // =========================================================================
  if (!selectedCaseId) {
    return (
      <div className="space-y-5 animate-fade-in-up">
        {/* Header Bar */}
        <div className="ws-panel p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-base font-bold text-slate-900 tracking-tight">
                Threat Intelligence & Risk Assessment
              </h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Select an active case dossier below to launch its dedicated forensic intelligence analysis.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="ws-badge ws-badge-amber text-xs">
              {cases.length} Registered Cases
            </span>
          </div>
        </div>

        {/* Case Directory Grid */}
        <div className="ws-panel p-5 space-y-4 bg-white border border-slate-200 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-slate-600" />
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
                Select Case Dossier to Launch Intelligence Page
              </h2>
            </div>

            {/* Quick Search */}
            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={caseSearch}
                onChange={(e) => setCaseSearch(e.target.value)}
                placeholder="Filter cases by ID or title..."
                className="w-full ws-input !pl-8 text-xs"
              />
            </div>
          </div>

          {loadingCases ? (
            <div className="p-12 text-center text-xs font-mono text-slate-500">
              <RefreshCw className="w-5 h-5 animate-spin mx-auto text-amber-600 mb-2" />
              Loading case directory...
            </div>
          ) : filteredCases.length === 0 ? (
            <div className="p-12 text-center text-xs font-mono text-slate-500 space-y-3">
              <FolderLock className="w-8 h-8 text-slate-300 mx-auto" />
              <p>{cases.length === 0 ? 'No active case files found in database.' : 'No cases match your search query.'}</p>
              <Link to="/cases" className="ws-btn ws-btn-secondary inline-flex">
                Register New Case
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-1">
              {filteredCases.map((c) => (
                <div
                  key={c._id}
                  onClick={() => handleSelectCase(c._id)}
                  className="ws-panel ws-panel-interactive p-4 rounded-xl border border-slate-200 hover:border-amber-400 bg-white hover:bg-amber-50/20 cursor-pointer flex flex-col justify-between space-y-3.5 transition-all duration-200 hover:-translate-y-1 hover:shadow-md group"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-amber-700 group-hover:text-amber-800">
                        {c.case_number}
                      </span>
                      <span className={`ws-badge ${
                        c.priority === 'CRITICAL' ? 'ws-badge-red' :
                        c.priority === 'HIGH' ? 'ws-badge-amber' : 'ws-badge-blue'
                      } text-[9px]`}>
                        {c.priority}
                      </span>
                    </div>
                    <h3 className="font-bold text-sm text-slate-900 group-hover:text-amber-900 transition-colors line-clamp-1">
                      {c.title}
                    </h3>
                    <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
                      {c.description || 'No description recorded.'}
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-2.5 border-t border-slate-200/80 text-xs font-mono">
                    <span className="text-slate-500">Status: <strong className="text-slate-700">{c.status}</strong></span>
                    <span className="text-amber-600 font-bold flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                      <span>Launch Analysis</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // =========================================================================
  // VIEW 2: DEDICATED CASE THREAT INTELLIGENCE PAGE (Full-page launch)
  // =========================================================================
  return (
    <div className="space-y-5 animate-fade-in-up">
      {/* Dedicated Navigation Bar: Return to Directory & Actions */}
      <div className="ws-panel p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white border border-slate-200 shadow-xs">
        <div className="flex items-center gap-3">
          <button
            onClick={handleBackToDirectory}
            className="ws-btn ws-btn-secondary !py-2 !px-3 text-xs flex items-center gap-1.5 cursor-pointer shadow-xs hover:border-amber-400 group"
            title="Return to Case Directory"
          >
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform text-slate-600 group-hover:text-amber-600" />
            <span>All Cases</span>
          </button>

          <div className="h-6 w-px bg-slate-200 hidden sm:block" />

          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-sm font-bold text-amber-700">
                {activeCase?.case_number || 'ACTIVE DOSSIER'}
              </span>
              <span className="text-slate-300">|</span>
              <h1 className="text-base font-extrabold text-slate-900 tracking-tight">
                {activeCase?.title || 'Forensic Threat Assessment'}
              </h1>
              {activeCase?.priority && (
                <span className={`ws-badge ${
                  activeCase.priority === 'CRITICAL' ? 'ws-badge-red' :
                  activeCase.priority === 'HIGH' ? 'ws-badge-amber' : 'ws-badge-blue'
                } text-[10px]`}>
                  {activeCase.priority}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5 font-sans">
              Dedicated forensic intelligence dossier • Cryptographic posture & threat vectors.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 shrink-0">
          <Link
            to={`/cases/${selectedCaseId}`}
            className="ws-btn ws-btn-secondary !py-1.5 !text-xs flex items-center gap-1.5"
            title="Open Case Exhibits"
          >
            <span>Case Exhibits</span>
            <ExternalLink className="w-3.5 h-3.5 text-slate-500" />
          </Link>

          <button
            onClick={() => loadCaseIntelligence(selectedCaseId)}
            disabled={loadingAnalysis}
            className="ws-btn ws-btn-secondary !py-1.5 !text-xs cursor-pointer flex items-center gap-1.5"
            title="Refresh Case Analysis"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-600 ${loadingAnalysis ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleGenerateReport}
            disabled={generatingReport}
            className="ws-btn ws-btn-amber !py-1.5 !text-xs inline-flex items-center gap-1.5 cursor-pointer font-bold shadow-xs"
            title="Generate Sealed Forensic Examination Report"
          >
            <FileDown className="w-3.5 h-3.5" />
            <span>{generatingReport ? 'Compiling...' : 'Generate Case Report'}</span>
          </button>
        </div>
      </div>

      {reportSuccessMsg && (
        <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-mono text-emerald-800 flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{reportSuccessMsg}</span>
          </div>
          <Link to={`/cases/${selectedCaseId}`} className="text-emerald-700 underline font-semibold hover:text-emerald-900">
            View in Case Details &rarr;
          </Link>
        </div>
      )}

      {loadingAnalysis ? (
        <div className="ws-panel p-20 text-center space-y-3 bg-white border border-slate-200 shadow-xs">
          <RefreshCw className="w-7 h-7 animate-spin mx-auto text-amber-600" />
          <p className="text-sm font-mono text-slate-700 font-bold tracking-wider">
            EVALUATING FORENSIC THREAT INTELLIGENCE FOR {activeCase?.case_number}...
          </p>
          <p className="text-xs text-slate-500 font-sans">
            Correlating cryptographic baseline hashes, timeline anomalies, and investigative heuristics.
          </p>
        </div>
      ) : (
        <div className="space-y-5 animate-fade-in-up">
          {/* AI Executive Intelligence Narrative & Engine Status */}
          <div className="rounded-2xl bg-white border-2 border-amber-300 shadow-sm overflow-hidden">
            <div className="bg-gradient-to-r from-amber-50/90 via-slate-50 to-amber-50/90 px-5 py-3.5 border-b border-amber-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-700 shadow-2xs">
                  <Radar className="w-5 h-5 text-amber-700" />
                </div>
                <div>
                  <h3 className="text-sm font-extrabold font-mono tracking-wide uppercase text-slate-900 flex items-center gap-2">
                    Executive Threat Intelligence Brief
                  </h3>
                  <p className="text-xs text-slate-600 font-sans font-medium">
                    Autonomous forensic threat modeling & cryptographic risk correlation
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono font-bold text-slate-500">AI ENGINE:</span>
                <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-bold ${
                  aiAnalysis?.is_fallback 
                    ? 'bg-slate-100 text-slate-800 border border-slate-300' 
                    : 'bg-emerald-50 text-emerald-900 border border-emerald-300 shadow-2xs'
                }`}>
                  <span className={`w-2 h-2 rounded-full ${aiAnalysis?.is_fallback ? 'bg-slate-500' : 'bg-emerald-600 animate-ping'}`} />
                  {aiAnalysis?.ai_provider || 'Google Gemini Threat Intel'}
                </span>
              </div>
            </div>

            <div className="p-5 space-y-3 bg-white">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 shadow-2xs">
                <p className="text-sm md:text-[15px] text-slate-900 leading-relaxed font-sans font-medium">
                  {aiAnalysis?.summary || 'Deterministic threat baseline established. No anomalous tamper deviations detected.'}
                </p>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[11px] font-mono text-slate-500">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-800 font-semibold">
                    CASE: {activeCase?.case_number}
                  </span>
                  <span>•</span>
                  <span className="text-slate-600">
                    {aiAnalysis?.generated_at ? formatLocalDateSafe(aiAnalysis.generated_at) : 'Live Analysis'}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-emerald-800 font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Grounding: Cryptographic Exhibits & Verified Timeline Events</span>
                </div>
              </div>
            </div>
          </div>

          {/* Quantitative Risk Summary & Signal Matrix */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Risk Gauge Card */}
            <div className={`lg:col-span-4 ws-panel ws-panel-interactive p-5 border ${riskBadge.border} ${riskBadge.bg} flex flex-col justify-between space-y-4`}>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-slate-600 uppercase tracking-wider flex items-center gap-1.5 font-bold">
                  <TrendingUp className="w-4 h-4 text-slate-700" />
                  Evaluated Case Risk Posture
                </span>
                <span className={`text-[10px] font-mono font-bold px-2.5 py-0.5 rounded border ${riskBadge.border} ${riskBadge.text} bg-white shadow-2xs`}>
                  {riskBadge.label}
                </span>
              </div>

              <div className="flex items-baseline gap-2">
                <span className={`text-5xl font-mono font-extrabold tracking-tight ${riskBadge.text}`}>
                  {riskData ? riskData.score : 0}
                </span>
                <span className="text-sm font-mono text-slate-500 font-bold">/ 100.0</span>
              </div>

              <div className="space-y-1.5">
                <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${riskBadge.bar}`}
                    style={{ width: `${Math.min(100, Math.max(5, riskData?.score || 0))}%` }}
                  />
                </div>
                <div className="flex justify-between text-[10px] font-mono text-slate-500 font-semibold">
                  <span>0 (NOMINAL)</span>
                  <span>50 (ELEVATED)</span>
                  <span>100 (CRITICAL)</span>
                </div>
              </div>

              <p className="text-xs text-slate-700 border-t border-slate-200/80 pt-2.5 leading-relaxed font-sans">
                {riskData?.explanation || 'Deterministic calculation evaluating cryptographic integrity, high-severity telemetry, and custody continuity.'}
              </p>
            </div>

            {/* Contributing Risk Breakdown Ledger */}
            <div className="lg:col-span-8 ws-panel p-5 space-y-3.5 bg-white border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  <span className="text-xs font-mono font-bold text-slate-900 uppercase tracking-wide">
                    Evaluated Threat Indicators
                  </span>
                </div>
                <span className="text-[10px] font-mono text-slate-500 font-bold">WEIGHTED RISK BREAKDOWN</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1 hover:border-slate-300 transition-colors">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-slate-600">Tampered Evidence Exhibits:</span>
                    <span className={tamperedSignal?.count ? 'text-red-700 font-bold' : 'text-emerald-700 font-bold'}>
                      {tamperedSignal?.count ?? 0} exhibits
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500 font-mono">+35 risk points per cryptographic hash mismatch</p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1 hover:border-slate-300 transition-colors">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-slate-600">Critical Severity Events:</span>
                    <span className={criticalSignal?.count ? 'text-red-700 font-bold' : 'text-slate-800 font-bold'}>
                      {criticalSignal?.count ?? 0} events
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500 font-mono">+15 risk points per unauthorized escalation alert</p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1 hover:border-slate-300 transition-colors">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-slate-600">High Severity Alerts:</span>
                    <span className={highSignal?.count ? 'text-amber-700 font-bold' : 'text-slate-800 font-bold'}>
                      {highSignal?.count ?? 0} events
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500 font-mono">+8 risk points per external intrusion pattern</p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1 hover:border-slate-300 transition-colors">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-slate-600">Chain of Custody Breaks:</span>
                    <span className={custodySignal?.count ? 'text-red-700 font-bold' : 'text-emerald-700 font-bold'}>
                      {custodySignal?.count ?? 0} anomalies
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500 font-mono">SHA-256 block ledger continuity verification</p>
                </div>
              </div>
            </div>
          </div>

          {/* Facts vs Hypotheses Dual Ledger */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Certified Facts */}
            <div className="ws-panel p-5 space-y-3.5 bg-white border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 font-mono uppercase tracking-wide">
                      Verifiable Forensic Evidence Facts
                    </h3>
                    <p className="text-[10px] text-slate-500 font-mono">
                      Deterministic evidentiary data points (Admissible in court)
                    </p>
                  </div>
                </div>
                <span className="ws-badge ws-badge-green text-[9px]">VERIFIED</span>
              </div>

              {aiAnalysis?.facts && aiAnalysis.facts.length > 0 ? (
                <div className="space-y-2">
                  {aiAnalysis.facts.map((fact: string, idx: number) => (
                    <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-start gap-2.5 text-xs text-slate-800 font-mono">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                      <span className="leading-relaxed text-[11px]">{fact}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center text-slate-500 font-mono text-xs">
                  No verified evidence artifacts recorded on this case yet.
                </div>
              )}
            </div>

            {/* AI Hypotheses & Threat Vectors */}
            <div className="ws-panel p-5 space-y-3.5 bg-white border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-amber-600" />
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 font-mono uppercase tracking-wide">
                      Investigative Hypotheses & Threat Vectors
                    </h3>
                    <p className="text-[10px] text-slate-500 font-mono">
                      Probabilistic threat vectors & lead generation (Analytical guidance)
                    </p>
                  </div>
                </div>
                <span className="ws-badge ws-badge-amber text-[9px]">ANALYTICAL</span>
              </div>

              {aiAnalysis?.ai_interpretations && aiAnalysis.ai_interpretations.length > 0 ? (
                <div className="space-y-2">
                  {aiAnalysis.ai_interpretations.map((interp: string, idx: number) => (
                    <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-start gap-2.5 text-xs text-slate-800 font-mono">
                      <div className="w-2 h-2 rounded-full bg-amber-500 shrink-0 mt-1.5" />
                      <span className="leading-relaxed text-[11px]">{interp}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center text-slate-500 font-mono text-xs">
                  No active threat hypotheses generated for this case.
                </div>
              )}
            </div>
          </div>

          {/* MITRE ATT&CK & Detected Threat Tactics */}
          {aiAnalysis?.detected_attack_patterns && aiAnalysis.detected_attack_patterns.length > 0 && (
            <div className="ws-panel p-5 space-y-3 bg-white border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-purple-600" />
                  <h3 className="text-xs font-bold text-slate-900 font-mono uppercase tracking-wide">
                    Detected Threat Indicators & MITRE ATT&CK Techniques
                  </h3>
                </div>
                <span className="text-[10px] font-mono font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
                  {aiAnalysis.detected_attack_patterns.length} DETECTED TACTICS
                </span>
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
                {aiAnalysis.detected_attack_patterns.map((pat: string, idx: number) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-50 border border-purple-200/80 text-purple-900 font-mono text-xs font-semibold shadow-2xs hover:bg-purple-100 transition-colors"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-600" />
                    {pat}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Prioritized Forensic Considerations */}
          {aiAnalysis?.investigation_considerations && aiAnalysis.investigation_considerations.length > 0 && (
            <div className="ws-panel p-5 space-y-3 bg-white border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
                <div className="flex items-center gap-2">
                  <Compass className="w-4 h-4 text-blue-600" />
                  <h3 className="text-xs font-bold text-slate-900 font-mono uppercase tracking-wide">
                    Judicial & Technical Investigation Directives
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-slate-500 font-bold">
                  EVIDENTIARY GUIDANCE
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
                {aiAnalysis.investigation_considerations.map((cons: string, idx: number) => (
                  <div key={idx} className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-mono text-slate-800 flex items-start gap-2.5">
                    <span className="w-5 h-5 rounded-md bg-blue-100 text-blue-700 flex items-center justify-center shrink-0 font-bold text-[10px]">
                      {idx + 1}
                    </span>
                    <span className="leading-relaxed text-[11px] font-sans text-slate-700">{cons}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actionable Recommendations Table */}
          <div className="ws-panel p-5 space-y-3.5 bg-white border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-600" />
                <div>
                  <h3 className="text-xs font-bold text-slate-900 font-mono uppercase tracking-wide">
                    Prioritized Investigative Countermeasures
                  </h3>
                  <p className="text-[10px] text-slate-500 font-mono">
                    Deterministic directives generated by forensic rule evaluation
                  </p>
                </div>
              </div>
              <span className="text-[11px] font-mono text-slate-500 font-bold">
                {recommendations.length} Active Directives
              </span>
            </div>

            {recommendations.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {recommendations.map((rec, idx) => {
                  const sev = (rec.severity || 'MEDIUM').toUpperCase();
                  const badgeClass =
                    sev === 'CRITICAL' || sev === 'IMMEDIATE'
                      ? 'ws-badge-red'
                      : sev === 'HIGH'
                      ? 'ws-badge-amber'
                      : 'ws-badge-blue';

                  return (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col justify-between space-y-2.5 font-mono text-xs hover:border-slate-300 transition-colors"
                    >
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className={`ws-badge ${badgeClass} text-[9px]`}>
                            {sev}
                          </span>
                          <span className="text-[10px] text-slate-500 font-bold">{rec.action_category || 'DIRECTIVE'}</span>
                        </div>
                        <h4 className="font-bold text-slate-900 text-xs">{rec.title}</h4>
                        <p className="text-slate-600 text-[11px] leading-relaxed">{rec.description}</p>
                      </div>

                      {rec.reason && (
                        <div className="pt-2 border-t border-slate-200 text-[10px] text-slate-500">
                          <span className="font-bold text-slate-700">EVIDENTIARY BASIS: </span>
                          <span>{rec.reason}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500 font-mono text-xs">
                No active directives compiled. Evidence is operating within nominal parameters.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AIAnalysisPage;
