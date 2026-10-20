import axios from 'axios';

export const getApiBaseUrl = (): string => {
  if (typeof window !== 'undefined') {
    const custom = localStorage.getItem('forensic_api_url');
    if (custom && custom.trim()) {
      const trimmed = custom.trim();
      return trimmed.endsWith('/api') ? trimmed : `${trimmed.replace(/\/$/, '')}/api`;
    }
  }
  const rawUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  return rawUrl.endsWith('/api') ? rawUrl : `${rawUrl.replace(/\/$/, '')}/api`;
};

const api = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30s timeout so requests don't hang indefinitely
});

// Automatically inject JWT token from local storage and ensure up-to-date baseURL
api.interceptors.request.use(
  (config) => {
    config.baseURL = getApiBaseUrl();
    const token = localStorage.getItem('forensic_token');
    if (token && config.headers) {
      if (typeof config.headers.set === 'function') {
        config.headers.set('Authorization', `Bearer ${token}`);
      } else {
        config.headers['Authorization'] = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle session expiries gracefully
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      const requestUrl = error.config?.url || '';
      // Explicitly exempt login, registration, and hardware auth attempts from redirecting
      if (
        requestUrl.includes('/auth/login') ||
        requestUrl.includes('/auth/register') ||
        requestUrl.includes('/hardware/authenticate')
      ) {
        return Promise.reject(error);
      }

      // Expired or invalid token on protected resources
      localStorage.removeItem('forensic_token');
      localStorage.removeItem('forensic_user');
      delete api.defaults.headers.common['Authorization'];

      // Redirect if not already on the login or landing page
      if (window.location.pathname !== '/login' && window.location.pathname !== '/') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const caseApi = {
  getCases: async (params?: {
    search?: string;
    status?: string;
    priority?: string;
    case_type?: string;
    assigned_investigator?: string;
    include_archived?: boolean;
    skip?: number;
    limit?: number;
  }) => {
    const res = await api.get('/cases', { params });
    return res.data;
  },

  getCaseStats: async () => {
    const res = await api.get('/cases/stats');
    return res.data;
  },

  getCase: async (caseId: string) => {
    const res = await api.get(`/cases/${caseId}`);
    return res.data;
  },

  createCase: async (payload: {
    title: string;
    description?: string;
    case_type?: string;
    priority?: string;
    assigned_investigator?: string;
    tags?: string[];
    initial_note?: string;
  }) => {
    const res = await api.post('/cases', payload);
    return res.data;
  },

  updateCase: async (caseId: string, payload: {
    title?: string;
    description?: string;
    case_type?: string;
    priority?: string;
    assigned_investigator?: string;
    tags?: string[];
  }) => {
    const res = await api.put(`/cases/${caseId}`, payload);
    return res.data;
  },

  updateCaseStatus: async (caseId: string, status: string) => {
    const res = await api.patch(`/cases/${caseId}/status`, { status });
    return res.data;
  },

  addCaseNote: async (caseId: string, content: string) => {
    const res = await api.post(`/cases/${caseId}/notes`, { content });
    return res.data;
  },

  archiveCase: async (caseId: string) => {
    const res = await api.delete(`/cases/${caseId}`);
    return res.data;
  },

  getInvestigators: async () => {
    const res = await api.get('/investigators');
    return res.data;
  },

  extractMetadata: async (caseId: string, formData: FormData) => {
    const res = await api.post(`/cases/${caseId}/extract-metadata`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },

  getCaseMetadata: async (caseId: string) => {
    const res = await api.get(`/cases/${caseId}/evidence-metadata`);
    return res.data;
  },

  seedDemo: async () => {
    const res = await api.post('/cases/seed-demo');
    return res.data;
  }
};

export const evidenceApi = {
  uploadEvidence: async (caseId: string, formData: FormData) => {
    const res = await api.post(`/cases/${caseId}/evidence`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },

  getCaseEvidence: async (caseId: string) => {
    const res = await api.get(`/cases/${caseId}/evidence`);
    return res.data;
  },

  getAllEvidence: async (params?: {
    search?: string;
    integrity_status?: string;
    case_id?: string;
    skip?: number;
    limit?: number;
  }) => {
    const res = await api.get('/evidence', { params });
    return res.data;
  },

  getEvidence: async (evidenceId: string) => {
    const res = await api.get(`/evidence/${evidenceId}`);
    return res.data;
  },

  verifyEvidence: async (evidenceId: string) => {
    const res = await api.post(`/evidence/${evidenceId}/verify`);
    return res.data;
  },

  getCustodyHistory: async (evidenceId: string) => {
    const res = await api.get(`/evidence/${evidenceId}/custody`);
    return res.data;
  },

  getEvidenceStats: async () => {
    const res = await api.get('/evidence/stats');
    return res.data;
  },

  getAllCustodyEvents: async (params?: { case_id?: string; evidence_id?: string; limit?: number }) => {
    const res = await api.get('/custody', { params });
    return res.data;
  },

  downloadEvidenceBlob: async (evidenceId: string) => {
    const res = await api.get(`/evidence/${evidenceId}/download`, {
      responseType: 'blob'
    });
    return res.data;
  },

  getDownloadUrl: (evidenceId: string) => {
    const token = localStorage.getItem('forensic_token');
    return `${getApiBaseUrl()}/evidence/${evidenceId}/download${token ? `?token=${token}` : ''}`;
  }
};

export const eventApi = {
  getCaseTimeline: async (caseId: string, params?: {
    start_time?: string;
    end_time?: string;
    event_type?: string;
    severity?: string;
    source_type?: string;
    evidence_id?: string;
    search?: string;
    order?: string;
    skip?: number;
    limit?: number;
  }) => {
    const res = await api.get(`/cases/${caseId}/timeline`, { params });
    return res.data;
  },

  getTimelineStats: async (caseId: string) => {
    const res = await api.get(`/cases/${caseId}/timeline/stats`);
    return res.data;
  },

  createCaseEvent: async (caseId: string, payload: any) => {
    const res = await api.post(`/cases/${caseId}/events`, payload);
    return res.data;
  },

  getEvent: async (eventId: string) => {
    const res = await api.get(`/events/${eventId}`);
    return res.data;
  },

  updateEvent: async (eventId: string, payload: any) => {
    const res = await api.put(`/events/${eventId}`, payload);
    return res.data;
  }
};

export const analyticsApi = {
  getCaseGraph: async (caseId: string, params?: { node_type?: string; severity?: string }) => {
    const res = await api.get(`/cases/${caseId}/graph`, { params });
    return res.data;
  },

  getCaseRiskScore: async (caseId: string) => {
    const res = await api.get(`/cases/${caseId}/risk-score`);
    return res.data;
  },

  getCaseAIAnalysis: async (caseId: string) => {
    const res = await api.get(`/cases/${caseId}/ai-analysis`);
    return res.data;
  },

  getCaseRecommendations: async (caseId: string) => {
    const res = await api.get(`/cases/${caseId}/recommendations`);
    return res.data;
  },

  generateCaseRecommendations: async (caseId: string) => {
    const res = await api.post(`/cases/${caseId}/recommendations/generate`);
    return res.data;
  },

  getGlobalRiskStats: async () => {
    const res = await api.get('/cases/risk/stats');
    return res.data;
  }
};

export const reportApi = {
  getAllReports: async () => {
    const res = await api.get('/reports');
    return res.data;
  },

  getCaseReports: async (caseId: string) => {
    const res = await api.get(`/cases/${caseId}/reports`);
    return res.data;
  },

  generateCaseReport: async (caseId: string, payload?: { title?: string; classification?: string; notes?: string }) => {
    const res = await api.post(`/cases/${caseId}/reports`, payload || {});
    return res.data;
  },

  getReport: async (reportId: string) => {
    const res = await api.get(`/reports/${reportId}`);
    return res.data;
  },

  downloadReportBlob: async (reportId: string) => {
    const res = await api.get(`/reports/${reportId}/download`, {
      responseType: 'blob'
    });
    return res.data;
  },

  getDownloadUrl: (reportId: string) => {
    const token = localStorage.getItem('forensic_token');
    return `${getApiBaseUrl()}/reports/${reportId}/download${token ? `?token=${token}` : ''}`;
  }
};

export const securityApi = {
  getEvents: async (params?: {
    case_id?: string;
    evidence_id?: string;
    event_type?: string;
    ip_address?: string;
    severity?: string;
    skip?: number;
    limit?: number;
  }) => {
    const res = await api.get('/security/events', { params });
    return res.data;
  },

  getEvent: async (eventId: string) => {
    const res = await api.get(`/security/events/${eventId}`);
    return res.data;
  },

  getAlerts: async (params?: {
    status?: string;
    severity?: string;
    skip?: number;
    limit?: number;
  }) => {
    const res = await api.get('/security/alerts', { params });
    return res.data;
  },

  getAlert: async (alertId: string) => {
    const res = await api.get(`/security/alerts/${alertId}`);
    return res.data;
  },

  updateAlertStatus: async (alertId: string, payload: { status: string; notes?: string }) => {
    const res = await api.patch(`/security/alerts/${alertId}/status`, payload);
    return res.data;
  },

  getStats: async () => {
    const res = await api.get('/security/stats');
    return res.data;
  }
};

export default api;


export const backupApi = {
  /**
   * Get preserved original backup metadata for an evidence item.
   * Physical storage path is never returned from the server.
   * Requires ADMIN or INVESTIGATOR role.
   */
  getEvidenceBackup: async (evidenceId: string) => {
    const res = await api.get(`/evidence/${evidenceId}/backup`);
    return res.data;
  },

  /**
   * Verify the backup file itself (not just the working copy).
   * Recalculates backup SHA-256 and compares against stored backup_sha256.
   * Requires ADMIN or INVESTIGATOR role.
   */
  verifyBackupIntegrity: async (evidenceId: string) => {
    const res = await api.post(`/evidence/${evidenceId}/backup/verify`);
    return res.data;
  },

  /**
   * List all preserved original backups for a case.
   * Requires ADMIN or INVESTIGATOR role.
   */
  getCaseBackups: async (caseId: string) => {
    const res = await api.get(`/cases/${caseId}/backups`);
    return res.data;
  },

  /**
   * Get secure download URL for the preserved original.
   * ADMIN only — every download is audited server-side.
   */
  getBackupDownloadUrl: (evidenceId: string) => {
    const token = localStorage.getItem('forensic_token');
    return `${getApiBaseUrl()}/evidence/${evidenceId}/backup/download${token ? `?token=${token}` : ''}`;
  }
};

export const diaryApi = {
  /**
   * Fetch digital investigation diary entries for a case with optional date filtering and search.
   */
  getCaseDiary: async (caseId: string, params?: {
    start_date?: string;
    end_date?: string;
    search?: string;
    skip?: number;
    limit?: number;
    sort_order?: number;
  }) => {
    const res = await api.get(`/cases/${caseId}/diary`, { params });
    return res.data;
  },

  /**
   * Get single investigation diary entry by ID.
   */
  getDiaryEntry: async (caseId: string, entryId: string) => {
    const res = await api.get(`/cases/${caseId}/diary/${entryId}`);
    return res.data;
  },

  /**
   * Record a new day-by-day Investigation Diary entry under BNSS Section 192.
   */
  createDiaryEntry: async (caseId: string, payload: {
    investigation_date: string;
    time_info_received?: string;
    start_time: string;
    closing_time: string;
    places_visited: string[];
    activities_performed: string;
    findings: string;
    related_evidence_ids?: string[];
    witness_references?: string;
    next_steps?: string;
    timeline_events?: { time: string; location: string; activity: string }[];
    raw_input?: string;
    detected_language?: string;
  }) => {
    const res = await api.post(`/cases/${caseId}/diary`, payload);
    return res.data;
  },

  /**
   * Amend a finalized diary entry with an official justification.
   */
  amendDiaryEntry: async (caseId: string, entryId: string, payload: {
    reason: string;
    investigation_date?: string;
    time_info_received?: string;
    start_time?: string;
    closing_time?: string;
    places_visited?: string[];
    activities_performed?: string;
    findings?: string;
    related_evidence_ids?: string[];
    witness_references?: string;
    next_steps?: string;
    timeline_events?: { time: string; location: string; activity: string }[];
    raw_input?: string;
    detected_language?: string;
  }) => {
    const res = await api.post(`/cases/${caseId}/diary/${entryId}/amend`, payload);
    return res.data;
  },

  /**
   * Verify SHA-256 seal integrity and chain continuity of a diary entry.
   */
  verifyDiaryEntry: async (caseId: string, entryId: string) => {
    const res = await api.get(`/cases/${caseId}/diary/${entryId}/verify`);
    return res.data;
  },

  /**
   * AI-driven parser for Tanglish, Hinglish, informal field notes, and audio transcripts.
   * Extracts chronological timeline milestones and normalizes into court-admissible forensic English.
   */
  aiParseDiaryNarrative: async (caseId: string, payload: { raw_text: string; investigation_date?: string }) => {
    const res = await api.post(`/cases/${caseId}/diary/ai-parse`, payload);
    return res.data;
  }
};

