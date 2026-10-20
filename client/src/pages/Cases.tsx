import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate, Link } from 'react-router-dom';
import { 
  FolderLock, 
  Plus, 
  Search, 
  RefreshCw, 
  ExternalLink, 
  Edit3, 
  Archive, 
  CheckCircle2, 
  AlertTriangle, 
  X
} from 'lucide-react';
import { caseApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { Case, CaseStats, CasePriority, CaseType, InvestigatorOption } from '../types';

export const Cases: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const isReadOnly = user?.role === 'readonly';

  // State
  const [cases, setCases] = useState<Case[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [stats, setStats] = useState<CaseStats | null>(null);
  const [investigators, setInvestigators] = useState<InvestigatorOption[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [includeArchived, setIncludeArchived] = useState<boolean>(false);

  // Modals
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);
  const [isEditOpen, setIsEditOpen] = useState<boolean>(false);
  const [editingCase, setEditingCase] = useState<Case | null>(null);

  // Form states
  const [formTitle, setFormTitle] = useState<string>('');
  const [formType, setFormType] = useState<CaseType>('DATA_BREACH');
  const [formPriority, setFormPriority] = useState<CasePriority>('MEDIUM');
  const [formInvestigator, setFormInvestigator] = useState<string>('');
  const [formDescription, setFormDescription] = useState<string>('');
  const [formTags, setFormTags] = useState<string>('');
  const [formInitialNote, setFormInitialNote] = useState<string>('');
  const [formSubmitting, setFormSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Fetch Cases and Stats
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [casesRes, statsRes] = await Promise.all([
        caseApi.getCases({
          search: search.trim() || undefined,
          status: statusFilter || undefined,
          priority: priorityFilter || undefined,
          case_type: typeFilter || undefined,
          include_archived: includeArchived,
          limit: 50
        }),
        caseApi.getCaseStats()
      ]);
      setCases(casesRes.cases || []);
      setTotal(casesRes.total || 0);
      setStats(statsRes);
    } catch (err: any) {
      console.error('Failed to load cases:', err);
      setError(err.response?.data?.detail || 'Failed to load forensic cases.');
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, priorityFilter, typeFilter, includeArchived]);

  // Load investigators for dropdown
  useEffect(() => {
    const loadInvestigators = async () => {
      try {
        const list = await caseApi.getInvestigators();
        setInvestigators(list || []);
      } catch (err) {
        console.error('Failed to fetch investigators:', err);
      }
    };
    loadInvestigators();
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Create Case Handler
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim()) {
      setFormError('Case title is required.');
      return;
    }

    setFormSubmitting(true);
    setFormError(null);
    try {
      const tagsArray = formTags
        .split(',')
        .map(t => t.trim().toUpperCase())
        .filter(t => t.length > 0);

      const payload = {
        title: formTitle.trim(),
        description: formDescription.trim() || undefined,
        case_type: formType,
        priority: formPriority,
        assigned_investigator: formInvestigator || undefined,
        tags: tagsArray.length > 0 ? tagsArray : undefined,
        initial_note: formInitialNote.trim() || undefined
      };

      const newCase = await caseApi.createCase(payload);
      setIsCreateOpen(false);
      resetForm();
      setActionSuccess(`Case ${newCase.case_number} registered successfully.`);
      setTimeout(() => setActionSuccess(null), 4000);
      fetchData();
      navigate(`/cases/${newCase._id}`);
    } catch (err: any) {
      console.error('Case creation failed:', err);
      setFormError(err.response?.data?.detail || 'Failed to create case dossier.');
    } finally {
      setFormSubmitting(false);
    }
  };

  // Edit Case Handler
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCase || !formTitle.trim()) return;

    setFormSubmitting(true);
    setFormError(null);
    try {
      const tagsArray = formTags
        .split(',')
        .map(t => t.trim().toUpperCase())
        .filter(t => t.length > 0);

      const payload = {
        title: formTitle.trim(),
        description: formDescription.trim(),
        case_type: formType,
        priority: formPriority,
        assigned_investigator: formInvestigator || undefined,
        tags: tagsArray
      };

      await caseApi.updateCase(editingCase._id, payload);
      setIsEditOpen(false);
      setEditingCase(null);
      resetForm();
      setActionSuccess(`Case ${editingCase.case_number} updated.`);
      setTimeout(() => setActionSuccess(null), 4000);
      fetchData();
    } catch (err: any) {
      console.error('Case update failed:', err);
      setFormError(err.response?.data?.detail || 'Failed to update case dossier.');
    } finally {
      setFormSubmitting(false);
    }
  };

  // Soft Delete / Archive Handler
  const handleArchiveCase = async (c: Case) => {
    if (!isAdmin) return;
    if (!window.confirm(`Archive case ${c.case_number}? It will remain preserved for legal chain of custody.`)) return;

    try {
      await caseApi.archiveCase(c._id);
      setActionSuccess(`Case ${c.case_number} archived.`);
      setTimeout(() => setActionSuccess(null), 4000);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to archive case.');
    }
  };

  const openEditModal = (c: Case) => {
    setEditingCase(c);
    setFormTitle(c.title);
    setFormType(c.case_type);
    setFormPriority(c.priority);
    setFormInvestigator(c.assigned_investigator || '');
    setFormDescription(c.description || '');
    setFormTags((c.tags || []).join(', '));
    setFormInitialNote('');
    setFormError(null);
    setIsEditOpen(true);
  };

  const resetForm = () => {
    setFormTitle('');
    setFormType('DATA_BREACH');
    setFormPriority('MEDIUM');
    setFormInvestigator('');
    setFormDescription('');
    setFormTags('');
    setFormInitialNote('');
    setFormError(null);
  };

  return (
    <div className="space-y-5 animate-fade-in-up">
      {/* Header & Registration CTA */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight font-sans">
              Investigation Case Files
            </h1>
            <span className="ws-badge ws-badge-gray">{total} Registered</span>
          </div>
          <p className="text-xs text-slate-500 mt-1 font-sans">
            Forensic case records with evidence tracking and chain of custody.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={fetchData}
            className="ws-btn ws-btn-secondary"
            title="Refresh case register"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          {!isReadOnly && (
            <button
              onClick={() => { resetForm(); setIsCreateOpen(true); }}
              className="ws-btn ws-btn-amber"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Register New Case</span>
            </button>
          )}
        </div>
      </div>

      {/* Notifications */}
      {actionSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-mono text-emerald-800 flex items-center gap-2.5 shadow-2xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {error && (
        <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs font-mono text-red-800 flex items-center gap-2.5 shadow-2xs">
          <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Statistics Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="ws-panel p-3.5">
          <div className="text-[10px] font-mono text-slate-500 uppercase font-bold">Total Cases</div>
          <div className="text-xl font-extrabold text-slate-900 font-mono mt-0.5">{stats?.total_cases ?? 0}</div>
        </div>
        <div className="ws-panel p-3.5">
          <div className="text-[10px] font-mono text-slate-500 uppercase font-bold">Active Inquest</div>
          <div className="text-xl font-extrabold text-blue-600 font-mono mt-0.5">{stats?.active_cases ?? 0}</div>
        </div>
        <div className="ws-panel p-3.5">
          <div className="text-[10px] font-mono text-slate-500 uppercase font-bold">Open Queue</div>
          <div className="text-xl font-extrabold text-amber-600 font-mono mt-0.5">{stats?.open_cases ?? 0}</div>
        </div>
        <div className="ws-panel p-3.5">
          <div className="text-[10px] font-mono text-slate-500 uppercase font-bold">Critical Tier</div>
          <div className="text-xl font-extrabold text-red-600 font-mono mt-0.5">{stats?.critical_cases ?? 0}</div>
        </div>
        <div className="ws-panel p-3.5">
          <div className="text-[10px] font-mono text-slate-500 uppercase font-bold">Closed / Court</div>
          <div className="text-xl font-extrabold text-emerald-600 font-mono mt-0.5">{stats?.closed_cases ?? 0}</div>
        </div>
        <div className="ws-panel p-3.5">
          <div className="text-[10px] font-mono text-slate-500 uppercase font-bold">Archived Vault</div>
          <div className="text-xl font-extrabold text-slate-600 font-mono mt-0.5">{stats?.archived_cases ?? 0}</div>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="ws-panel p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search case #, title, tags..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="ws-input pl-8 w-60 text-xs"
            />
          </div>

          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="ws-select text-xs"
          >
            <option value="">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="PENDING_REVIEW">Pending Review</option>
            <option value="CLOSED">Closed</option>
          </select>

          <select
            value={priorityFilter}
            onChange={e => setPriorityFilter(e.target.value)}
            className="ws-select text-xs"
          >
            <option value="">All Priorities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          <select
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value)}
            className="ws-select text-xs"
          >
            <option value="">All Case Types</option>
            <option value="DATA_BREACH">Data Breach</option>
            <option value="MALWARE">Malware Analysis</option>
            <option value="INSIDER_THREAT">Insider Threat</option>
            <option value="FINANCIAL_FRAUD">Financial Fraud</option>
            <option value="PHISHING">Phishing / BEC</option>
            <option value="UNAUTHORIZED_ACCESS">Unauthorized Access</option>
            <option value="OTHER">Other Forensics</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={e => setIncludeArchived(e.target.checked)}
              className="rounded border-slate-300 text-amber-600 focus:ring-amber-500"
            />
            <span>Include Archived</span>
          </label>
        </div>
      </div>

      {/* Structured Cases Table */}
      <div className="ws-panel overflow-hidden">
        <div className="table-responsive">
          <table className="ws-table min-w-[720px]">
          <thead>
            <tr>
              <th>Case Number</th>
              <th>Investigation Title</th>
              <th>Type</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Assigned Investigator</th>
              <th>Created (UTC)</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {cases.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-12 text-slate-500">
                  {loading ? 'Querying case registry...' : 'No case records match the specified filters.'}
                </td>
              </tr>
            ) : (
              cases.map(c => (
                <tr key={c._id} className="cursor-pointer">
                  <td className="font-mono text-xs font-bold text-blue-600 whitespace-nowrap">
                    <Link to={`/cases/${c._id}`}>{c.case_number}</Link>
                  </td>
                  <td>
                    <div className="font-semibold text-xs text-slate-900">
                      <Link to={`/cases/${c._id}`}>{c.title}</Link>
                    </div>
                    {c.description && (
                      <div className="text-[11px] text-slate-500 line-clamp-1 mt-0.5 font-normal">
                        {c.description}
                      </div>
                    )}
                  </td>
                  <td>
                    <span className="ws-badge ws-badge-gray">{c.case_type?.replace(/_/g, ' ')}</span>
                  </td>
                  <td>
                    <span className={`ws-badge ${
                      c.priority === 'CRITICAL' ? 'ws-badge-red' :
                      c.priority === 'HIGH' ? 'ws-badge-amber' : 'ws-badge-blue'
                    }`}>
                      {c.priority}
                    </span>
                  </td>
                  <td>
                    <span className={`ws-badge ${
                      c.status === 'IN_PROGRESS' ? 'ws-badge-amber' :
                      c.status === 'CLOSED' ? 'ws-badge-green' : 'ws-badge-gray'
                    }`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="text-xs text-slate-600 whitespace-nowrap">
                    {c.assigned_investigator_name || 'Unassigned'}
                  </td>
                  <td className="font-mono text-[11px] text-slate-500 whitespace-nowrap">
                    {new Date(c.created_at).toISOString().replace('T', ' ').substring(0, 16)}
                  </td>
                  <td className="text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5">
                      <Link
                        to={`/cases/${c._id}`}
                        className="ws-btn ws-btn-secondary !py-1 !px-2 !text-[11px]"
                        title="Open Case Dossier"
                      >
                        <span>Open</span>
                        <ExternalLink className="w-3 h-3" />
                      </Link>

                      {!isReadOnly && (
                        <button
                          onClick={() => openEditModal(c)}
                          className="ws-btn ws-btn-secondary !py-1 !px-2 !text-[11px]"
                          title="Edit Case Metadata"
                        >
                          <Edit3 className="w-3 h-3" />
                        </button>
                      )}

                      {isAdmin && c.status !== 'ARCHIVED' && (
                        <button
                          onClick={() => handleArchiveCase(c)}
                          className="ws-btn ws-btn-danger !py-1 !px-2 !text-[11px]"
                          title="Archive Case"
                        >
                          <Archive className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        </div>
      </div>

      {/* Case Registration / Edit Modal (Centered, Scrollable, Non-clipping via Portal) */}
      {(isCreateOpen || isEditOpen) && createPortal(
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 overflow-y-auto"
          onClick={() => { setIsCreateOpen(false); setIsEditOpen(false); }}
        >
          <div 
            className="ws-panel-elevated w-full max-w-xl max-h-[90vh] flex flex-col my-auto overflow-hidden shadow-2xl animate-fade-in-up"
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-white shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shrink-0">
                  <FolderLock className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 font-mono tracking-tight">
                  {isCreateOpen ? 'Register New Forensic Case' : `Edit Case ${editingCase?.case_number}`}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => { setIsCreateOpen(false); setIsEditOpen(false); }}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-md transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={isCreateOpen ? handleCreateSubmit : handleEditSubmit} className="flex flex-col flex-1 min-h-0 overflow-hidden">
              {/* Modal Body - Scrollable */}
              <div className="overflow-y-auto p-5 sm:p-6 space-y-4 flex-1 min-h-0">
                {formError && (
                  <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-xs font-mono text-red-700 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
                    <span>{formError}</span>
                  </div>
                )}

                <div className="space-y-4 text-xs">
                  <div className="space-y-1">
                    <label className="text-slate-700 font-semibold block">Investigation Title *</label>
                    <input
                      type="text"
                      value={formTitle}
                      onChange={e => setFormTitle(e.target.value)}
                      placeholder="e.g. Operation Cyber Aegis - Corporate Data Exfiltration"
                      className="ws-input w-full font-sans"
                      required
                      autoFocus
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <label className="text-slate-700 font-semibold block">Case Type</label>
                      <select
                        value={formType}
                        onChange={e => setFormType(e.target.value as CaseType)}
                        className="ws-select w-full"
                      >
                        <option value="DATA_BREACH">Data Breach</option>
                        <option value="MALWARE">Malware</option>
                        <option value="INSIDER_THREAT">Insider Threat</option>
                        <option value="FINANCIAL_FRAUD">Financial Fraud</option>
                        <option value="PHISHING">Phishing</option>
                        <option value="UNAUTHORIZED_ACCESS">Unauthorized Access</option>
                        <option value="OTHER">Other</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-slate-700 font-semibold block">Priority Tier</label>
                      <select
                        value={formPriority}
                        onChange={e => setFormPriority(e.target.value as CasePriority)}
                        className="ws-select w-full"
                      >
                        <option value="LOW">Low</option>
                        <option value="MEDIUM">Medium</option>
                        <option value="HIGH">High</option>
                        <option value="CRITICAL">Critical</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-slate-700 font-semibold block">Assigned Lead</label>
                      <select
                        value={formInvestigator}
                        onChange={e => setFormInvestigator(e.target.value)}
                        className="ws-select w-full"
                      >
                        <option value="">Unassigned</option>
                        {investigators
                          .filter(inv => inv.role !== 'readonly')
                          .map(inv => (
                            <option key={inv._id} value={inv._id}>
                              {inv.name} ({inv.role})
                            </option>
                          ))}
                      </select>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-slate-700 font-semibold block">Forensic Description</label>
                    <textarea
                      value={formDescription}
                      onChange={e => setFormDescription(e.target.value)}
                      rows={3}
                      placeholder="Summary of suspected threat vectors, affected systems, and legal scope..."
                      className="ws-input w-full font-sans"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-slate-700 font-semibold block">Investigation Tags (comma-separated)</label>
                    <input
                      type="text"
                      value={formTags}
                      onChange={e => setFormTags(e.target.value)}
                      placeholder="APT, INSIDER_THREAT, DATABASE_EXFIL"
                      className="ws-input w-full font-mono text-xs"
                    />
                  </div>

                  {isCreateOpen && (
                    <div className="space-y-1">
                      <label className="text-slate-700 font-semibold block">Initial Case Note</label>
                      <textarea
                        value={formInitialNote}
                        onChange={e => setFormInitialNote(e.target.value)}
                        rows={2}
                        placeholder="Initial custodian transfer notes or evidence intake summary..."
                        className="ws-input w-full font-sans"
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Modal Footer */}
              <div className="flex items-center justify-end gap-2.5 px-5 py-3.5 border-t border-slate-200 bg-slate-50 shrink-0">
                <button
                  type="button"
                  onClick={() => { setIsCreateOpen(false); setIsEditOpen(false); }}
                  className="ws-btn ws-btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="ws-btn ws-btn-amber"
                >
                  {formSubmitting ? 'Saving...' : isCreateOpen ? 'Register Case Dossier' : 'Save Changes'}
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

export default Cases;
