import React, { useState, useEffect, useMemo } from 'react';
import {
  Users,
  FolderLock,
  UserCheck,
  UserX,
  Search,
  Filter,
  RefreshCw,
  Edit2,
  CheckCircle,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  UserPlus,
  User,
  Layers
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { portalManagerApi } from '../services/api';
import type {
  PortalManagerOverview,
  PortalUser,
  PortalCaseOversight,
  UserRole
} from '../types';

export const PortalManagerDashboard: React.FC = () => {
  const { user: currentUser } = useAuth();
  const isAdmin = currentUser?.role === 'admin';

  // Active Tab
  const [activeTab, setActiveTab] = useState<'users' | 'cases'>('users');

  // Overview stats
  const [overview, setOverview] = useState<PortalManagerOverview | null>(null);
  const [loadingOverview, setLoadingOverview] = useState<boolean>(true);

  // User Management State
  const [users, setUsers] = useState<PortalUser[]>([]);
  const [totalUsers, setTotalUsers] = useState<number>(0);
  const [loadingUsers, setLoadingUsers] = useState<boolean>(true);
  const [userSearch, setUserSearch] = useState<string>('');
  const [roleFilter, setRoleFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [userPage, setUserPage] = useState<number>(1);
  const pageSize = 10;

  // Case Oversight State
  const [cases, setCases] = useState<PortalCaseOversight[]>([]);
  const [totalCases, setTotalCases] = useState<number>(0);
  const [loadingCases, setLoadingCases] = useState<boolean>(true);
  const [caseSearch, setCaseSearch] = useState<string>('');
  const [caseStatusFilter, setCaseStatusFilter] = useState<string>('ALL');
  const [assignmentFilter, setAssignmentFilter] = useState<string>('ALL');
  const [casePage, setCasePage] = useState<number>(1);

  // Modal Dialogs
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [showEditModal, setShowEditModal] = useState<boolean>(false);
  const [showAssignModal, setShowAssignModal] = useState<boolean>(false);
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);

  // Form State for User Creation
  const [createForm, setCreateForm] = useState({
    name: '',
    email: '',
    role: 'investigator' as UserRole,
    password: '',
    is_active: true
  });
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Form State for User Editing
  const [editTarget, setEditTarget] = useState<PortalUser | null>(null);
  const [editForm, setEditForm] = useState({
    name: '',
    email: '',
    role: 'investigator' as UserRole,
    is_active: true
  });
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Case Assignment Target
  const [assignTargetCase, setAssignTargetCase] = useState<PortalCaseOversight | null>(null);
  const [selectedOfficerId, setSelectedOfficerId] = useState<string>('');
  const [assignSubmitting, setAssignSubmitting] = useState<boolean>(false);

  // Status Toggle Confirmation
  const [confirmTarget, setConfirmTarget] = useState<{
    user: PortalUser;
    action: 'activate' | 'deactivate';
  } | null>(null);
  const [statusToggling, setStatusToggling] = useState(false);

  // Flash Feedback
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const showFeedback = (type: 'success' | 'error', text: string) => {
    setFeedbackMessage({ type, text });
    setTimeout(() => setFeedbackMessage(null), 6000);
  };

  // 1. Fetch Overview Metrics
  const fetchOverview = async () => {
    setLoadingOverview(true);
    try {
      const data = await portalManagerApi.getOverview();
      setOverview(data);
    } catch (err: any) {
      console.error('Failed to fetch portal overview', err);
    } finally {
      setLoadingOverview(false);
    }
  };

  // 2. Fetch Users
  const fetchUsers = async () => {
    setLoadingUsers(true);
    try {
      const res = await portalManagerApi.getUsers({
        search: userSearch.trim() || undefined,
        role: roleFilter !== 'ALL' ? roleFilter : undefined,
        is_active: statusFilter === 'ACTIVE' ? true : statusFilter === 'INACTIVE' ? false : undefined,
        skip: (userPage - 1) * pageSize,
        limit: pageSize
      });
      setUsers(res.users || []);
      setTotalUsers(res.total || 0);
    } catch (err: any) {
      console.error('Failed to fetch users', err);
      showFeedback('error', err.response?.data?.detail || 'Failed to load user directory.');
    } finally {
      setLoadingUsers(false);
    }
  };

  // 3. Fetch Cases Oversight
  const fetchCases = async () => {
    setLoadingCases(true);
    try {
      const res = await portalManagerApi.getCases({
        search: caseSearch.trim() || undefined,
        status: caseStatusFilter !== 'ALL' ? caseStatusFilter : undefined,
        assignment_status: assignmentFilter !== 'ALL' ? assignmentFilter : undefined,
        skip: (casePage - 1) * pageSize,
        limit: pageSize
      });
      setCases(res.cases || []);
      setTotalCases(res.total || 0);
    } catch (err: any) {
      console.error('Failed to fetch oversight cases', err);
      showFeedback('error', err.response?.data?.detail || 'Failed to load case oversight list.');
    } finally {
      setLoadingCases(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [userSearch, roleFilter, statusFilter, userPage]);

  useEffect(() => {
    fetchCases();
  }, [caseSearch, caseStatusFilter, assignmentFilter, casePage]);

  // Handle User Creation
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.name.trim() || !createForm.email.trim() || !createForm.password.trim()) {
      setCreateError('Please complete all required fields.');
      return;
    }
    setCreateSubmitting(true);
    setCreateError(null);
    try {
      await portalManagerApi.createUser(createForm);
      setShowCreateModal(false);
      setCreateForm({
        name: '',
        email: '',
        role: 'investigator',
        password: '',
        is_active: true
      });
      showFeedback('success', `User account '${createForm.email}' provisioned successfully.`);
      fetchUsers();
      fetchOverview();
    } catch (err: any) {
      setCreateError(err.response?.data?.detail || err.message || 'Failed to create user account.');
    } finally {
      setCreateSubmitting(false);
    }
  };

  // Open Edit User Modal
  const openEditModal = (user: PortalUser) => {
    setEditTarget(user);
    setEditForm({
      name: user.name,
      email: user.email,
      role: user.role,
      is_active: user.is_active
    });
    setEditError(null);
    setShowEditModal(true);
  };

  // Handle User Edit Submit
  const handleEditUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editTarget) return;
    setEditSubmitting(true);
    setEditError(null);
    try {
      await portalManagerApi.updateUser(editTarget._id, editForm);
      setShowEditModal(false);
      showFeedback('success', `Account profile for '${editForm.email}' updated successfully.`);
      fetchUsers();
      fetchOverview();
    } catch (err: any) {
      setEditError(err.response?.data?.detail || err.message || 'Failed to update user account.');
    } finally {
      setEditSubmitting(false);
    }
  };

  // Trigger Status Toggle Confirmation
  const promptStatusToggle = (user: PortalUser) => {
    const action = user.is_active ? 'deactivate' : 'activate';
    setConfirmTarget({ user, action });
    setShowConfirmModal(true);
  };

  const handleConfirmStatusToggle = async () => {
    if (!confirmTarget) return;
    setStatusToggling(true);
    try {
      const targetIsActive = confirmTarget.action === 'activate';
      await portalManagerApi.toggleUserStatus(confirmTarget.user._id, targetIsActive);
      setShowConfirmModal(false);
      showFeedback('success', `Account '${confirmTarget.user.email}' is now ${targetIsActive ? 'ACTIVE' : 'DEACTIVATED'}.`);
      fetchUsers();
      fetchOverview();
    } catch (err: any) {
      showFeedback('error', err.response?.data?.detail || 'Failed to alter user status.');
    } finally {
      setStatusToggling(false);
      setConfirmTarget(null);
    }
  };

  // Open Case Assignment Modal
  const openAssignModal = (c: PortalCaseOversight) => {
    setAssignTargetCase(c);
    setSelectedOfficerId(c.assigned_officer_id || '');
    setShowAssignModal(true);
  };

  // Submit Case Assignment
  const handleAssignOfficer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignTargetCase) return;
    setAssignSubmitting(true);
    try {
      await portalManagerApi.assignCase(assignTargetCase.case_id, selectedOfficerId || null);
      setShowAssignModal(false);
      showFeedback('success', `Officer assignment updated for Case ${assignTargetCase.case_number}.`);
      fetchCases();
      fetchOverview();
    } catch (err: any) {
      showFeedback('error', err.response?.data?.detail || 'Failed to update officer assignment.');
    } finally {
      setAssignSubmitting(false);
    }
  };

  // Active Officers list for assignment modal
  const eligibleOfficers = useMemo(() => {
    return users.filter(u => u.is_active && u.role !== 'readonly' && u.role !== 'portal_manager');
  }, [users]);

  return (
    <div className="space-y-6 relative z-10 animate-fade-in-up pb-10">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight font-sans flex items-center gap-2">
              <Users className="w-6 h-6 text-blue-600" />
              <span>Portal Operations & User Management</span>
            </h1>
            <span className="ws-badge ws-badge-blue text-[10px] font-mono uppercase">
              PORTAL_MANAGER
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 font-sans">
            Central administration for portal credentials, investigator accounts, and case assignment oversight.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => {
              fetchOverview();
              if (activeTab === 'users') fetchUsers();
              else fetchCases();
            }}
            className="ws-btn ws-btn-secondary"
            title="Refresh portal statistics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${(loadingOverview || loadingUsers || loadingCases) ? 'animate-spin' : ''}`} />
            <span>Refresh Telemetry</span>
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="ws-btn ws-btn-amber flex items-center gap-1.5"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>Provision New User</span>
          </button>
        </div>
      </div>

      {/* Security Confidentiality Notice Banner */}
      <div className="p-3.5 rounded-lg bg-blue-50/80 border border-blue-200 text-blue-900 text-xs flex items-start gap-3 shadow-xs font-sans">
        <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-bold uppercase tracking-wider text-[11px] font-mono text-blue-800">
            STRICT EVIDENCE CONFIDENTIALITY POLICY ACTIVE
          </span>
          <p className="text-slate-600 text-[11px] leading-relaxed">
            As Portal Manager, you oversee portal personnel, account activation, and officer case allocations. Under the judicial chain-of-custody standard, evidence files, physical exhibits, and forensic examination reports remain cryptographically sealed to authorized casework investigators.
          </p>
        </div>
      </div>

      {/* Feedback Alert Toast */}
      {feedbackMessage && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center gap-2 shadow-xs animate-fade-in-up ${
            feedbackMessage.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}
        >
          {feedbackMessage.type === 'success' ? (
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
          )}
          <span className="font-medium">{feedbackMessage.text}</span>
        </div>
      )}

      {/* Telemetry Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="ws-panel p-3.5 bg-white border border-slate-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-slate-500 block font-mono">TOTAL USERS</span>
          <div className="text-2xl font-extrabold text-slate-900 mt-1 font-mono">
            {loadingOverview ? '…' : overview?.total_users ?? 0}
          </div>
          <span className="text-[10px] text-slate-400">Registered Accounts</span>
        </div>

        <div className="ws-panel p-3.5 bg-white border border-slate-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-emerald-600 block font-mono">ACTIVE USERS</span>
          <div className="text-2xl font-extrabold text-emerald-700 mt-1 font-mono">
            {loadingOverview ? '…' : overview?.active_users ?? 0}
          </div>
          <span className="text-[10px] text-emerald-600 font-semibold">Enabled Logins</span>
        </div>

        <div className="ws-panel p-3.5 bg-white border border-slate-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-amber-600 block font-mono">INACTIVE USERS</span>
          <div className="text-2xl font-extrabold text-amber-700 mt-1 font-mono">
            {loadingOverview ? '…' : overview?.inactive_users ?? 0}
          </div>
          <span className="text-[10px] text-amber-600 font-semibold">Deactivated / Suspended</span>
        </div>

        <div className="ws-panel p-3.5 bg-white border border-slate-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-slate-500 block font-mono">TOTAL CASES</span>
          <div className="text-2xl font-extrabold text-slate-900 mt-1 font-mono">
            {loadingOverview ? '…' : overview?.total_cases ?? 0}
          </div>
          <span className="text-[10px] text-slate-400">Forensic Case Files</span>
        </div>

        <div className="ws-panel p-3.5 bg-white border border-slate-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-blue-600 block font-mono">ASSIGNED OFFICERS</span>
          <div className="text-2xl font-extrabold text-blue-700 mt-1 font-mono">
            {loadingOverview ? '…' : overview?.total_assigned_officers ?? 0}
          </div>
          <span className="text-[10px] text-blue-600">Active Case Handlers</span>
        </div>

        <div className="ws-panel p-3.5 bg-white border border-slate-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-slate-500 block font-mono">ASSIGNMENT RATE</span>
          <div className="text-2xl font-extrabold text-slate-900 mt-1 font-mono">
            {loadingOverview ? '…' : `${overview?.assignment_overview.assignment_rate ?? 0}%`}
          </div>
          <span className="text-[10px] text-slate-500 font-mono">
            {overview?.assignment_overview.assigned_cases ?? 0} / {overview?.total_cases ?? 0} Cases
          </span>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-slate-200 flex items-center gap-6">
        <button
          onClick={() => setActiveTab('users')}
          className={`pb-3 text-xs font-bold uppercase tracking-wider font-mono flex items-center gap-2 border-b-2 transition-colors cursor-pointer ${
            activeTab === 'users'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>User Directory ({totalUsers})</span>
        </button>

        <button
          onClick={() => setActiveTab('cases')}
          className={`pb-3 text-xs font-bold uppercase tracking-wider font-mono flex items-center gap-2 border-b-2 transition-colors cursor-pointer ${
            activeTab === 'cases'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <FolderLock className="w-3.5 h-3.5" />
          <span>Case Oversight & Allocation ({totalCases})</span>
        </button>
      </div>

      {/* TAB 1: USER MANAGEMENT DIRECTORY */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="ws-panel p-3.5 flex flex-wrap items-center justify-between gap-3 bg-white border border-slate-200 shadow-xs">
            <div className="flex items-center gap-2 flex-1 min-w-[240px] max-w-md relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search user by name or email address..."
                value={userSearch}
                onChange={e => {
                  setUserSearch(e.target.value);
                  setUserPage(1);
                }}
                className="ws-input pl-8.5 w-full text-xs font-sans"
              />
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono">
                <Filter className="w-3 h-3 text-slate-400" />
                <span>Role:</span>
              </div>
              <select
                value={roleFilter}
                onChange={e => {
                  setRoleFilter(e.target.value);
                  setUserPage(1);
                }}
                className="ws-select text-xs"
              >
                <option value="ALL">All Roles</option>
                <option value="admin">Chief Investigator (Admin)</option>
                <option value="investigator">Forensic Investigator</option>
                <option value="readonly">Court Auditor (Read-Only)</option>
                <option value="portal_manager">Portal Operations Manager</option>
              </select>

              <select
                value={statusFilter}
                onChange={e => {
                  setStatusFilter(e.target.value);
                  setUserPage(1);
                }}
                className="ws-select text-xs"
              >
                <option value="ALL">All Account Status</option>
                <option value="ACTIVE">Active Logins Only</option>
                <option value="INACTIVE">Deactivated Accounts Only</option>
              </select>
            </div>
          </div>

          {/* Users Table */}
          <div className="ws-panel overflow-hidden bg-white border border-slate-200 shadow-xs">
            <table className="ws-table">
              <thead>
                <tr>
                  <th>Investigator / User</th>
                  <th>Email ID</th>
                  <th>Platform Role</th>
                  <th>Status</th>
                  <th>Assigned Cases</th>
                  <th>Registered (UTC)</th>
                  <th className="text-right">Account Actions</th>
                </tr>
              </thead>
              <tbody>
                {loadingUsers ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-slate-400 font-mono text-xs">
                      <div className="flex flex-col items-center justify-center space-y-2">
                        <RefreshCw className="w-5 h-5 animate-spin text-blue-600" />
                        <span>Querying user directory...</span>
                      </div>
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-slate-500 font-mono text-xs">
                      <div className="space-y-1.5">
                        <UserX className="w-8 h-8 text-slate-300 mx-auto" />
                        <p className="font-semibold text-slate-700">No User Accounts Found</p>
                        <p className="text-slate-400 text-[11px]">
                          Adjust your search query or role filter.
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  users.map(u => {
                    const isTargetAdmin = u.role === 'admin';
                    const isSelf = currentUser?._id === u._id;
                    const canEdit = isAdmin || (!isTargetAdmin && !isSelf);

                    return (
                      <tr key={u._id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="font-semibold text-xs text-slate-900">
                          <div className="flex items-center gap-2">
                            <div className="w-7 h-7 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 font-bold text-xs font-mono shrink-0">
                              {u.name?.charAt(0)?.toUpperCase() || 'U'}
                            </div>
                            <div>
                              <span>{u.name}</span>
                              {isSelf && (
                                <span className="ml-1.5 text-[9px] bg-blue-100 text-blue-700 px-1 py-0.2 rounded font-mono font-bold">
                                  YOU
                                </span>
                              )}
                            </div>
                          </div>
                        </td>

                        <td className="font-mono text-xs text-slate-600">
                          {u.email}
                        </td>

                        <td>
                          <span
                            className={`ws-badge text-[10px] ${
                              u.role === 'admin'
                                ? 'ws-badge-red'
                                : u.role === 'portal_manager'
                                ? 'ws-badge-blue'
                                : u.role === 'readonly'
                                ? 'ws-badge-gray'
                                : 'ws-badge-green'
                            }`}
                          >
                            {u.role?.toUpperCase()}
                          </span>
                        </td>

                        <td>
                          <span
                            className={`ws-badge text-[10px] flex items-center gap-1 w-fit ${
                              u.is_active ? 'ws-badge-green' : 'ws-badge-amber'
                            }`}
                          >
                            <span
                              className={`w-1.5 h-1.5 rounded-full ${
                                u.is_active ? 'bg-emerald-500' : 'bg-amber-500'
                              }`}
                            ></span>
                            <span>{u.is_active ? 'ACTIVE' : 'INACTIVE'}</span>
                          </span>
                        </td>

                        <td className="font-mono text-xs text-slate-700">
                          <span className="font-bold text-slate-900">{u.assigned_cases_count ?? 0}</span> Case(s)
                        </td>

                        <td className="font-mono text-xs text-slate-500">
                          {u.created_at ? new Date(u.created_at).toISOString().slice(0, 10) : 'N/A'}
                        </td>

                        <td className="text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-1.5">
                            {canEdit ? (
                              <>
                                <button
                                  onClick={() => openEditModal(u)}
                                  className="ws-btn ws-btn-secondary !py-1 !px-2 !text-[11px] inline-flex items-center gap-1"
                                  title="Edit user details"
                                >
                                  <Edit2 className="w-3 h-3 text-slate-500" />
                                  <span>Edit</span>
                                </button>

                                <button
                                  onClick={() => promptStatusToggle(u)}
                                  className={`ws-btn !py-1 !px-2 !text-[11px] inline-flex items-center gap-1 ${
                                    u.is_active
                                      ? 'hover:bg-amber-50 text-amber-700 border-amber-200'
                                      : 'hover:bg-emerald-50 text-emerald-700 border-emerald-200'
                                  }`}
                                  title={u.is_active ? 'Deactivate account login' : 'Activate account login'}
                                >
                                  {u.is_active ? (
                                    <>
                                      <UserX className="w-3 h-3 text-amber-600" />
                                      <span>Suspend</span>
                                    </>
                                  ) : (
                                    <>
                                      <UserCheck className="w-3 h-3 text-emerald-600" />
                                      <span>Activate</span>
                                    </>
                                  )}
                                </button>
                              </>
                            ) : (
                              <span className="text-[10px] font-mono text-slate-400 italic px-2 py-1">
                                {isTargetAdmin ? 'Protected Admin' : 'Self Managed'}
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>

            {/* Pagination Controls */}
            {totalUsers > pageSize && (
              <div className="flex items-center justify-between p-3 border-t border-slate-200 bg-slate-50 text-xs font-mono text-slate-600">
                <span>
                  Showing {(userPage - 1) * pageSize + 1} to {Math.min(userPage * pageSize, totalUsers)} of {totalUsers} accounts
                </span>
                <div className="flex items-center gap-1">
                  <button
                    disabled={userPage <= 1}
                    onClick={() => setUserPage(p => Math.max(1, p - 1))}
                    className="ws-btn ws-btn-secondary !py-1 !px-2 disabled:opacity-40"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                  </button>
                  <span className="px-2 font-bold text-slate-800">Page {userPage}</span>
                  <button
                    disabled={userPage * pageSize >= totalUsers}
                    onClick={() => setUserPage(p => p + 1)}
                    className="ws-btn ws-btn-secondary !py-1 !px-2 disabled:opacity-40"
                  >
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: CASE OVERSIGHT & ALLOCATION */}
      {activeTab === 'cases' && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="ws-panel p-3.5 flex flex-wrap items-center justify-between gap-3 bg-white border border-slate-200 shadow-xs">
            <div className="flex items-center gap-2 flex-1 min-w-[240px] max-w-md relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search case #, title, or assigned officer..."
                value={caseSearch}
                onChange={e => {
                  setCaseSearch(e.target.value);
                  setCasePage(1);
                }}
                className="ws-input pl-8.5 w-full text-xs font-sans"
              />
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <select
                value={caseStatusFilter}
                onChange={e => {
                  setCaseStatusFilter(e.target.value);
                  setCasePage(1);
                }}
                className="ws-select text-xs"
              >
                <option value="ALL">All Case Statuses</option>
                <option value="OPEN">OPEN</option>
                <option value="IN_PROGRESS">IN PROGRESS</option>
                <option value="ON_HOLD">ON HOLD</option>
                <option value="CLOSED">CLOSED</option>
              </select>

              <select
                value={assignmentFilter}
                onChange={e => {
                  setAssignmentFilter(e.target.value);
                  setCasePage(1);
                }}
                className="ws-select text-xs"
              >
                <option value="ALL">All Allocation States</option>
                <option value="ASSIGNED">Assigned Cases Only</option>
                <option value="UNASSIGNED">Unassigned Cases Only</option>
              </select>
            </div>
          </div>

          {/* Cases Table */}
          <div className="ws-panel overflow-hidden bg-white border border-slate-200 shadow-xs">
            <table className="ws-table">
              <thead>
                <tr>
                  <th>Case Docket #</th>
                  <th>Title & Description</th>
                  <th>Classification</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Assigned Officer</th>
                  <th>Allocation Status</th>
                  <th className="text-right">Officer Assignment</th>
                </tr>
              </thead>
              <tbody>
                {loadingCases ? (
                  <tr>
                    <td colSpan={8} className="text-center py-12 text-slate-400 font-mono text-xs">
                      <div className="flex flex-col items-center justify-center space-y-2">
                        <RefreshCw className="w-5 h-5 animate-spin text-blue-600" />
                        <span>Querying case repository...</span>
                      </div>
                    </td>
                  </tr>
                ) : cases.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-12 text-slate-500 font-mono text-xs">
                      <div className="space-y-1.5">
                        <FolderLock className="w-8 h-8 text-slate-300 mx-auto" />
                        <p className="font-semibold text-slate-700">No Cases Found</p>
                        <p className="text-slate-400 text-[11px]">
                          Adjust search query or assignment filters.
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  cases.map(c => (
                    <tr key={c._id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="font-mono text-xs font-bold text-blue-700 whitespace-nowrap">
                        {c.case_number}
                      </td>

                      <td className="text-xs max-w-xs">
                        <div className="font-semibold text-slate-900 truncate" title={c.title}>
                          {c.title}
                        </div>
                        {c.description && (
                          <div className="text-slate-500 text-[11px] truncate" title={c.description}>
                            {c.description}
                          </div>
                        )}
                      </td>

                      <td className="font-mono text-[11px] text-slate-600 whitespace-nowrap">
                        {c.case_type}
                      </td>

                      <td>
                        <span
                          className={`ws-badge text-[10px] ${
                            c.priority === 'CRITICAL'
                              ? 'ws-badge-red'
                              : c.priority === 'HIGH'
                              ? 'ws-badge-amber'
                              : 'ws-badge-blue'
                          }`}
                        >
                          {c.priority}
                        </span>
                      </td>

                      <td>
                        <span
                          className={`ws-badge text-[10px] ${
                            c.status === 'IN_PROGRESS'
                              ? 'ws-badge-amber'
                              : c.status === 'CLOSED'
                              ? 'ws-badge-green'
                              : 'ws-badge-gray'
                          }`}
                        >
                          {c.status}
                        </span>
                      </td>

                      <td className="text-xs font-sans whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <User className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span className={c.assigned_officer_id ? 'font-semibold text-slate-900' : 'text-slate-400 italic'}>
                            {c.assigned_officer_name}
                          </span>
                        </div>
                      </td>

                      <td>
                        <span
                          className={`ws-badge text-[10px] ${
                            c.assignment_status === 'ASSIGNED' ? 'ws-badge-green' : 'ws-badge-amber'
                          }`}
                        >
                          {c.assignment_status}
                        </span>
                      </td>

                      <td className="text-right whitespace-nowrap">
                        <button
                          onClick={() => openAssignModal(c)}
                          className="ws-btn ws-btn-secondary !py-1 !px-2 !text-[11px] inline-flex items-center gap-1"
                          title="Assign or reassign investigator"
                        >
                          <Layers className="w-3 h-3 text-blue-600" />
                          <span>Reallocate</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>

            {/* Pagination Controls */}
            {totalCases > pageSize && (
              <div className="flex items-center justify-between p-3 border-t border-slate-200 bg-slate-50 text-xs font-mono text-slate-600">
                <span>
                  Showing {(casePage - 1) * pageSize + 1} to {Math.min(casePage * pageSize, totalCases)} of {totalCases} cases
                </span>
                <div className="flex items-center gap-1">
                  <button
                    disabled={casePage <= 1}
                    onClick={() => setCasePage(p => Math.max(1, p - 1))}
                    className="ws-btn ws-btn-secondary !py-1 !px-2 disabled:opacity-40"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                  </button>
                  <span className="px-2 font-bold text-slate-800">Page {casePage}</span>
                  <button
                    disabled={casePage * pageSize >= totalCases}
                    onClick={() => setCasePage(p => p + 1)}
                    className="ws-btn ws-btn-secondary !py-1 !px-2 disabled:opacity-40"
                  >
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL 1: PROVISION NEW USER */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="ws-panel-elevated w-full max-w-md bg-white border border-slate-200 shadow-2xl p-6 rounded-xl animate-fade-in-up">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 font-sans">
                <UserPlus className="w-5 h-5 text-blue-600" />
                <span>Provision Portal Account</span>
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-700 text-lg font-bold"
              >
                ×
              </button>
            </div>

            {createError && (
              <div className="mt-3 p-2.5 rounded bg-red-50 border border-red-200 text-red-800 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-3.5 mt-4 text-xs font-sans">
              <div>
                <label className="block text-slate-700 font-bold mb-1">Full Legal Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Special Investigator Jane Doe"
                  value={createForm.name}
                  onChange={e => setCreateForm({ ...createForm, name: e.target.value })}
                  className="ws-input w-full"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Official Forensic Email Address *</label>
                <input
                  type="email"
                  required
                  placeholder="e.g. j.doe@forensics.gov"
                  value={createForm.email}
                  onChange={e => setCreateForm({ ...createForm, email: e.target.value })}
                  className="ws-input w-full font-mono text-xs"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Platform Role Designation *</label>
                <select
                  value={createForm.role}
                  onChange={e => setCreateForm({ ...createForm, role: e.target.value as UserRole })}
                  className="ws-select w-full"
                >
                  <option value="investigator">Forensic Investigator (Case Access)</option>
                  <option value="readonly">Court Auditor (Platform-Wide Read-Only)</option>
                  {isAdmin && (
                    <>
                      <option value="portal_manager">Portal Operations Manager</option>
                      <option value="admin">Chief Investigator (Admin)</option>
                    </>
                  )}
                </select>
                {!isAdmin && (
                  <p className="text-[10px] text-slate-400 mt-1 italic">
                    Note: Portal Managers can provision Investigator and Read-Only roles. Chief Investigator accounts require Admin authorization.
                  </p>
                )}
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Temporary Initial Passphrase *</label>
                <input
                  type="password"
                  required
                  placeholder="At least 6 characters"
                  value={createForm.password}
                  onChange={e => setCreateForm({ ...createForm, password: e.target.value })}
                  className="ws-input w-full font-mono text-xs"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="create_is_active"
                  checked={createForm.is_active}
                  onChange={e => setCreateForm({ ...createForm, is_active: e.target.checked })}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="create_is_active" className="text-slate-700 font-medium cursor-pointer">
                  Activate account immediately upon provisioning
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="ws-btn ws-btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createSubmitting}
                  className="ws-btn ws-btn-amber"
                >
                  {createSubmitting ? 'Provisioning...' : 'Provision Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: EDIT USER DETAILS */}
      {showEditModal && editTarget && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="ws-panel-elevated w-full max-w-md bg-white border border-slate-200 shadow-2xl p-6 rounded-xl animate-fade-in-up">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 font-sans">
                <Edit2 className="w-4 h-4 text-blue-600" />
                <span>Edit User Account</span>
              </h3>
              <button
                onClick={() => setShowEditModal(false)}
                className="text-slate-400 hover:text-slate-700 text-lg font-bold"
              >
                ×
              </button>
            </div>

            {editError && (
              <div className="mt-3 p-2.5 rounded bg-red-50 border border-red-200 text-red-800 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{editError}</span>
              </div>
            )}

            <form onSubmit={handleEditUser} className="space-y-3.5 mt-4 text-xs font-sans">
              <div>
                <label className="block text-slate-700 font-bold mb-1">Full Legal Name</label>
                <input
                  type="text"
                  required
                  value={editForm.name}
                  onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                  className="ws-input w-full"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Official Forensic Email Address</label>
                <input
                  type="email"
                  required
                  value={editForm.email}
                  onChange={e => setEditForm({ ...editForm, email: e.target.value })}
                  className="ws-input w-full font-mono text-xs"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Role Designation</label>
                <select
                  value={editForm.role}
                  onChange={e => setEditForm({ ...editForm, role: e.target.value as UserRole })}
                  className="ws-select w-full"
                >
                  <option value="investigator">Forensic Investigator</option>
                  <option value="readonly">Court Auditor (Read-Only)</option>
                  {isAdmin && (
                    <>
                      <option value="portal_manager">Portal Operations Manager</option>
                      <option value="admin">Chief Investigator (Admin)</option>
                    </>
                  )}
                </select>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="edit_is_active"
                  checked={editForm.is_active}
                  onChange={e => setEditForm({ ...editForm, is_active: e.target.checked })}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="edit_is_active" className="text-slate-700 font-medium cursor-pointer">
                  Account is active and permitted to authenticate
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="ws-btn ws-btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editSubmitting}
                  className="ws-btn ws-btn-amber"
                >
                  {editSubmitting ? 'Saving Changes...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: CASE REALLOCATION */}
      {showAssignModal && assignTargetCase && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="ws-panel-elevated w-full max-w-md bg-white border border-slate-200 shadow-2xl p-6 rounded-xl animate-fade-in-up">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 font-sans">
                <Layers className="w-4 h-4 text-blue-600" />
                <span>Reallocate Case Officer</span>
              </h3>
              <button
                onClick={() => setShowAssignModal(false)}
                className="text-slate-400 hover:text-slate-700 text-lg font-bold"
              >
                ×
              </button>
            </div>

            <div className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded text-xs space-y-1 font-mono">
              <div>
                <span className="text-slate-400">DOCKET:</span>{' '}
                <strong className="text-blue-700">{assignTargetCase.case_number}</strong>
              </div>
              <div>
                <span className="text-slate-400">TITLE:</span>{' '}
                <span className="text-slate-900">{assignTargetCase.title}</span>
              </div>
              <div>
                <span className="text-slate-400">CURRENT OFFICER:</span>{' '}
                <span className="text-slate-800">{assignTargetCase.assigned_officer_name}</span>
              </div>
            </div>

            <form onSubmit={handleAssignOfficer} className="space-y-3.5 mt-4 text-xs font-sans">
              <div>
                <label className="block text-slate-700 font-bold mb-1">Select Lead Investigating Officer</label>
                <select
                  value={selectedOfficerId}
                  onChange={e => setSelectedOfficerId(e.target.value)}
                  className="ws-select w-full"
                >
                  <option value="">-- Unassigned (No Assigned Officer) --</option>
                  {eligibleOfficers.map(off => (
                    <option key={off._id} value={off._id}>
                      {off.name} ({off.email}) [{off.role?.toUpperCase()}]
                    </option>
                  ))}
                </select>
                <p className="text-[10px] text-slate-400 mt-1 italic">
                  Only active forensic investigators are eligible for case assignment.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAssignModal(false)}
                  className="ws-btn ws-btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={assignSubmitting}
                  className="ws-btn ws-btn-amber"
                >
                  {assignSubmitting ? 'Updating...' : 'Confirm Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: CONFIRMATION FOR DEACTIVATE / ACTIVATE */}
      {showConfirmModal && confirmTarget && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="ws-panel-elevated w-full max-w-sm bg-white border border-slate-200 shadow-2xl p-6 rounded-xl animate-fade-in-up">
            <div className="flex items-center gap-2.5 text-amber-600 mb-2 font-sans font-bold text-sm">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <span>Confirm Account State Alteration</span>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed font-sans mb-4">
              Are you sure you want to <strong>{confirmTarget.action.toUpperCase()}</strong> the account for{' '}
              <span className="font-mono text-slate-900 font-semibold">{confirmTarget.user.name}</span> ({confirmTarget.user.email})?
              {confirmTarget.action === 'deactivate' && (
                <span className="block mt-1 text-red-600 font-medium">
                  This user will be immediately barred from workstation authentication and hardware bridge access.
                </span>
              )}
            </p>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => {
                  setShowConfirmModal(false);
                  setConfirmTarget(null);
                }}
                className="ws-btn ws-btn-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={statusToggling}
                onClick={handleConfirmStatusToggle}
                className={`ws-btn ${
                  confirmTarget.action === 'deactivate' ? 'ws-btn-red' : 'ws-btn-green'
                }`}
              >
                {statusToggling ? 'Processing...' : `Confirm ${confirmTarget.action}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PortalManagerDashboard;
