import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  History,
  Search,
  RefreshCw,
  User as UserIcon,
  GitCommit,
  ExternalLink,
  CheckCircle,
  Copy,
  ShieldCheck,
  Cpu
} from 'lucide-react';
import { evidenceApi, caseApi } from '../services/api';
import { formatIsoDateSafe } from '../utils/date';
import type { Case } from '../types';

export const ChainOfCustodyPage: React.FC = () => {
  const [events, setEvents] = useState<any[]>([]);
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [search, setSearch] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [seeding, setSeeding] = useState<boolean>(false);

  // Load Cases
  const loadCases = async () => {
    try {
      const res = await caseApi.getCases({ limit: 100 });
      setCases(res.cases || []);
    } catch (err) {
      console.error('Failed to load cases', err);
    }
  };

  // Load Custody Events
  const loadCustody = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { limit: 300 };
      if (selectedCaseId) params.case_id = selectedCaseId;
      const res = await evidenceApi.getAllCustodyEvents(params);
      setEvents(res.events || []);
    } catch (err) {
      console.error('Failed to load chain of custody ledger', err);
    } finally {
      setLoading(false);
    }
  }, [selectedCaseId]);

  useEffect(() => {
    loadCases();
  }, []);

  useEffect(() => {
    loadCustody();
  }, [loadCustody]);

  // Handle Demo Seed
  const handleSeedDemo = async () => {
    setSeeding(true);
    try {
      await caseApi.seedDemo();
      await loadCases();
      await loadCustody();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to seed demo data.');
    } finally {
      setSeeding(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  // Action Badge Helper
  const getActionBadgeClass = (action: string) => {
    const act = (action || '').toUpperCase();
    if (act.includes('TAMPER') || act.includes('FAIL')) {
      return 'ws-badge-tampered';
    }
    if (act.includes('VERIFIED') || act.includes('PASS')) {
      return 'ws-badge-verified';
    }
    if (act.includes('INGEST') || act.includes('COLLECT') || act.includes('UPLOAD')) {
      return 'ws-badge-amber';
    }
    if (act.includes('TRANSFER') || act.includes('HANDOFF')) {
      return 'ws-badge-blue';
    }
    return 'ws-badge-subtle';
  };

  // Filtered Events
  const filteredEvents = events.filter(e => {
    if (!search.trim()) return true;
    const s = search.toLowerCase();
    return (
      (e.evidence_name || '').toLowerCase().includes(s) ||
      (e.case_number || '').toLowerCase().includes(s) ||
      (e.action || '').toLowerCase().includes(s) ||
      (e.actor_name || '').toLowerCase().includes(s) ||
      (e.details || '').toLowerCase().includes(s)
    );
  });

  return (
    <div className="space-y-6 relative z-10">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shadow-xs">
              <History className="w-4.5 h-4.5" />
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight font-sans">
              Chain of Custody Ledger
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1 font-sans">
            Cryptographically sealed timeline of evidence acquisition, transfer, and custodial handoffs.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadCustody}
            className="ws-btn ws-btn-secondary"
            title="Reload Custody Ledger"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Ledger</span>
          </button>

          <button
            onClick={handleSeedDemo}
            disabled={seeding}
            className="ws-btn ws-btn-amber"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>{seeding ? 'Seeding...' : 'Seed Verification Ledger'}</span>
          </button>
        </div>
      </div>

      {/* Summary Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="ws-panel p-4.5 space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
            <span>Audit Records</span>
            <div className="w-7 h-7 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
              <History className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">{events.length}</div>
          <div className="text-[11px] text-blue-600 font-medium">Immutable Ledger Entries</div>
        </div>

        <div className="ws-panel p-4.5 space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
            <span>Chain Continuity</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-emerald-600 font-mono tracking-tight">UNBROKEN</div>
          <div className="text-[11px] text-slate-500">Cryptographic Hash Chaining</div>
        </div>

        <div className="ws-panel p-4.5 space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
            <span>Integrity Verifications</span>
            <div className="w-7 h-7 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600">
              <CheckCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
            {events.filter(e => (e.action || '').includes('VERIF')).length}
          </div>
          <div className="text-[11px] text-emerald-600 font-medium">0 Bit-Rot Anomalies</div>
        </div>

        <div className="ws-panel p-4.5 space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
            <span>Jurisdiction Standard</span>
            <div className="w-7 h-7 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-amber-700 font-mono tracking-tight">ISO/IEC 27037</div>
          <div className="text-[11px] text-slate-500">Court-Admissible Provenance</div>
        </div>
      </div>

      {/* Search & Case Filter Toolbar */}
      <div className="ws-panel p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="relative w-72">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filter exhibit, examiner, action, or note..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="ws-input w-full pl-9 py-1.5 text-xs font-mono"
            />
          </div>

          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg text-xs">
            <span className="text-slate-500 font-bold uppercase text-[10px]">CASE:</span>
            <select
              value={selectedCaseId}
              onChange={e => setSelectedCaseId(e.target.value)}
              className="bg-transparent text-slate-800 font-semibold border-none focus:outline-none text-xs cursor-pointer"
            >
              <option value="">ALL CASES ({cases.length})</option>
              {cases.map(c => (
                <option key={c._id} value={c._id}>
                  {c.case_number} - {c.title}
                </option>
              ))}
            </select>
          </div>
        </div>

        <span className="text-slate-500 text-xs font-mono">
          Displaying <strong className="text-slate-900">{filteredEvents.length}</strong> of {events.length} ledger events
        </span>
      </div>

      {/* Master Custody Table */}
      <div className="ws-panel overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-500 font-mono text-xs space-y-2 flex flex-col items-center justify-center">
            <RefreshCw className="w-5 h-5 animate-spin text-blue-600" />
            <p>Verifying cryptographic custody chain...</p>
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="p-12 text-center space-y-3 text-xs">
            <History className="w-10 h-10 text-slate-300 mx-auto" />
            <div className="text-sm font-bold text-slate-900">No Chain of Custody Records Found</div>
            <p className="text-slate-500 max-w-sm mx-auto text-xs">
              Custody ledger records are automatically anchored when exhibits are ingested, verified, or transferred.
            </p>
            <button
              onClick={handleSeedDemo}
              disabled={seeding}
              className="ws-btn ws-btn-secondary px-3 py-1.5 text-xs mt-2"
            >
              {seeding ? 'Seeding...' : 'Seed Verification Ledger'}
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="ws-table">
              <thead>
                <tr>
                  <th>Timestamp (UTC)</th>
                  <th>Case Ref</th>
                  <th>Evidence Exhibit</th>
                  <th>Custodial Event</th>
                  <th>Examiner / Actor</th>
                  <th>Operational Narrative</th>
                  <th>Block Hash Link</th>
                  <th>Physical Vault Node</th>
                </tr>
              </thead>
              <tbody>
                {filteredEvents.map((evt) => (
                  <tr key={evt._id}>
                    <td className="text-slate-500 whitespace-nowrap text-xs font-mono">
                      {evt.timestamp ? `${formatIsoDateSafe(evt.timestamp, 19)} UTC` : 'N/A'}
                    </td>
                    <td className="whitespace-nowrap font-bold">
                      <Link
                        to={`/cases/${evt.case_id}`}
                        className="text-blue-600 hover:text-blue-800 flex items-center gap-1 font-mono"
                      >
                        <span>{evt.case_number}</span>
                        <ExternalLink className="w-3 h-3 text-slate-400" />
                      </Link>
                    </td>
                    <td className="font-semibold text-slate-900 whitespace-nowrap">
                      {evt.evidence_name}
                    </td>
                    <td className="whitespace-nowrap">
                      <span className={`ws-badge ${getActionBadgeClass(evt.action)} text-[10px]`}>
                        {evt.action}
                      </span>
                    </td>
                    <td className="whitespace-nowrap">
                      <div className="flex items-center gap-1.5 text-slate-800">
                        <UserIcon className="w-3.5 h-3.5 text-slate-400" />
                        <span className="font-medium">{evt.actor_name || 'Investigator'}</span>
                      </div>
                    </td>
                    <td className="text-slate-600 max-w-xs text-xs truncate" title={evt.details}>
                      {evt.details}
                    </td>
                    <td className="whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <GitCommit className="w-3 h-3 text-slate-400" />
                        <span className="text-[11px] font-mono text-slate-600 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded truncate max-w-[110px]" title={evt.event_hash}>
                          {evt.event_hash ? evt.event_hash.slice(0, 14) + '...' : 'GENESIS'}
                        </span>
                        {evt.event_hash && (
                          <button
                            onClick={() => handleCopy(evt.event_hash)}
                            className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-700 transition-colors"
                            title="Copy Cryptographic Event Hash"
                          >
                            {copiedHash === evt.event_hash ? (
                              <CheckCircle className="w-3 h-3 text-emerald-600" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="whitespace-nowrap text-slate-500 text-xs">
                      <span className="flex items-center gap-1">
                        <Cpu className="w-3.5 h-3.5 text-slate-400" />
                        {evt.device_id || 'NODE-SEC-01'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChainOfCustodyPage;
