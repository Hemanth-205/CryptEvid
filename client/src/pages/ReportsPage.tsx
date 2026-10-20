import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import {
  FileDown,
  Download,
  Copy,
  CheckCircle2,
  RefreshCw,
  Plus,
  ShieldCheck,
  ExternalLink,
  Lock,
  FileText
} from 'lucide-react';
import { caseApi, reportApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { formatIsoDateSafe } from '../utils/date';
import type { Case } from '../types';

export const ReportsPage: React.FC = () => {
  const { user } = useAuth();
  const isReadOnly = user?.role === 'readonly';

  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [compiling, setCompiling] = useState<boolean>(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Compile Form State
  const [showModal, setShowModal] = useState<boolean>(false);
  const [reportTitle, setReportTitle] = useState<string>('Official Forensic Investigation Report');
  const [classification, setClassification] = useState<string>('CONFIDENTIAL // LAW ENFORCEMENT SENSITIVE');

  // Load Cases
  const loadCases = async () => {
    try {
      const res = await caseApi.getCases({ limit: 100 });
      const caseList = res.cases || [];
      setCases(caseList);
      if (caseList.length > 0 && !selectedCaseId) {
        setSelectedCaseId(caseList[0]._id);
      }
    } catch (err) {
      console.error('Failed to load cases', err);
    }
  };

  // Load Reports
  const loadReports = useCallback(async () => {
    setLoading(true);
    try {
      const res = await reportApi.getAllReports();
      setReports(res.reports || []);
    } catch (err) {
      console.error('Failed to load court reports', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCases();
    loadReports();
  }, [loadReports]);

  // Compile Report for Selected Case
  const handleCompileReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCaseId) {
      alert('Please select an active target case first.');
      return;
    }

    setCompiling(true);
    try {
      await reportApi.generateCaseReport(selectedCaseId, {
        title: reportTitle.trim(),
        classification
      });
      setShowModal(false);
      await loadReports();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Report compilation failed.');
    } finally {
      setCompiling(false);
    }
  };

  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const handleDownloadReport = async (reportId: string, caseNumber: string, version: number) => {
    setDownloadingId(reportId);
    try {
      const blobData = await reportApi.downloadReportBlob(reportId);
      const filename = `${caseNumber || 'Case'}_Forensic_Report_v${version || 1}.pdf`;
      const blob = new Blob([blobData], { type: 'application/pdf' });
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1000);
    } catch (err: any) {
      console.error('Download report failed:', err);
      alert(err.response?.data?.detail || err.message || 'Failed to download report.');
    } finally {
      setDownloadingId(null);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  return (
    <div className="space-y-4 animate-fade-in-up">
      {/* Page Header */}
      <div className="ws-panel p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white border border-slate-200 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 shrink-0">
            <FileDown className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight">
              Forensic Reports Registry
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Compile, export, and cryptographically seal judicial forensic examination dossiers.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadReports}
            className="ws-btn ws-btn-secondary !p-1.5 text-xs cursor-pointer"
            title="Reload Reports Registry"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-600 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {!isReadOnly && (
            <button
              onClick={() => setShowModal(true)}
              className="ws-btn ws-btn-primary text-xs flex items-center gap-1.5 py-1.5 px-3 cursor-pointer font-semibold"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Compile Judicial Report</span>
            </button>
          )}
        </div>
      </div>

      {/* Compliance & Standards Metric Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="ws-panel p-4 font-mono space-y-1 bg-white border border-slate-200 shadow-xs">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Certified Archive Volume</div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">{reports.length}</span>
            <span className="text-[11px] text-emerald-700 font-bold">SEALED DOSSIERS</span>
          </div>
          <p className="text-[11px] text-slate-500 font-sans">Directly admissible in legal proceedings</p>
        </div>

        <div className="ws-panel p-4 font-mono space-y-1 bg-white border border-slate-200 shadow-xs">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Digest Verification Standard</div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-blue-700">FIPS 180-4</span>
            <span className="text-[11px] text-slate-600 font-bold">SHA-256</span>
          </div>
          <p className="text-[11px] text-slate-500 font-sans">Cryptographic bit-stream verification</p>
        </div>

        <div className="ws-panel p-4 font-mono space-y-1 bg-white border border-slate-200 shadow-xs">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Custody Architecture</div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-amber-700">ISO/IEC 27037</span>
          </div>
          <p className="text-[11px] text-slate-500 font-sans">Digital evidence handling & preservation</p>
        </div>
      </div>

      {/* Master Registry Table */}
      <div className="ws-panel overflow-hidden bg-white border border-slate-200 shadow-xs">
        <div className="p-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span className="text-xs font-mono font-bold text-slate-900 uppercase tracking-wide">
              Master Registry of Certified Forensic Reports
            </span>
          </div>
          <span className="text-[11px] font-mono text-slate-500 font-bold">{reports.length} REGISTERED EXHIBITS</span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 font-mono text-xs space-y-2">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto text-emerald-600" />
            <p>Querying verified report registry...</p>
          </div>
        ) : reports.length === 0 ? (
          <div className="p-12 text-center space-y-3 font-mono text-xs">
            <FileText className="w-8 h-8 text-slate-300 mx-auto" />
            <div className="text-sm font-bold text-slate-800">No Sealed Reports Compiled</div>
            <p className="text-slate-500 max-w-sm mx-auto text-xs leading-relaxed">
              Select an active case dossier and click "Compile Judicial Report" to generate an official court-admissible PDF forensic summary.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="ws-table">
              <thead>
                <tr>
                  <th>Case Ref</th>
                  <th>Document Title</th>
                  <th>Revision</th>
                  <th>Classification</th>
                  <th>Examiner</th>
                  <th>Timestamp (UTC)</th>
                  <th>Cryptographic Digest (SHA-256)</th>
                  <th className="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => (
                  <tr key={report.report_id}>
                    <td className="whitespace-nowrap font-bold">
                      <Link
                        to={`/cases/${report.case_id}`}
                        className="text-blue-600 hover:text-blue-800 flex items-center gap-1 font-mono"
                      >
                        <span>{report.case_number}</span>
                        <ExternalLink className="w-3 h-3 text-slate-400" />
                      </Link>
                    </td>
                    <td className="font-semibold text-slate-900">
                      {report.title}
                    </td>
                    <td>
                      <span className="ws-badge ws-badge-green text-[10px]">
                        v{report.version}.0
                      </span>
                    </td>
                    <td>
                      <span className="ws-badge ws-badge-blue text-[10px]">
                        {report.classification}
                      </span>
                    </td>
                    <td className="text-slate-700">
                      {report.generated_by_name}
                    </td>
                    <td className="text-slate-500 whitespace-nowrap font-mono text-xs">
                      {report.generated_at ? `${formatIsoDateSafe(report.generated_at, 19)} UTC` : 'N/A'}
                    </td>
                    <td>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[11px] text-slate-700 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded font-mono truncate max-w-[150px]">
                          {report.sha256_hash}
                        </span>
                        <button
                          onClick={() => handleCopy(report.sha256_hash)}
                          className="p-1 hover:bg-slate-200 rounded text-slate-500 hover:text-slate-800 cursor-pointer"
                          title="Copy Full SHA-256 Seal"
                        >
                          {copiedHash === report.sha256_hash ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="text-right whitespace-nowrap">
                      <button
                        type="button"
                        disabled={downloadingId === report.report_id}
                        onClick={() => handleDownloadReport(report.report_id, report.case_number, report.version)}
                        className="ws-btn ws-btn-secondary text-xs py-1 px-2.5 inline-flex items-center gap-1.5 text-blue-700 border-blue-200 hover:bg-blue-50 font-semibold cursor-pointer disabled:opacity-50"
                        title="Download cryptographically sealed PDF dossier"
                      >
                        {downloadingId === report.report_id ? (
                          <RefreshCw className="w-3 h-3 animate-spin text-blue-600" />
                        ) : (
                          <Download className="w-3 h-3 text-blue-600" />
                        )}
                        <span>{downloadingId === report.report_id ? 'Downloading...' : 'Export PDF'}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Compile Report Modal */}
      {showModal && createPortal(
        <div 
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4 overflow-y-auto"
          onClick={() => setShowModal(false)}
        >
          <div 
            className="ws-panel max-w-lg w-full p-5 bg-white border border-slate-200 shadow-xl rounded-xl space-y-4 font-mono text-xs my-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="border-b border-slate-200 pb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileDown className="w-4 h-4 text-blue-600" />
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                  Compile Official Judicial Forensic Report
                </h3>
              </div>
              <Lock className="w-4 h-4 text-slate-400" />
            </div>

            <p className="text-slate-600 text-xs leading-relaxed font-sans">
              Compiles a sealed PDF document summarizing verified evidence exhibits, SHA-256 hashes, custody history, incident timeline, risk score, and technical recommendations.
            </p>

            <form onSubmit={handleCompileReport} className="space-y-3.5 font-sans">
              <div>
                <label className="block text-slate-700 font-bold text-xs mb-1">TARGET CASE DOSSIER</label>
                <select
                  required
                  value={selectedCaseId}
                  onChange={e => setSelectedCaseId(e.target.value)}
                  className="ws-select w-full bg-white border-slate-200 text-slate-800 text-xs"
                >
                  {cases.map(c => (
                    <option key={c._id} value={c._id}>
                      {c.case_number} - {c.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-700 font-bold text-xs mb-1">REPORT TITLE / DOCUMENT HEADER</label>
                <input
                  type="text"
                  required
                  value={reportTitle}
                  onChange={e => setReportTitle(e.target.value)}
                  placeholder="e.g. Official Forensic Examination Report"
                  className="ws-input w-full text-xs"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-bold text-xs mb-1">SECURITY CLASSIFICATION MARKING</label>
                <select
                  value={classification}
                  onChange={e => setClassification(e.target.value)}
                  className="ws-select w-full bg-white border-slate-200 text-slate-800 text-xs"
                >
                  <option value="CONFIDENTIAL // LAW ENFORCEMENT SENSITIVE">CONFIDENTIAL // LAW ENFORCEMENT SENSITIVE</option>
                  <option value="RESTRICTED - COURT EXHIBIT">RESTRICTED - COURT EXHIBIT</option>
                  <option value="OFFICIAL - FORENSIC RECORD">OFFICIAL - FORENSIC RECORD</option>
                  <option value="PUBLIC RECORD">PUBLIC RECORD</option>
                </select>
              </div>

              <div className="flex justify-end gap-2.5 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="ws-btn ws-btn-secondary px-3.5 py-1.5 text-xs cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={compiling || !selectedCaseId}
                  className="ws-btn ws-btn-primary px-3.5 py-1.5 text-xs flex items-center gap-1.5 disabled:opacity-50 cursor-pointer font-semibold"
                >
                  {compiling ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <FileDown className="w-3.5 h-3.5" />
                  )}
                  <span>{compiling ? 'Compiling PDF...' : 'Seal & Generate PDF'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};

export default ReportsPage;
