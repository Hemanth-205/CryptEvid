import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useParams, Link } from 'react-router-dom';
import {
  FolderLock,
  ArrowLeft,
  Tag,
  FileCheck,
  CheckCircle2,
  AlertTriangle,
  Send,
  Upload,
  RefreshCw,
  Download,
  Copy,
  Check,
  X,
  History,
  Lock,
  LockOpen,
  Eye,
  EyeOff,
  AlertCircle,
  Info,
  Network,
  GitCommit,
  Search,
  User as UserIcon,
  Cpu,
  ShieldCheck,
  FileDown,
  FileText,
  BookOpen,
  Calendar,
  Clock,
  MapPin,
  Plus,
  FileEdit,
  Sparkles,
  Languages,
  ListOrdered
} from 'lucide-react';
import api, { caseApi, evidenceApi, reportApi, diaryApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { 
  Case, 
  Evidence, 
  EvidenceVerifyResult,
  CustodyEvent,
  DiaryEntry,
  DiaryVerificationResult,
  DiaryTimelineMilestone,
  DiaryParseResponse
} from '../types';

export const CaseDetail: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const { user } = useAuth();
  const isReadOnly = user?.role === 'readonly';

  const [caseData, setCaseData] = useState<Case | null>(null);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [caseCustodyEvents, setCaseCustodyEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'evidence' | 'custody' | 'diary'>('overview');
  const [custodySearch, setCustodySearch] = useState<string>('');
  const [custodyActionFilter, setCustodyActionFilter] = useState<string>('ALL');
  const [loadingCaseCustody, setLoadingCaseCustody] = useState<boolean>(false);

  // Digital Investigation Diary (BNSS Section 192) state
  const [diaryEntries, setDiaryEntries] = useState<DiaryEntry[]>([]);
  const [diaryTotal, setDiaryTotal] = useState<number>(0);
  const [loadingDiary, setLoadingDiary] = useState<boolean>(false);
  const [diaryLegalNotice, setDiaryLegalNotice] = useState<string>('');
  const [diaryStartDate, setDiaryStartDate] = useState<string>('');
  const [diaryEndDate, setDiaryEndDate] = useState<string>('');
  const [diarySearch, setDiarySearch] = useState<string>('');
  const [diarySortOrder, setDiarySortOrder] = useState<1 | -1>(1);
  const [diaryPage, setDiaryPage] = useState<number>(1);
  const diaryPageSize = 8;

  // Record Diary Entry Modal state
  const [showCreateDiaryModal, setShowCreateDiaryModal] = useState<boolean>(false);
  const [createDiaryDate, setCreateDiaryDate] = useState<string>(() => new Date().toISOString().split('T')[0]);
  const [createDiaryTimeReceived, setCreateDiaryTimeReceived] = useState<string>('');
  const [createDiaryStartTime, setCreateDiaryStartTime] = useState<string>('09:30');
  const [createDiaryClosingTime, setCreateDiaryClosingTime] = useState<string>('18:00');
  const [createDiaryPlaces, setCreateDiaryPlaces] = useState<string>('');
  const [createDiaryActivities, setCreateDiaryActivities] = useState<string>('');
  const [createDiaryFindings, setCreateDiaryFindings] = useState<string>('');
  const [createDiarySelectedEvidence, setCreateDiarySelectedEvidence] = useState<string[]>([]);
  const [createDiaryWitness, setCreateDiaryWitness] = useState<string>('');
  const [createDiaryNextSteps, setCreateDiaryNextSteps] = useState<string>('');
  const [createTimelineEvents, setCreateTimelineEvents] = useState<DiaryTimelineMilestone[]>([]);
  const [createAiRawText, setCreateAiRawText] = useState<string>('');
  const [createAiParsing, setCreateAiParsing] = useState<boolean>(false);
  const [createAiMessage, setCreateAiMessage] = useState<string | null>(null);
  const [createDetectedLanguage, setCreateDetectedLanguage] = useState<string>('');
  const [diarySubmitting, setDiarySubmitting] = useState<boolean>(false);
  const [diaryFormError, setDiaryFormError] = useState<string | null>(null);

  // Amend Diary Entry Modal state
  const [amendingEntry, setAmendingEntry] = useState<DiaryEntry | null>(null);
  const [amendReason, setAmendReason] = useState<string>('');
  const [amendDate, setAmendDate] = useState<string>('');
  const [amendTimeReceived, setAmendTimeReceived] = useState<string>('');
  const [amendStartTime, setAmendStartTime] = useState<string>('');
  const [amendClosingTime, setAmendClosingTime] = useState<string>('');
  const [amendPlaces, setAmendPlaces] = useState<string>('');
  const [amendActivities, setAmendActivities] = useState<string>('');
  const [amendFindings, setAmendFindings] = useState<string>('');
  const [amendSelectedEvidence, setAmendSelectedEvidence] = useState<string[]>([]);
  const [amendWitness, setAmendWitness] = useState<string>('');
  const [amendNextSteps, setAmendNextSteps] = useState<string>('');
  const [amendTimelineEvents, setAmendTimelineEvents] = useState<DiaryTimelineMilestone[]>([]);
  const [amendAiRawText, setAmendAiRawText] = useState<string>('');
  const [amendAiParsing, setAmendAiParsing] = useState<boolean>(false);
  const [amendAiMessage, setAmendAiMessage] = useState<string | null>(null);
  const [amendDetectedLanguage, setAmendDetectedLanguage] = useState<string>('');
  const [amendSubmitting, setAmendSubmitting] = useState<boolean>(false);
  const [amendFormError, setAmendFormError] = useState<string | null>(null);
  const [expandedTimelineMap, setExpandedTimelineMap] = useState<Record<string, boolean>>({});

  // View Amendment History state
  const [historyEntry, setHistoryEntry] = useState<DiaryEntry | null>(null);

  // Verification state
  const [verifyingDiaryId, setVerifyingDiaryId] = useState<string | null>(null);
  const [diaryVerifyStatus, setDiaryVerifyStatus] = useState<Record<string, DiaryVerificationResult>>({});

  // Report generation & download state
  const [downloadingReport, setDownloadingReport] = useState<boolean>(false);
  const [reportSuccess, setReportSuccess] = useState<string | null>(null);
  const [recentReportHash, setRecentReportHash] = useState<string | null>(null);

  // Notes form
  const [noteContent, setNoteContent] = useState<string>('');
  const [noteSubmitting, setNoteSubmitting] = useState<boolean>(false);

  // Evidence upload form
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadDescription, setUploadDescription] = useState<string>('');
  const [uploadTags, setUploadTags] = useState<string>('');
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);

  // Verification & Custody & Inspector modals
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [selectedVerify, setSelectedVerify] = useState<EvidenceVerifyResult | null>(null);
  const [custodyEvidence, setCustodyEvidence] = useState<Evidence | null>(null);
  const [custodyEvents, setCustodyEvents] = useState<CustodyEvent[]>([]);
  const [custodyLoading, setCustodyLoading] = useState<boolean>(false);
  const [inspectEvidence, setInspectEvidence] = useState<Evidence | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Evidence Access Authentication Challenge (Mandatory Lock Policy)
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(false);
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null);
  const [authTargetName, setAuthTargetName] = useState<string | null>(null);
  const [authEmail, setAuthEmail] = useState<string>('');
  const [authPassword, setAuthPassword] = useState<string>('');
  const [showAuthPassword, setShowAuthPassword] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSubmitting, setAuthSubmitting] = useState<boolean>(false);

  // Fetch Case Data, Evidence & Custody
  const fetchCaseDetails = async () => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const [caseRes, evidenceRes, custodyRes, diaryRes] = await Promise.all([
        caseApi.getCase(caseId),
        evidenceApi.getCaseEvidence(caseId),
        evidenceApi.getAllCustodyEvents({ case_id: caseId, limit: 300 }).catch(() => ({ events: [] })),
        diaryApi.getCaseDiary(caseId, { skip: 0, limit: diaryPageSize, sort_order: diarySortOrder }).catch(() => ({ entries: [], total: 0, legal_disclaimer: '' }))
      ]);
      setCaseData(caseRes);
      const exhibits: Evidence[] = Array.isArray(evidenceRes) ? evidenceRes : evidenceRes.evidence || [];
      setEvidenceList(exhibits);
      setCaseCustodyEvents(custodyRes?.events || []);
      setDiaryEntries(diaryRes?.entries || []);
      setDiaryTotal(diaryRes?.total || 0);
      setDiaryLegalNotice(diaryRes?.legal_disclaimer || '');
    } catch (err: any) {
      console.error('Failed to load case:', err);
      setError(err.response?.data?.detail || 'Failed to load case details.');
    } finally {
      setLoading(false);
    }
  };

  const loadCaseCustody = async () => {
    if (!caseId) return;
    setLoadingCaseCustody(true);
    try {
      const res = await evidenceApi.getAllCustodyEvents({ case_id: caseId, limit: 300 });
      setCaseCustodyEvents(res.events || []);
    } catch (err) {
      console.error('Failed to reload case custody events', err);
    } finally {
      setLoadingCaseCustody(false);
    }
  };

  const loadCaseDiary = async (page = diaryPage) => {
    if (!caseId) return;
    setLoadingDiary(true);
    try {
      const skip = (page - 1) * diaryPageSize;
      const res = await diaryApi.getCaseDiary(caseId, {
        start_date: diaryStartDate || undefined,
        end_date: diaryEndDate || undefined,
        search: diarySearch || undefined,
        skip,
        limit: diaryPageSize,
        sort_order: diarySortOrder
      });
      setDiaryEntries(res.entries || []);
      setDiaryTotal(res.total || 0);
      setDiaryLegalNotice(res.legal_disclaimer || '');
    } catch (err) {
      console.error('Failed to reload investigation diary', err);
    } finally {
      setLoadingDiary(false);
    }
  };

  const handleAiParseCreate = async () => {
    if (!caseId || !createAiRawText.trim()) return;
    setCreateAiParsing(true);
    setCreateAiMessage(null);
    setDiaryFormError(null);
    try {
      const res: DiaryParseResponse = await diaryApi.aiParseDiaryNarrative(caseId, {
        raw_text: createAiRawText.trim(),
        investigation_date: createDiaryDate || undefined
      });

      if (res.investigation_date) setCreateDiaryDate(res.investigation_date);
      if (res.time_info_received) setCreateDiaryTimeReceived(res.time_info_received);
      if (res.start_time) setCreateDiaryStartTime(res.start_time);
      if (res.closing_time) setCreateDiaryClosingTime(res.closing_time);
      if (res.places_visited && res.places_visited.length > 0) {
        setCreateDiaryPlaces(res.places_visited.join(', '));
      }
      if (res.activities_performed) setCreateDiaryActivities(res.activities_performed);
      if (res.findings) setCreateDiaryFindings(res.findings);
      if (res.witness_references) setCreateDiaryWitness(res.witness_references);
      if (res.next_steps) setCreateDiaryNextSteps(res.next_steps);
      if (res.timeline_events) setCreateTimelineEvents(res.timeline_events);
      if (res.detected_language) setCreateDetectedLanguage(res.detected_language);

      setCreateAiMessage(`AI identified ${res.detected_language} (${res.ai_provider}). Extracted ${res.timeline_events?.length || 0} chronological timeline milestone(s) and structured all fields into court-admissible forensic English.`);
    } catch (err: any) {
      setDiaryFormError(err.response?.data?.detail || 'Failed to auto-parse narrative with AI.');
    } finally {
      setCreateAiParsing(false);
    }
  };

  const handleAiParseAmend = async () => {
    if (!caseId || !amendAiRawText.trim()) return;
    setAmendAiParsing(true);
    setAmendAiMessage(null);
    setAmendFormError(null);
    try {
      const res: DiaryParseResponse = await diaryApi.aiParseDiaryNarrative(caseId, {
        raw_text: amendAiRawText.trim(),
        investigation_date: amendDate || undefined
      });

      if (res.investigation_date) setAmendDate(res.investigation_date);
      if (res.time_info_received) setAmendTimeReceived(res.time_info_received);
      if (res.start_time) setAmendStartTime(res.start_time);
      if (res.closing_time) setAmendClosingTime(res.closing_time);
      if (res.places_visited && res.places_visited.length > 0) {
        setAmendPlaces(res.places_visited.join(', '));
      }
      if (res.activities_performed) setAmendActivities(res.activities_performed);
      if (res.findings) setAmendFindings(res.findings);
      if (res.witness_references) setAmendWitness(res.witness_references);
      if (res.next_steps) setAmendNextSteps(res.next_steps);
      if (res.timeline_events) setAmendTimelineEvents(res.timeline_events);
      if (res.detected_language) setAmendDetectedLanguage(res.detected_language);

      setAmendAiMessage(`AI identified ${res.detected_language} (${res.ai_provider}). Re-organized ${res.timeline_events?.length || 0} chronological milestones.`);
    } catch (err: any) {
      setAmendFormError(err.response?.data?.detail || 'Failed to auto-parse amendment narrative with AI.');
    } finally {
      setAmendAiParsing(false);
    }
  };

  const handleOpenAmendModal = (entry: DiaryEntry) => {
    setAmendingEntry(entry);
    setAmendReason('');
    setAmendDate(entry.investigation_date);
    setAmendTimeReceived(entry.time_info_received || '');
    setAmendStartTime(entry.start_time);
    setAmendClosingTime(entry.closing_time);
    setAmendPlaces((entry.places_visited || []).join(', '));
    setAmendActivities(entry.activities_performed);
    setAmendFindings(entry.findings);
    setAmendSelectedEvidence(entry.related_evidence_ids || []);
    setAmendWitness(entry.witness_references && !entry.is_witness_redacted ? entry.witness_references : '');
    setAmendNextSteps(entry.next_steps || '');
    setAmendTimelineEvents(entry.timeline_events || []);
    setAmendDetectedLanguage(entry.detected_language || '');
    setAmendAiRawText(entry.raw_input || '');
    setAmendAiMessage(null);
    setAmendFormError(null);
  };

  const handleCreateDiarySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId) return;
    setDiarySubmitting(true);
    setDiaryFormError(null);
    try {
      const placesArr = createDiaryPlaces
        .split(',')
        .map(p => p.trim())
        .filter(Boolean);

      await diaryApi.createDiaryEntry(caseId, {
        investigation_date: createDiaryDate,
        time_info_received: createDiaryTimeReceived.trim() || undefined,
        start_time: createDiaryStartTime.trim(),
        closing_time: createDiaryClosingTime.trim(),
        places_visited: placesArr,
        activities_performed: createDiaryActivities.trim(),
        findings: createDiaryFindings.trim(),
        related_evidence_ids: createDiarySelectedEvidence,
        witness_references: createDiaryWitness.trim() || undefined,
        next_steps: createDiaryNextSteps.trim() || undefined,
        timeline_events: createTimelineEvents.length > 0 ? createTimelineEvents : undefined,
        raw_input: createAiRawText.trim() || undefined,
        detected_language: createDetectedLanguage || undefined
      });

      setShowCreateDiaryModal(false);
      setCreateDiaryActivities('');
      setCreateDiaryFindings('');
      setCreateDiaryPlaces('');
      setCreateDiaryWitness('');
      setCreateDiaryNextSteps('');
      setCreateDiarySelectedEvidence([]);
      setCreateTimelineEvents([]);
      setCreateAiRawText('');
      setCreateAiMessage(null);
      setCreateDetectedLanguage('');
      await loadCaseDiary(1);
      setDiaryPage(1);
    } catch (err: any) {
      setDiaryFormError(err.response?.data?.detail || 'Failed to record investigation diary entry.');
    } finally {
      setDiarySubmitting(false);
    }
  };

  const handleAmendDiarySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !amendingEntry) return;
    if (!amendReason.trim() || amendReason.trim().length < 5) {
      setAmendFormError('A mandatory official reason (minimum 5 characters) is required to amend a finalized record.');
      return;
    }
    setAmendSubmitting(true);
    setAmendFormError(null);
    try {
      const placesArr = amendPlaces
        .split(',')
        .map(p => p.trim())
        .filter(Boolean);

      const updated = await diaryApi.amendDiaryEntry(caseId, amendingEntry._id, {
        reason: amendReason.trim(),
        investigation_date: amendDate !== amendingEntry.investigation_date ? amendDate : undefined,
        time_info_received: amendTimeReceived !== (amendingEntry.time_info_received || '') ? (amendTimeReceived.trim() || undefined) : undefined,
        start_time: amendStartTime !== amendingEntry.start_time ? amendStartTime.trim() : undefined,
        closing_time: amendClosingTime !== amendingEntry.closing_time ? amendClosingTime.trim() : undefined,
        places_visited: placesArr,
        activities_performed: amendActivities !== amendingEntry.activities_performed ? amendActivities.trim() : undefined,
        findings: amendFindings !== amendingEntry.findings ? amendFindings.trim() : undefined,
        related_evidence_ids: amendSelectedEvidence,
        witness_references: amendWitness !== (amendingEntry.witness_references || '') ? (amendWitness.trim() || undefined) : undefined,
        next_steps: amendNextSteps !== (amendingEntry.next_steps || '') ? (amendNextSteps.trim() || undefined) : undefined,
        timeline_events: amendTimelineEvents.length > 0 ? amendTimelineEvents : undefined,
        raw_input: amendAiRawText.trim() || undefined,
        detected_language: amendDetectedLanguage || undefined
      });

      setAmendingEntry(null);
      setDiaryEntries(prev => prev.map(item => item._id === updated._id ? updated : item));
    } catch (err: any) {
      setAmendFormError(err.response?.data?.detail || 'Failed to submit diary amendment.');
    } finally {
      setAmendSubmitting(false);
    }
  };

  const handleVerifyDiaryEntry = async (entryId: string) => {
    if (!caseId) return;
    setVerifyingDiaryId(entryId);
    try {
      const res = await diaryApi.verifyDiaryEntry(caseId, entryId);
      setDiaryVerifyStatus(prev => ({ ...prev, [entryId]: res }));
    } catch (err) {
      console.error('Failed to verify diary entry', err);
    } finally {
      setVerifyingDiaryId(null);
    }
  };

  useEffect(() => {
    fetchCaseDetails();
  }, [caseId]);

  // Guard all evidence and report actions with mandatory credential authentication
  const requireEvidenceAuth = (targetName: string, action: () => void) => {
    setAuthTargetName(targetName);
    setPendingAction(() => action);
    setAuthEmail(user?.email || 'admin@forensics.gov');
    setAuthPassword('');
    setAuthError(null);
    setAuthModalOpen(true);
  };

  // Download Report with mandatory authentication challenge
  const handleDownloadCaseReport = async () => {
    if (!caseId) return;
    setDownloadingReport(true);
    setReportSuccess(null);
    try {
      const res = await reportApi.generateCaseReport(caseId, {
        title: `Official Forensic Investigation Dossier - ${caseData?.case_number || 'Case'}`,
        classification: 'CONFIDENTIAL // LAW ENFORCEMENT SENSITIVE'
      });

      // Extract report ID and metadata from response
      const reportId = res?.report_id || res?._id || res?.report?.report_id || res?.report?._id;
      const reportVersion = res?.version || res?.report?.version || 1;
      const reportHash = res?.sha256_hash || res?.report?.sha256_hash || '';

      if (reportId) {
        // Download binary PDF blob directly via authenticated axios client
        const blobData = await reportApi.downloadReportBlob(reportId);
        const filename = `${caseData?.case_number || 'Case'}_Forensic_Report_v${reportVersion}.pdf`;

        const blob = new Blob([blobData], { type: 'application/pdf' });
        const blobUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1000);

        setRecentReportHash(reportHash || null);
        setReportSuccess(`Official Forensic Report v${reportVersion} compiled & downloaded! SHA-256 Seal: ${reportHash ? reportHash.substring(0, 16) + '...' : 'Verified'}`);
        setTimeout(() => setReportSuccess(null), 10000);
      } else {
        throw new Error('Report generated successfully, but the report identifier was not found in the response.');
      }
    } catch (err: any) {
      console.error('Error generating or downloading forensic report:', err);
      alert(err.response?.data?.detail || err.message || 'Failed to generate and download report.');
    } finally {
      setDownloadingReport(false);
    }
  };

  const requestReportDownload = () => {
    requireEvidenceAuth(
      `Judicial Forensic Case Dossier (Case: ${caseData?.case_number || 'Current'})`,
      handleDownloadCaseReport
    );
  };

  // Submit Evidence Access Authentication
  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authPassword.trim()) {
      setAuthError('Password is required');
      return;
    }
    setAuthSubmitting(true);
    setAuthError(null);
    try {
      const loginRes = await api.post('/auth/login', {
        email: authEmail.trim(),
        password: authPassword
      });
      if (loginRes.data?.access_token) {
        localStorage.setItem('forensic_token', loginRes.data.access_token);
      }
      // Mandatory Lock Policy: authenticate single action then maintain locked state
      setAuthModalOpen(false);
      if (pendingAction) {
        const actionToRun = pendingAction;
        setPendingAction(null);
        actionToRun();
      }
    } catch (err: any) {
      setAuthError(err.response?.data?.detail || 'Authentication failed. Incorrect password.');
    } finally {
      setAuthSubmitting(false);
    }
  };

  // Add Note to Case
  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !noteContent.trim()) return;

    setNoteSubmitting(true);
    try {
      const updatedCase = await caseApi.addCaseNote(caseId, noteContent.trim());
      setCaseData(updatedCase);
      setNoteContent('');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to record note.');
    } finally {
      setNoteSubmitting(false);
    }
  };

  // Upload Evidence File
  const handleUploadEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !uploadFile) return;

    setUploading(true);
    setUploadError(null);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('description', uploadDescription.trim());
      formData.append('source_device', 'ESP32_01');
      if (uploadTags.trim()) {
        formData.append('tags', uploadTags.trim());
      }

      await evidenceApi.uploadEvidence(caseId, formData);
      setUploadFile(null);
      setUploadDescription('');
      setUploadTags('');
      setShowUploadModal(false);
      fetchCaseDetails();
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Evidence ingestion failed.');
    } finally {
      setUploading(false);
    }
  };

  // Verify Evidence
  const handleVerifyEvidence = async (evidenceId: string) => {
    setVerifyingId(evidenceId);
    try {
      const result = await evidenceApi.verifyEvidence(evidenceId);
      setSelectedVerify(result);
      fetchCaseDetails();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Verification request failed.');
    } finally {
      setVerifyingId(null);
    }
  };

  // Open Custody Modal
  const handleOpenCustody = async (evidence: Evidence) => {
    setCustodyEvidence(evidence);
    setCustodyLoading(true);
    try {
      const res = await evidenceApi.getCustodyHistory(evidence._id);
      setCustodyEvents(res.custody_events || res.history || []);
    } catch (err) {
      console.error('Failed to load custody events', err);
    } finally {
      setCustodyLoading(false);
    }
  };

  const handleDownload = async (evidence: Evidence) => {
    try {
      const blobData = await evidenceApi.downloadEvidenceBlob(evidence._id);
      const blob = new Blob([blobData]);
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = evidence.original_filename || 'evidence_file.bin';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1000);
    } catch (err: any) {
      console.error('Evidence download failed, using fallback URL:', err);
      const downloadUrl = evidenceApi.getDownloadUrl(evidence._id);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = evidence.original_filename || 'evidence_file.bin';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(id);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const getActionBadgeClass = (action: string) => {
    const act = (action || '').toUpperCase();
    if (act.includes('TAMPER') || act.includes('FAIL')) {
      return 'ws-badge-red';
    }
    if (act.includes('VERIFIED') || act.includes('PASS')) {
      return 'ws-badge-green';
    }
    if (act.includes('INGEST') || act.includes('COLLECT')) {
      return 'ws-badge-amber';
    }
    if (act.includes('TRANSFER') || act.includes('HANDOFF')) {
      return 'ws-badge-blue';
    }
    return 'ws-badge-blue';
  };

  const filteredCaseCustody = caseCustodyEvents.filter((e: any) => {
    const actMatch = custodyActionFilter === 'ALL' || (e.action || '').toUpperCase() === custodyActionFilter.toUpperCase();
    if (!actMatch) return false;
    if (!custodySearch.trim()) return true;
    const q = custodySearch.toLowerCase().trim();
    return (
      (e.action || '').toLowerCase().includes(q) ||
      (e.actor_name || '').toLowerCase().includes(q) ||
      (e.details || '').toLowerCase().includes(q) ||
      (e.event_hash || '').toLowerCase().includes(q) ||
      (e.evidence_name || '').toLowerCase().includes(q) ||
      (e.device_id || '').toLowerCase().includes(q)
    );
  });

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-3 font-mono text-xs text-slate-500">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
        <span className="tracking-wider">LOADING CASE DETAILS...</span>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="ws-panel p-6 max-w-lg mx-auto text-center space-y-3">
        <AlertTriangle className="w-8 h-8 text-red-500 mx-auto" />
        <h2 className="text-sm font-bold text-slate-900 dark:text-[#E6EAF0]">Case Not Found</h2>
        <p className="text-xs text-slate-500 dark:text-[#8B96A3]">{error || 'The requested forensic case could not be located.'}</p>
        <Link to="/cases" className="ws-btn ws-btn-secondary inline-flex">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Return to Cases</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Top Breadcrumb & Case Master Header */}
      <div className="ws-panel p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-3">
          <div className="flex items-center gap-3">
            <Link
              to="/cases"
              className="p-1.5 rounded hover:bg-slate-100 text-slate-500 hover:text-slate-900 transition-colors"
              title="Return to Cases"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-mono text-sm font-bold text-blue-600">
                  {caseData.case_number}
                </span>
                <span className="text-slate-300">|</span>
                <h1 className="text-base font-bold text-slate-900">{caseData.title}</h1>
                <span className={`ws-badge ${
                  caseData.status === 'IN_PROGRESS' ? 'ws-badge-amber' :
                  caseData.status === 'CLOSED' ? 'ws-badge-green' : 'ws-badge-gray'
                }`}>
                  {caseData.status}
                </span>
                <span className={`ws-badge ${
                  caseData.priority === 'CRITICAL' ? 'ws-badge-red' :
                  caseData.priority === 'HIGH' ? 'ws-badge-amber' : 'ws-badge-blue'
                }`}>
                  {caseData.priority}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={requestReportDownload}
              disabled={downloadingReport}
              className="ws-btn ws-btn-amber !py-1.5 !text-xs inline-flex items-center gap-1.5 cursor-pointer font-bold shadow-xs active:scale-95 transition-transform"
              title="Authenticate and Download Official Court Report"
            >
              {downloadingReport ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Compiling Report...</span>
                </>
              ) : (
                <>
                  <FileDown className="w-3.5 h-3.5" />
                  <span>Download Court Report</span>
                  <Lock className="w-3 h-3 text-amber-200" />
                </>
              )}
            </button>

            <Link
              to={`/graph?caseId=${caseData._id}`}
              className="ws-btn ws-btn-secondary !py-1.5 !text-xs inline-flex items-center gap-1.5 cursor-pointer font-semibold"
              title="Explore Relational Topology Graph for this Case"
            >
              <Network className="w-3.5 h-3.5 text-blue-600" />
              <span>Explore Graph</span>
            </Link>
          </div>
        </div>

        {/* Case Metadata Summary Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono text-slate-500">
          <div>
            <span className="text-slate-400 block text-[10px] font-bold">CASE CLASSIFICATION</span>
            <span className="text-slate-900 font-semibold">{caseData.case_type?.replace(/_/g, ' ')}</span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px] font-bold">LEAD INVESTIGATOR</span>
            <span className="text-slate-900">{caseData.assigned_investigator_name || 'Unassigned'}</span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px] font-bold">LAST MODIFIED (UTC)</span>
            <span className="text-slate-900">
              {caseData.updated_at ? new Date(caseData.updated_at).toISOString().replace('T', ' ').substring(0, 16) : 'N/A'}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px] font-bold">REGISTERED (UTC)</span>
            <span className="text-slate-900">
              {new Date(caseData.created_at).toISOString().replace('T', ' ').substring(0, 16)}
            </span>
          </div>
        </div>
      </div>

      {/* Report Success Toast */}
      {reportSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-mono text-emerald-800 flex items-center justify-between shadow-2xs animate-fade-in-up">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{reportSuccess}</span>
          </div>
          {recentReportHash && (
            <span className="hidden sm:inline text-[10px] text-emerald-700 bg-white px-2 py-0.5 rounded border border-emerald-200 font-bold">
              SHA-256 SEAL VERIFIED
            </span>
          )}
        </div>
      )}

      {/* Structured Forensic Workstation Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-200 text-xs font-medium font-mono select-none bg-white px-2 rounded-t-md">
        {[
          { id: 'overview' as const, label: 'Overview of the Case', icon: FolderLock },
          { id: 'evidence' as const, label: `Evidence Vault (${evidenceList.length})`, icon: FileCheck },
          { id: 'custody' as const, label: `Chain of Custody (${caseCustodyEvents.length})`, icon: History },
          { id: 'diary' as const, label: `Investigation Diary (${diaryTotal})`, icon: BookOpen },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 border-b-2 transition-all cursor-pointer ${
                isActive
                  ? 'border-blue-600 text-blue-600 bg-blue-50/70 font-bold'
                  : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-100 font-medium'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: OVERVIEW OF THE CASE (Comprehensive Case Details - No Evidence) */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          {/* Complete Case Details Specification Panel */}
          <div className="ws-panel p-5 space-y-4 bg-white border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-blue-600" />
                <h2 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wider">
                  Case Details & Parameters
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <span className={`ws-badge ${
                  caseData.status === 'IN_PROGRESS' ? 'ws-badge-amber' :
                  caseData.status === 'CLOSED' ? 'ws-badge-green' : 'ws-badge-gray'
                }`}>
                  Status: {caseData.status}
                </span>
                <span className={`ws-badge ${
                  caseData.priority === 'CRITICAL' ? 'ws-badge-red' :
                  caseData.priority === 'HIGH' ? 'ws-badge-amber' : 'ws-badge-blue'
                }`}>
                  Priority: {caseData.priority}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 text-xs font-mono">
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 shadow-2xs">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Official Case Number</span>
                <span className="font-bold text-blue-600 text-sm">{caseData.case_number}</span>
              </div>
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 shadow-2xs">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Case Title</span>
                <span className="font-semibold text-slate-900">{caseData.title}</span>
              </div>
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 shadow-2xs">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Incident Classification</span>
                <span className="font-semibold text-slate-900">{caseData.case_type?.replace(/_/g, ' ')}</span>
              </div>
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 shadow-2xs">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Lead Assigned Investigator</span>
                <span className="text-slate-900 font-medium">{caseData.assigned_investigator_name || 'Unassigned'}</span>
              </div>
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 shadow-2xs">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Internal Reference ID</span>
                <span className="text-slate-700 font-mono select-all break-all">{caseData._id}</span>
              </div>
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 shadow-2xs">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Registration Date (UTC)</span>
                <span className="text-slate-800">
                  {new Date(caseData.created_at).toISOString().replace('T', ' ').substring(0, 19)}
                </span>
              </div>
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 shadow-2xs">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Last Modified (UTC)</span>
                <span className="text-slate-800">
                  {caseData.updated_at ? new Date(caseData.updated_at).toISOString().replace('T', ' ').substring(0, 19) : 'N/A'}
                </span>
              </div>
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 shadow-2xs">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Closure Status</span>
                <span className="text-slate-800">
                  {caseData.closed_at ? `Closed on ${new Date(caseData.closed_at).toLocaleDateString()}` : 'Active Ongoing Investigation'}
                </span>
              </div>
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 shadow-2xs">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Created By</span>
                <span className="text-slate-800">
                  {caseData.created_by_name || caseData.created_by || 'System Admin'}
                </span>
              </div>
            </div>

            {/* Scope / Description */}
            <div className="pt-3 border-t border-slate-200 space-y-1.5">
              <span className="text-[10px] font-bold text-slate-500 uppercase font-mono tracking-wider block">
                Forensic Case Scope & Overview Description
              </span>
              <p className="text-xs text-slate-800 leading-relaxed font-sans whitespace-pre-wrap bg-slate-50 p-3.5 rounded-lg border border-slate-200 shadow-2xs">
                {caseData.description || 'No detailed scope description recorded for this investigation.'}
              </p>
            </div>

            {/* Tags */}
            {caseData.tags && caseData.tags.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap pt-2">
                <Tag className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-[10px] text-slate-500 font-mono">Tags:</span>
                {caseData.tags.map((t, idx) => (
                  <span key={idx} className="ws-badge ws-badge-gray text-[10px]">
                    {t}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Official Judicial Forensic Report Card */}
          <div className="ws-panel p-5 space-y-3.5 bg-gradient-to-r from-white via-amber-50/25 to-white border border-amber-200/90 shadow-xs rounded-xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-amber-100">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shrink-0">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wider">
                    Official Judicial Forensic Dossier (PDF Export)
                  </h3>
                  <p className="text-[11px] text-slate-500 font-sans">
                    Court-admissible PDF compiling evidence exhibits, baseline SHA-256 hashes, and chain of custody with exact UTC timestamps.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-mono font-bold shadow-2xs">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Judicial Dossier Ready</span>
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
              <div className="p-3 rounded-lg bg-white border border-slate-200">
                <span className="text-slate-400 block text-[10px] font-bold">DIGITAL EVIDENCE EXHIBITS</span>
                <span className="font-bold text-slate-800">{evidenceList.length} Exhibits (SHA-256 Sealed)</span>
              </div>
              <div className="p-3 rounded-lg bg-white border border-slate-200">
                <span className="text-slate-400 block text-[10px] font-bold">CHAIN OF CUSTODY LOG</span>
                <span className="font-bold text-slate-800">{caseCustodyEvents.length} Events (Timestamped UTC)</span>
              </div>
              <div className="p-3 rounded-lg bg-white border border-slate-200">
                <span className="text-slate-400 block text-[10px] font-bold">EXPORT ACCESS SECURITY</span>
                <span className="font-bold text-amber-700 flex items-center gap-1">
                  <Lock className="w-3 h-3 text-amber-600" />
                  <span>Mandatory Password Verification</span>
                </span>
              </div>
            </div>
          </div>

          {/* Notes Ledger */}
          <div className="ws-panel p-4 space-y-3 bg-white border border-slate-200 shadow-xs">
            <h3 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wider">
              Investigator Notes Ledger
            </h3>

            <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
              {!caseData.notes || caseData.notes.length === 0 ? (
                <p className="text-xs text-slate-400 italic py-2">
                  No notes recorded yet. Add observations below.
                </p>
              ) : (
                caseData.notes.map((note, idx) => (
                  <div key={idx} className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1 text-xs shadow-2xs">
                    <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
                      <span className="font-semibold text-slate-700">{note.author_name || note.author || 'Investigator'}</span>
                      <span>{note.timestamp || note.created_at ? new Date(note.timestamp || note.created_at!).toLocaleString() : ''}</span>
                    </div>
                    <p className="text-slate-800 font-sans leading-relaxed whitespace-pre-wrap">
                      {note.content}
                    </p>
                  </div>
                ))
              )}
            </div>

            {!isReadOnly && (
              <form onSubmit={handleAddNote} className="space-y-2 pt-2 border-t border-slate-200">
                <textarea
                  value={noteContent}
                  onChange={e => setNoteContent(e.target.value)}
                  placeholder="Record an evidentiary observation, witness statement, or investigative note..."
                  rows={3}
                  className="ws-input w-full font-sans text-xs"
                />
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={noteSubmitting || !noteContent.trim()}
                    className="ws-btn ws-btn-secondary text-xs flex items-center gap-1.5"
                  >
                    <Send className="w-3 h-3 text-blue-500" />
                    <span>{noteSubmitting ? 'Recording...' : 'Add Note'}</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: EVIDENCE VAULT */}
      {activeTab === 'evidence' && (
        <div className="space-y-4">
          <div className="ws-panel p-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-blue-500" />
              <span className="text-xs font-bold text-slate-900 dark:text-[#E6EAF0] uppercase font-mono">
                Preserved Evidence Artifacts ({evidenceList.length})
              </span>
              <span className="ws-badge ws-badge-amber text-[10px] flex items-center gap-1 font-mono">
                <Lock className="w-3 h-3 text-amber-500" />
                <span>Access Locked • Mandatory Authentication</span>
              </span>
            </div>

            <div className="flex items-center gap-2">

              {!isReadOnly && (
                <button
                  onClick={() => requireEvidenceAuth("Add New Evidence Exhibit", () => setShowUploadModal(true))}
                  className="ws-btn ws-btn-amber text-xs flex items-center gap-1.5"
                >
                  <Upload className="w-3.5 h-3.5" />
                  <span>Ingest New Exhibit</span>
                </button>
              )}
            </div>
          </div>

          <div className="ws-panel overflow-hidden">
            <table className="ws-table">
              <thead>
                <tr>
                  <th>Exhibit Filename</th>
                  <th>Size</th>
                  <th>MIME Type</th>
                  <th>SHA-256 Digest</th>
                  <th>Integrity</th>
                  <th>Terminal</th>
                  <th className="text-right">Verification & Actions</th>
                </tr>
              </thead>
              <tbody>
                {evidenceList.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-10 text-slate-500">
                      No evidence artifacts deposited for this case.
                    </td>
                  </tr>
                ) : (
                  evidenceList.map(ev => (
                    <tr
                      key={ev._id}
                      onClick={() => requireEvidenceAuth(`View Exhibit: ${ev.original_filename}`, () => setInspectEvidence(ev))}
                      className="cursor-pointer hover:bg-slate-50 transition-colors"
                    >
                      <td className="font-semibold text-xs text-slate-900">
                        <div className="flex items-center gap-2">
                          <FileCheck className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                          <span className="hover:underline">{ev.original_filename}</span>
                        </div>
                      </td>
                      <td className="font-mono text-xs text-slate-600">
                        {(ev.file_size / 1024).toFixed(1)} KB
                      </td>
                      <td className="font-mono text-xs text-slate-600">
                        {ev.mime_type}
                      </td>
                      <td onClick={e => e.stopPropagation()}>
                        <div className="flex items-center gap-1.5 font-mono text-[10px] text-blue-600">
                          <span>{ev.sha256_hash?.substring(0, 16)}…</span>
                          <button
                            onClick={() => handleCopy(ev.sha256_hash, ev._id)}
                            className="text-slate-400 hover:text-slate-700"
                            title="Copy full SHA-256"
                          >
                            {copiedHash === ev._id ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3 text-slate-400" />}
                          </button>
                        </div>
                      </td>
                      <td>
                        <span className={`ws-badge ${
                          ev.integrity_status === 'VERIFIED' ? 'ws-badge-green' : 'ws-badge-red'
                        }`}>
                          {ev.integrity_status}
                        </span>
                      </td>
                      <td className="font-mono text-xs text-slate-600">
                        {ev.source_device || 'WORKSTATION'}
                      </td>
                      <td className="text-right whitespace-nowrap" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => requireEvidenceAuth(`Verify Exhibit: ${ev.original_filename}`, () => handleVerifyEvidence(ev._id))}
                            disabled={verifyingId === ev._id}
                            className="ws-btn ws-btn-secondary !py-1 !px-2 !text-[11px]"
                            title="Recalculate SHA-256 integrity (Requires Login)"
                          >
                            <RefreshCw className={`w-3 h-3 ${verifyingId === ev._id ? 'animate-spin' : ''}`} />
                            <span>Verify</span>
                          </button>

                          <button
                            onClick={() => requireEvidenceAuth(`Custody History: ${ev.original_filename}`, () => handleOpenCustody(ev))}
                            className="ws-btn ws-btn-secondary !py-1 !px-2 !text-[11px]"
                            title="View Chain of Custody History (Requires Login)"
                          >
                            <History className="w-3 h-3" />
                            <span>Custody</span>
                          </button>

                          <button
                            onClick={() => requireEvidenceAuth(`Download Exhibit: ${ev.original_filename}`, () => handleDownload(ev))}
                            className="ws-btn ws-btn-secondary !py-1 !px-2 !text-[11px]"
                            title="Download Evidence Copy (Requires Login)"
                          >
                            <Download className="w-3 h-3 text-blue-500" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: CHAIN OF CUSTODY */}
      {activeTab === 'custody' && (
        <div className="space-y-4">
          {/* Header & Controls Panel */}
          <div className="ws-panel p-3.5 flex flex-wrap items-center justify-between gap-3 bg-white border border-slate-200 shadow-xs">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-bold text-slate-900 uppercase font-mono">
                Chain of Custody Ledger ({filteredCaseCustody.length})
              </span>
              <span className="ws-badge ws-badge-green text-[10px] flex items-center gap-1 font-mono">
                <ShieldCheck className="w-3 h-3 text-emerald-600" />
                <span>ISO/IEC 27037 Continuity</span>
              </span>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  placeholder="Filter events, actors, hashes..."
                  value={custodySearch}
                  onChange={e => setCustodySearch(e.target.value)}
                  className="ws-input pl-8 w-52 text-xs"
                />
              </div>

              <select
                value={custodyActionFilter}
                onChange={e => setCustodyActionFilter(e.target.value)}
                className="ws-select text-xs"
              >
                <option value="ALL">All Custody Actions</option>
                <option value="EVIDENCE_INGESTION">Ingestion & Preservation</option>
                <option value="VERIFICATION_PASSED">Verification (Passed)</option>
                <option value="EVIDENCE_HANDOFF">Evidence Handoff / Transfer</option>
                <option value="EVIDENCE_DOWNLOAD">Authorized Download</option>
                <option value="EVIDENCE_INTEGRITY_FAILURE">Integrity Anomalies</option>
              </select>

              <button
                onClick={loadCaseCustody}
                disabled={loadingCaseCustody}
                className="ws-btn ws-btn-secondary !p-1.5 cursor-pointer"
                title="Reload Custody Ledger"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-slate-600 ${loadingCaseCustody ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* Compliance & Verification Metrics Strip */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="ws-panel p-3.5 font-mono space-y-1 bg-white border border-slate-200 shadow-xs">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Custodial Block Count</div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-slate-900">{caseCustodyEvents.length}</span>
                <span className="text-[11px] text-blue-600 font-bold">SEALED BLOCKS</span>
              </div>
              <p className="text-[11px] text-slate-500 font-sans">Tamper-evident chain of handoffs</p>
            </div>

            <div className="ws-panel p-3.5 font-mono space-y-1 bg-white border border-slate-200 shadow-xs">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Digest Standard</div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-slate-900">FIPS 180-4</span>
                <span className="text-[11px] text-emerald-600 font-bold">SHA-256</span>
              </div>
              <p className="text-[11px] text-slate-500 font-sans">Cryptographic integrity proof</p>
            </div>

            <div className="ws-panel p-3.5 font-mono space-y-1 bg-white border border-slate-200 shadow-xs">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Admissibility Standard</div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-slate-900">ISO/IEC 27037</span>
              </div>
              <p className="text-[11px] text-slate-500 font-sans">Digital evidence handling & preservation</p>
            </div>
          </div>

          {/* Master Custody Ledger Table */}
          <div className="ws-panel overflow-hidden bg-white border border-slate-200 shadow-xs">
            <div className="overflow-x-auto">
              <table className="ws-table">
                <thead>
                  <tr>
                    <th>Timestamp (UTC)</th>
                    <th>Custodial Action</th>
                    <th>Associated Exhibit</th>
                    <th>Custodian / Operator</th>
                    <th>Operational Narrative</th>
                    <th>Block Hash Seal</th>
                    <th>Terminal Node</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCaseCustody.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center py-12 text-slate-400 font-mono text-xs">
                        {loadingCaseCustody ? (
                          <div className="flex flex-col items-center justify-center space-y-2">
                            <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
                            <span>Querying custody ledger...</span>
                          </div>
                        ) : (
                          <div className="space-y-1 py-4">
                            <History className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                            <p className="font-semibold text-slate-700">No Custody Entries Recorded</p>
                            <p className="text-slate-400 text-[11px]">
                              Ingesting, verifying, or downloading exhibits automatically generates tamper-evident custody entries.
                            </p>
                          </div>
                        )}
                      </td>
                    </tr>
                  ) : (
                    filteredCaseCustody.map((evt: any) => (
                      <tr key={evt._id || evt.event_id}>
                        <td className="text-slate-500 whitespace-nowrap text-[11px] font-mono">
                          {evt.timestamp ? new Date(evt.timestamp).toISOString().replace('T', ' ').substring(0, 19) + ' UTC' : 'N/A'}
                        </td>
                        <td className="whitespace-nowrap">
                          <span className={`ws-badge ${getActionBadgeClass(evt.action)} text-[10px]`}>
                            {evt.action}
                          </span>
                        </td>
                        <td className="font-semibold text-slate-900 whitespace-nowrap text-xs">
                          {evt.evidence_name || 'Case Exhibit'}
                        </td>
                        <td className="whitespace-nowrap text-xs">
                          <div className="flex items-center gap-1.5 text-slate-800">
                            <UserIcon className="w-3 h-3 text-slate-400" />
                            <span>{evt.actor_name || evt.custodian || 'Investigator'}</span>
                          </div>
                        </td>
                        <td className="text-slate-600 max-w-xs text-xs truncate" title={evt.details || evt.notes}>
                          {evt.details || evt.notes || 'Recorded in chain of custody'}
                        </td>
                        <td className="whitespace-nowrap">
                          <div className="flex items-center gap-1.5">
                            <GitCommit className="w-3 h-3 text-slate-400" />
                            <span
                              className="text-[11px] font-mono text-blue-700 bg-slate-50 border border-slate-200 px-1.5 py-0.5 rounded truncate max-w-[120px]"
                              title={evt.event_hash}
                            >
                              {evt.event_hash ? evt.event_hash.slice(0, 14) + '...' : 'GENESIS_BLOCK'}
                            </span>
                            {evt.event_hash && (
                              <button
                                onClick={() => handleCopy(evt.event_hash, evt._id || evt.event_id)}
                                className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-700 cursor-pointer"
                                title="Copy Cryptographic Event Hash"
                              >
                                {copiedHash === (evt._id || evt.event_id) ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                                ) : (
                                  <Copy className="w-3.5 h-3.5" />
                                )}
                              </button>
                            )}
                          </div>
                        </td>
                        <td className="whitespace-nowrap text-slate-500 text-xs font-mono">
                          <span className="flex items-center gap-1">
                            <Cpu className="w-3 h-3 text-slate-400" />
                            <span>{evt.device_id || 'NODE-SEC-01'}</span>
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: INVESTIGATION DIARY (BNSS SECTION 192 INFORMED) */}
      {activeTab === 'diary' && (
        <div className="space-y-4">
          {/* Statutory BNSS Header & Action Card */}
          <div className="ws-panel p-5 bg-gradient-to-r from-[#0B1B3D] to-[#152a57] text-white border border-[#1e3a75] shadow-md rounded-lg">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1.5 max-w-3xl">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono text-[10px] font-bold tracking-wider uppercase">
                    BNSS Sec. 192 Informed
                  </span>
                  <span className="text-slate-400 text-xs">|</span>
                  <span className="font-mono text-xs text-slate-300">
                    Case: <strong className="text-white">{caseData.case_number}</strong>
                  </span>
                  <span className="text-slate-400 text-xs">|</span>
                  <span className="font-mono text-xs text-amber-300">
                    {diaryTotal} Finalized Proceeding(s)
                  </span>
                </div>
                <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-amber-400 shrink-0" />
                  <span>Digital Investigation Case Diary</span>
                </h2>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Pursuant to Section 192 of the Bharatiya Nagarik Suraksha Sanhita, 2023, the investigating officer
                  records day-by-day proceedings, times, places visited, and ascertained circumstances. Each entry is
                  cryptographically secured with SHA-256 hash chaining. Finalized records cannot be deleted; amendments
                  are permanently audited.
                </p>
              </div>

              <div className="flex items-center gap-2.5 shrink-0">
                <button
                  onClick={() => setShowCreateDiaryModal(true)}
                  disabled={isReadOnly}
                  className={`ws-btn !py-2 !px-3.5 !text-xs font-bold inline-flex items-center gap-1.5 shadow-sm transition-all ${
                    isReadOnly
                      ? 'bg-slate-700 text-slate-400 border border-slate-600 cursor-not-allowed opacity-60'
                      : 'bg-[#B8860B] hover:bg-[#996f08] active:bg-[#7d5b06] text-white border border-amber-600 cursor-pointer'
                  }`}
                  title={isReadOnly ? 'Read-only accounts cannot record diary entries' : 'Record a new daily investigation diary entry'}
                >
                  <Plus className="w-4 h-4" />
                  <span>Record Diary Entry</span>
                </button>
              </div>
            </div>

            {/* Legal Notice Footer */}
            <div className="mt-3.5 pt-3 border-t border-white/10 flex items-start gap-2 text-[11px] text-slate-400 font-mono">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
              <span>
                {diaryLegalNotice ||
                  'Digital Diary Record maintained pursuant to BNSS Section 192 principles. Evidentiary admissibility and statutory presentation remain subject to applicable police procedural rules and judicial directives.'}
              </span>
            </div>
          </div>

          {/* Filtering and Search Toolbar */}
          <div className="ws-panel p-3.5 bg-white border border-slate-200 rounded-lg flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-2.5 flex-1">
              {/* Search */}
              <div className="relative min-w-[200px] flex-1 max-w-sm">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={diarySearch}
                  onChange={e => {
                    setDiarySearch(e.target.value);
                    setDiaryPage(1);
                  }}
                  placeholder="Search activities, findings, places, entry code..."
                  className="ws-input w-full !pl-8 !py-1.5 !text-xs"
                />
                {diarySearch && (
                  <button
                    onClick={() => {
                      setDiarySearch('');
                      setDiaryPage(1);
                    }}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>

              {/* Start Date */}
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-slate-500 font-medium">From:</span>
                <input
                  type="date"
                  value={diaryStartDate}
                  onChange={e => {
                    setDiaryStartDate(e.target.value);
                    setDiaryPage(1);
                  }}
                  className="ws-input !py-1 !px-2 !text-xs font-mono"
                />
              </div>

              {/* End Date */}
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-slate-500 font-medium">To:</span>
                <input
                  type="date"
                  value={diaryEndDate}
                  onChange={e => {
                    setDiaryEndDate(e.target.value);
                    setDiaryPage(1);
                  }}
                  className="ws-input !py-1 !px-2 !text-xs font-mono"
                />
              </div>

              {/* Sort Order Toggle */}
              <button
                type="button"
                onClick={() => {
                  setDiarySortOrder(prev => (prev === 1 ? -1 : 1));
                  setDiaryPage(1);
                }}
                className="ws-btn ws-btn-secondary !py-1.5 !px-2.5 !text-xs inline-flex items-center gap-1 cursor-pointer font-mono"
                title="Toggle Chronological / Reverse Chronological sorting"
              >
                <span>{diarySortOrder === 1 ? 'Oldest First' : 'Newest First'}</span>
              </button>

              {(diarySearch || diaryStartDate || diaryEndDate) && (
                <button
                  type="button"
                  onClick={() => {
                    setDiarySearch('');
                    setDiaryStartDate('');
                    setDiaryEndDate('');
                    setDiaryPage(1);
                  }}
                  className="text-xs text-blue-600 hover:text-blue-800 font-medium cursor-pointer underline"
                >
                  Clear Filters
                </button>
              )}
            </div>

            <div className="flex items-center gap-2 text-slate-500 font-mono text-[11px]">
              <button
                onClick={() => loadCaseDiary(diaryPage)}
                disabled={loadingDiary}
                className="ws-btn ws-btn-secondary !py-1.5 !px-2.5 !text-xs inline-flex items-center gap-1 cursor-pointer"
                title="Refresh Diary Entries"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingDiary ? 'animate-spin text-blue-600' : ''}`} />
                <span>Refresh</span>
              </button>
            </div>
          </div>

          {/* Entries Container */}
          {loadingDiary ? (
            <div className="flex flex-col items-center justify-center p-12 bg-white rounded-lg border border-slate-200 text-xs font-mono text-slate-500 space-y-2">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
              <span>FETCHING INVESTIGATION DIARY LEDGER...</span>
            </div>
          ) : diaryEntries.length === 0 ? (
            <div className="ws-panel p-8 text-center bg-white border border-slate-200 rounded-lg space-y-3">
              <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                <BookOpen className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-bold text-slate-800">No Investigation Diary Entries Recorded</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                {diarySearch || diaryStartDate || diaryEndDate
                  ? 'No diary proceedings match your current search or date filters.'
                  : 'Start recording daily proceedings, visited places, and ascertained circumstances for this case container.'}
              </p>
              {!isReadOnly && !diarySearch && !diaryStartDate && !diaryEndDate && (
                <button
                  onClick={() => setShowCreateDiaryModal(true)}
                  className="ws-btn ws-btn-primary !py-1.5 !px-3 !text-xs inline-flex items-center gap-1.5 mx-auto cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Record First Entry</span>
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {diaryEntries.map((entry) => {
                const verifyObj = diaryVerifyStatus[entry._id];
                const isVerifying = verifyingDiaryId === entry._id;

                return (
                  <div
                    key={entry._id}
                    className="ws-panel p-4 bg-white border border-slate-200 hover:border-slate-300 rounded-lg shadow-2xs space-y-3.5 transition-all"
                  >
                    {/* Top Row: Entry Identity, Status, Date, Hours, Actions */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-slate-100">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2.5 py-1 rounded bg-[#0B1B3D] text-amber-300 font-mono text-xs font-bold tracking-wider">
                          {entry.entry_code}
                        </span>

                        <span
                          className={`ws-badge ${
                            entry.is_amended
                              ? 'bg-amber-50 text-amber-700 border-amber-300'
                              : 'bg-emerald-50 text-emerald-700 border-emerald-300'
                          }`}
                        >
                          {entry.is_amended ? `AMENDED (${entry.amendments?.length || 1})` : 'FINALIZED RECORD'}
                        </span>

                        <div className="flex items-center gap-1 text-slate-600 text-xs font-mono bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                          <Calendar className="w-3.5 h-3.5 text-slate-500" />
                          <span>{entry.investigation_date}</span>
                        </div>

                        <div className="flex items-center gap-1 text-slate-600 text-xs font-mono bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                          <Clock className="w-3.5 h-3.5 text-slate-500" />
                          <span>
                            {entry.start_time} - {entry.closing_time}
                          </span>
                        </div>

                        {entry.detected_language && (
                          <div className="flex items-center gap-1 text-violet-700 bg-violet-50 px-2 py-0.5 rounded border border-violet-200 text-[10px] font-mono font-bold">
                            <Sparkles className="w-3 h-3 text-violet-600" />
                            <span>AI: {entry.detected_language}</span>
                          </div>
                        )}

                        {entry.time_info_received && (
                          <div className="flex items-center gap-1 text-slate-500 text-[11px] font-mono">
                            <span>(Info Recv: {entry.time_info_received})</span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {entry.is_amended && (
                          <button
                            type="button"
                            onClick={() => setHistoryEntry(entry)}
                            className="ws-btn ws-btn-secondary !py-1 !px-2.5 !text-xs inline-flex items-center gap-1 cursor-pointer font-mono text-amber-800 bg-amber-50/60 border-amber-200 hover:bg-amber-100"
                            title="View versioned amendment audit trail"
                          >
                            <History className="w-3.5 h-3.5 text-amber-600" />
                            <span>Audit Trail ({entry.amendments?.length || 0})</span>
                          </button>
                        )}

                        <button
                          type="button"
                          onClick={() => handleOpenAmendModal(entry)}
                          disabled={isReadOnly}
                          className={`ws-btn ws-btn-secondary !py-1 !px-2.5 !text-xs inline-flex items-center gap-1 cursor-pointer font-medium ${
                            isReadOnly ? 'opacity-50 cursor-not-allowed' : 'hover:bg-slate-100'
                          }`}
                          title={isReadOnly ? 'Read-only accounts cannot amend entries' : 'Amend this finalized diary entry with recorded justification'}
                        >
                          <FileEdit className="w-3.5 h-3.5 text-slate-600" />
                          <span>Amend Entry</span>
                        </button>
                      </div>
                    </div>

                    {/* Places Visited */}
                    {entry.places_visited && entry.places_visited.length > 0 && (
                      <div className="flex items-center gap-2 flex-wrap text-xs">
                        <span className="text-[11px] font-semibold font-mono text-slate-500 uppercase flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5 text-rose-500" />
                          <span>Places Visited:</span>
                        </span>
                        {entry.places_visited.map((p, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center px-2 py-0.5 rounded-full bg-slate-100 text-slate-800 text-xs border border-slate-200"
                          >
                            {p}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Chronological Event Timeline Sequence (AI Organized Milestones) */}
                    {entry.timeline_events && entry.timeline_events.length > 0 && (
                      <div className="p-3 rounded-lg bg-gradient-to-r from-slate-50 via-indigo-50/25 to-blue-50/30 border border-indigo-100 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 font-bold font-mono text-[11px] text-indigo-950 uppercase tracking-wider">
                            <ListOrdered className="w-4 h-4 text-indigo-600" />
                            <span>Chronological Event Timeline Sequence</span>
                            <span className="px-1.5 py-0.2 rounded bg-indigo-100 text-indigo-700 text-[10px] font-bold">
                              {entry.timeline_events.length} Milestones
                            </span>
                          </div>
                          <button
                            type="button"
                            onClick={() => setExpandedTimelineMap(prev => ({ ...prev, [entry._id]: prev[entry._id] === false ? true : false }))}
                            className="text-[11px] text-indigo-600 hover:text-indigo-800 font-mono font-semibold cursor-pointer underline"
                          >
                            {expandedTimelineMap[entry._id] === false ? 'Expand Timeline' : 'Collapse Timeline'}
                          </button>
                        </div>

                        {expandedTimelineMap[entry._id] !== false && (
                          <div className="space-y-1.5 pt-1">
                            {entry.timeline_events.map((ev, tIdx) => (
                              <div key={tIdx} className="flex items-start gap-2.5 p-2 rounded-md bg-white border border-slate-200 text-xs shadow-2xs">
                                <span className="px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 font-mono font-bold text-[11px] shrink-0 border border-indigo-100">
                                  {ev.time || '--:--'}
                                </span>
                                <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[10px] shrink-0 border border-slate-200">
                                  {ev.location || 'Field'}
                                </span>
                                <span className="text-slate-800 font-sans leading-relaxed text-xs">
                                  {ev.activity}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Main Content Grid: Activities Performed & Circumstances Discovered */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                      {/* Activities */}
                      <div className="p-3 rounded-md bg-slate-50/70 border border-slate-200 space-y-1">
                        <div className="text-[11px] font-bold font-mono text-slate-700 uppercase tracking-wider">
                          Proceedings & Investigation Activities (BNSS Sec. 192)
                        </div>
                        <p className="text-xs text-slate-800 whitespace-pre-wrap leading-relaxed font-sans">
                          {entry.activities_performed}
                        </p>
                      </div>

                      {/* Findings */}
                      <div className="p-3 rounded-md bg-blue-50/40 border border-blue-100 space-y-1">
                        <div className="text-[11px] font-bold font-mono text-blue-900 uppercase tracking-wider">
                          Ascertained Circumstances & Findings Discovered
                        </div>
                        <p className="text-xs text-slate-800 whitespace-pre-wrap leading-relaxed font-sans">
                          {entry.findings}
                        </p>
                      </div>
                    </div>

                    {/* Linked Evidence Exhibits */}
                    {entry.related_evidence_ids && entry.related_evidence_ids.length > 0 && (
                      <div className="flex items-center gap-2 flex-wrap text-xs pt-1">
                        <span className="text-[11px] font-semibold font-mono text-slate-500 uppercase flex items-center gap-1">
                          <FileCheck className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Related Exhibits:</span>
                        </span>
                        {entry.related_evidence_ids.map((eid, idx) => {
                          const evMatch = evidenceList.find(e => e._id === eid || e._id.endsWith(eid));
                          return (
                            <span
                              key={idx}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 font-mono text-xs border border-emerald-200"
                              title={`Exhibit ID: ${eid}`}
                            >
                              <span>{evMatch ? evMatch.original_filename : `Exhibit #${eid.slice(-8)}`}</span>
                            </span>
                          );
                        })}
                      </div>
                    )}

                    {/* Witness References (Confidential BNSS Sec. 192(3)) */}
                    {entry.witness_references && (
                      <div
                        className={`p-3 rounded-md text-xs space-y-1 ${
                          entry.is_witness_redacted
                            ? 'bg-slate-100 border border-slate-300 text-slate-600'
                            : 'bg-amber-50/60 border border-amber-200 text-amber-950'
                        }`}
                      >
                        <div className="flex items-center gap-1.5 font-bold font-mono text-[11px] text-amber-800 uppercase tracking-wider">
                          <Lock className="w-3.5 h-3.5 text-amber-600" />
                          <span>Witness-Related References (Confidential under BNSS Sec. 192(3))</span>
                        </div>
                        <p className="text-xs whitespace-pre-wrap leading-relaxed font-sans">
                          {entry.witness_references}
                        </p>
                      </div>
                    )}

                    {/* Next Steps / Remarks */}
                    {entry.next_steps && (
                      <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-xs space-y-0.5">
                        <div className="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-wider">
                          Next Steps & Procedural Remarks
                        </div>
                        <p className="text-xs text-slate-700 leading-relaxed font-sans">{entry.next_steps}</p>
                      </div>
                    )}

                    {/* Original Raw Notes / Tanglish Source (if saved) */}
                    {entry.raw_input && (
                      <details className="text-[11px] font-mono text-slate-500 bg-slate-50 p-2 rounded border border-slate-200 cursor-pointer">
                        <summary className="font-semibold text-slate-600 hover:text-slate-900 select-none">
                          View Original Input / Field Notes ({entry.detected_language || 'Raw Notes'})
                        </summary>
                        <p className="mt-1.5 p-2 rounded bg-white text-slate-700 font-mono text-[11px] whitespace-pre-wrap border border-slate-100">
                          {entry.raw_input}
                        </p>
                      </details>
                    )}

                    {/* Footer: Investigator ID, Timestamps, Hash Seal, Verification Button */}
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pt-2.5 border-t border-slate-100 text-[11px] font-mono text-slate-500">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="flex items-center gap-1">
                          <UserIcon className="w-3 h-3 text-slate-400" />
                          <span>
                            Investigator: <strong className="text-slate-700">{entry.created_by_name}</strong>
                          </span>
                        </span>
                        <span className="text-slate-300">|</span>
                        <span>Logged: {new Date(entry.created_at).toISOString().replace('T', ' ').substring(0, 16)} UTC</span>
                      </div>

                      {/* Cryptographic Seal & Verification Action */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <div className="flex items-center gap-1.5 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                          <span className="text-[10px] text-slate-400 font-bold">SHA-256 SEAL:</span>
                          <span className="text-blue-700 font-bold">
                            {entry.entry_hash ? `${entry.entry_hash.substring(0, 14)}…` : 'CALCULATING'}
                          </span>
                          {entry.entry_hash && (
                            <button
                              type="button"
                              onClick={() => {
                                navigator.clipboard.writeText(entry.entry_hash);
                                setCopiedHash(entry.entry_hash);
                                setTimeout(() => setCopiedHash(null), 2000);
                              }}
                              className="text-slate-400 hover:text-slate-700 p-0.5"
                              title="Copy full cryptographic SHA-256 digest"
                            >
                              {copiedHash === entry.entry_hash ? (
                                <Check className="w-3 h-3 text-emerald-600" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          )}
                        </div>

                        {verifyObj ? (
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold border ${
                              verifyObj.is_valid && verifyObj.previous_hash_matches
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                                : 'bg-red-50 text-red-700 border-red-300'
                            }`}
                          >
                            <ShieldCheck className="w-3 h-3" />
                            <span>{verifyObj.status}</span>
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleVerifyDiaryEntry(entry._id)}
                            disabled={isVerifying}
                            className="ws-btn ws-btn-secondary !py-0.5 !px-2 !text-[10px] font-mono inline-flex items-center gap-1 cursor-pointer hover:bg-slate-100"
                            title="Recalculate SHA-256 digest and verify cryptographic chain continuity"
                          >
                            <ShieldCheck className={`w-3 h-3 text-blue-600 ${isVerifying ? 'animate-spin' : ''}`} />
                            <span>{isVerifying ? 'Verifying...' : 'Verify Seal'}</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Pagination Bar */}
              {diaryTotal > diaryPageSize && (
                <div className="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-lg text-xs font-mono text-slate-600">
                  <span>
                    Showing {(diaryPage - 1) * diaryPageSize + 1} -{' '}
                    {Math.min(diaryPage * diaryPageSize, diaryTotal)} of {diaryTotal} entries
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      disabled={diaryPage === 1}
                      onClick={() => {
                        const newPage = diaryPage - 1;
                        setDiaryPage(newPage);
                        loadCaseDiary(newPage);
                      }}
                      className="ws-btn ws-btn-secondary !py-1 !px-2.5 !text-xs disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <span className="px-2 text-slate-700 font-bold">
                      Page {diaryPage} of {Math.ceil(diaryTotal / diaryPageSize)}
                    </span>
                    <button
                      type="button"
                      disabled={diaryPage >= Math.ceil(diaryTotal / diaryPageSize)}
                      onClick={() => {
                        const newPage = diaryPage + 1;
                        setDiaryPage(newPage);
                        loadCaseDiary(newPage);
                      }}
                      className="ws-btn ws-btn-secondary !py-1 !px-2.5 !text-xs disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* AUTHENTICATION REQUIRED MODAL (Triggered when adding, downloading, or viewing evidence) */}
      {authModalOpen && createPortal(
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 overflow-y-auto"
          onClick={() => setAuthModalOpen(false)}
        >
          <div 
            className="ws-panel-elevated w-full max-w-md max-h-[90vh] flex flex-col my-auto overflow-hidden shadow-2xl animate-fade-in-up"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-white shrink-0">
              <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
                <div className="w-7 h-7 rounded-md bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
                  <Lock className="w-4 h-4" />
                </div>
                <span>Authentication Required</span>
              </div>
              <button
                type="button"
                onClick={() => setAuthModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAuthSubmit} className="flex flex-col flex-1 min-h-0 overflow-hidden">
              <div className="overflow-y-auto p-5 sm:p-6 space-y-4 flex-1 min-h-0">
                <div className="space-y-1.5">
                  <p className="text-xs text-slate-600">
                    Please enter your credentials to access confidential evidence:
                  </p>
                  {authTargetName && (
                    <div className="p-2.5 rounded bg-slate-50 border border-slate-200 font-mono text-xs text-slate-800 truncate">
                      Operation: <strong className="text-blue-600">{authTargetName}</strong>
                    </div>
                  )}
                </div>

                {authError && (
                  <div className="p-2.5 rounded bg-red-50 border border-red-200 text-xs text-red-600 font-medium font-mono flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>{authError}</span>
                  </div>
                )}

                <div className="space-y-3.5">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Examiner Email / Username
                    </label>
                    <input
                      type="text"
                      value={authEmail}
                      onChange={e => setAuthEmail(e.target.value)}
                      required
                      className="ws-input w-full text-xs"
                      placeholder="examiner@cryptevid.gov"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Password
                    </label>
                    <div className="relative">
                      <input
                        type={showAuthPassword ? 'text' : 'password'}
                        value={authPassword}
                        onChange={e => setAuthPassword(e.target.value)}
                        required
                        autoFocus
                        className="ws-input w-full pr-9 text-xs"
                        placeholder="Enter investigator password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowAuthPassword(!showAuthPassword)}
                        className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
                      >
                        {showAuthPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-slate-200 bg-slate-50 shrink-0">
                <button
                  type="button"
                  onClick={() => setAuthModalOpen(false)}
                  className="ws-btn ws-btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={authSubmitting}
                  className="ws-btn ws-btn-primary text-xs flex items-center gap-1.5"
                >
                  {authSubmitting ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <LockOpen className="w-3.5 h-3.5" />
                  )}
                  <span>Authenticate & Proceed</span>
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* Upload Evidence Modal (Clean and focused) */}
      {showUploadModal && createPortal(
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 overflow-y-auto"
          onClick={() => setShowUploadModal(false)}
        >
          <div 
            className="ws-panel-elevated w-full max-w-lg max-h-[90vh] flex flex-col my-auto overflow-hidden shadow-2xl animate-fade-in-up"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-white shrink-0">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 font-mono">
                <Upload className="w-4 h-4 text-amber-500" />
                <span>Add Evidence Exhibit</span>
              </h3>
              <button 
                type="button" 
                onClick={() => setShowUploadModal(false)} 
                className="text-slate-400 hover:text-slate-700 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleUploadEvidence} className="flex flex-col flex-1 min-h-0 overflow-hidden">
              <div className="overflow-y-auto p-5 sm:p-6 space-y-4 flex-1 min-h-0">
                {uploadError && (
                  <div className="p-2.5 rounded bg-red-50 border border-red-200 text-xs font-mono text-red-600">
                    {uploadError}
                  </div>
                )}

                <div className="space-y-3.5 text-xs">
                  <div className="space-y-1">
                    <label className="text-slate-700 font-semibold block">Select Evidence File *</label>
                    <input
                      type="file"
                      onChange={e => setUploadFile(e.target.files ? e.target.files[0] : null)}
                      className="ws-input w-full file:mr-3 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:bg-blue-50 file:text-blue-600"
                      required
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-slate-700 font-semibold block">Description</label>
                    <textarea
                      value={uploadDescription}
                      onChange={e => setUploadDescription(e.target.value)}
                      rows={2}
                      placeholder="Notes on source, device, or acquisition origin..."
                      className="ws-input w-full font-sans"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-slate-700 font-semibold block">Tags (comma-separated)</label>
                    <input
                      type="text"
                      value={uploadTags}
                      onChange={e => setUploadTags(e.target.value)}
                      placeholder="PCAP, DISK_IMAGE, LOGS"
                      className="ws-input w-full font-mono text-xs"
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-slate-200 bg-slate-50 shrink-0">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="ws-btn ws-btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading || !uploadFile}
                  className="ws-btn ws-btn-amber text-xs flex items-center gap-1.5"
                >
                  {uploading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Hashing & Uploading...</span>
                    </>
                  ) : (
                    <>
                      <Upload className="w-3.5 h-3.5" />
                      <span>Upload & Seal Exhibit</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* Exhibit Details Inspector Modal */}
      {inspectEvidence && createPortal(
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 overflow-y-auto"
          onClick={() => setInspectEvidence(null)}
        >
          <div 
            className="ws-panel-elevated w-full max-w-lg max-h-[90vh] flex flex-col my-auto overflow-hidden shadow-2xl animate-fade-in-up"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-white shrink-0">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 font-mono">
                <FileCheck className="w-4 h-4 text-blue-500" />
                <span>Evidence Exhibit Inspector</span>
              </h3>
              <button 
                type="button" 
                onClick={() => setInspectEvidence(null)} 
                className="text-slate-400 hover:text-slate-700 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="overflow-y-auto p-5 space-y-3 text-xs font-mono flex-1 min-h-0">
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">EXHIBIT FILENAME:</span>
                <span className="text-slate-900 font-bold">{inspectEvidence.original_filename}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">SIZE:</span>
                <span className="text-slate-900">{(inspectEvidence.file_size / 1024).toFixed(1)} KB</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">MIME TYPE:</span>
                <span className="text-slate-900">{inspectEvidence.mime_type}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">INTEGRITY STATUS:</span>
                <span className={`ws-badge ${
                  inspectEvidence.integrity_status === 'VERIFIED' ? 'ws-badge-green' : 'ws-badge-red'
                }`}>
                  {inspectEvidence.integrity_status}
                </span>
              </div>
              <div className="space-y-1 pt-1">
                <span className="text-slate-500 block text-[10px]">SHA-256 HASH</span>
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-[10px] text-blue-600 break-all select-all">
                  {inspectEvidence.sha256_hash}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between px-5 py-3.5 border-t border-slate-200 bg-slate-50 shrink-0">
              <button
                type="button"
                onClick={() => handleDownload(inspectEvidence)}
                className="ws-btn ws-btn-secondary text-xs flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5 text-blue-500" />
                <span>Download Copy</span>
              </button>
              <button 
                type="button" 
                onClick={() => setInspectEvidence(null)} 
                className="ws-btn ws-btn-primary text-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Verify Evidence Modal Result */}
      {selectedVerify && createPortal(
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 overflow-y-auto"
          onClick={() => setSelectedVerify(null)}
        >
          <div 
            className="ws-panel-elevated w-full max-w-lg max-h-[90vh] flex flex-col my-auto overflow-hidden shadow-2xl animate-fade-in-up"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-white shrink-0">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 font-mono">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>SHA-256 Integrity Verification Result</span>
              </h3>
              <button 
                type="button" 
                onClick={() => setSelectedVerify(null)} 
                className="text-slate-400 hover:text-slate-700 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="overflow-y-auto p-5 space-y-3 font-mono text-xs flex-1 min-h-0">
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">EXHIBIT:</span>
                <span className="text-slate-900 font-bold">{selectedVerify.original_filename}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">STATUS:</span>
                <span className={`ws-badge ${
                  selectedVerify.integrity === 'VERIFIED' ? 'ws-badge-green' : 'ws-badge-red'
                }`}>
                  {selectedVerify.integrity}
                </span>
              </div>
              <div className="space-y-1 pt-1">
                <span className="text-slate-500 block text-[10px]">STORED BASELINE HASH</span>
                <div className="p-2 rounded bg-slate-50 border border-slate-200 text-[10px] text-blue-600 break-all">
                  {selectedVerify.stored_hash}
                </div>
              </div>
              <div className="space-y-1 pt-1">
                <span className="text-slate-500 block text-[10px]">CALCULATED DISK HASH</span>
                <div className="p-2 rounded bg-slate-50 border border-slate-200 text-[10px] text-emerald-600 break-all">
                  {selectedVerify.calculated_hash}
                </div>
              </div>
            </div>

            <div className="flex justify-end px-5 py-3.5 border-t border-slate-200 bg-slate-50 shrink-0">
              <button
                type="button"
                onClick={() => setSelectedVerify(null)}
                className="ws-btn ws-btn-secondary text-xs"
              >
                Close Report
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Custody Ledger Modal */}
      {custodyEvidence && createPortal(
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 overflow-y-auto"
          onClick={() => setCustodyEvidence(null)}
        >
          <div 
            className="ws-panel-elevated w-full max-w-2xl max-h-[90vh] flex flex-col my-auto overflow-hidden shadow-2xl animate-fade-in-up"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-white shrink-0">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 font-mono">
                <History className="w-4 h-4 text-amber-500" />
                <span>Chain of Custody Ledger: {custodyEvidence.original_filename}</span>
              </h3>
              <button 
                type="button" 
                onClick={() => setCustodyEvidence(null)} 
                className="text-slate-400 hover:text-slate-700 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="overflow-y-auto p-5 space-y-2.5 flex-1 min-h-0">
              {custodyLoading ? (
                <p className="text-center py-8 text-xs text-slate-500">Loading custody records...</p>
              ) : custodyEvents.length === 0 ? (
                <p className="text-center py-8 text-xs text-slate-500">No custody transfers logged.</p>
              ) : (
                custodyEvents.map((evt, idx) => (
                  <div key={idx} className="ws-panel-subtle p-3 space-y-1 font-mono text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-amber-600 font-bold">{evt.action}</span>
                      <span className="text-slate-400 text-[10px]">{new Date(evt.timestamp).toLocaleString()}</span>
                    </div>
                    <div className="text-xs text-slate-900 font-sans">{evt.details}</div>
                    <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-100">
                      <span>Custodian: <strong className="text-slate-700">{evt.actor_name}</strong></span>
                      <span>Hash Seal: <strong className="text-blue-600">{evt.event_hash?.substring(0, 12)}…</strong></span>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="flex justify-end px-5 py-3.5 border-t border-slate-200 bg-slate-50 shrink-0">
              <button
                type="button"
                onClick={() => setCustodyEvidence(null)}
                className="ws-btn ws-btn-secondary text-xs"
              >
                Close Ledger
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* RECORD INVESTIGATION DIARY ENTRY MODAL */}
      {showCreateDiaryModal && createPortal(
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 overflow-y-auto"
          onClick={() => setShowCreateDiaryModal(false)}
        >
          <div 
            className="ws-panel-elevated w-full max-w-2xl max-h-[92vh] flex flex-col my-auto overflow-hidden shadow-2xl animate-fade-in-up"
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-white shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-md bg-[#0B1B3D] text-amber-300 flex items-center justify-center shrink-0">
                  <BookOpen className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Record Investigation Diary Entry
                  </h3>
                  <p className="text-[11px] text-slate-500 font-mono">
                    BNSS Section 192 Digital Case Diary // Case: {caseData.case_number}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateDiaryModal(false)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleCreateDiarySubmit} className="flex flex-col flex-1 min-h-0 overflow-hidden">
              <div className="overflow-y-auto p-5 space-y-4 flex-1 min-h-0 text-xs">
                {diaryFormError && (
                  <div className="p-2.5 rounded bg-red-50 border border-red-200 text-xs text-red-600 font-medium font-mono flex items-center gap-1.5">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{diaryFormError}</span>
                  </div>
                )}

                {/* AI Smart Assistant (Tanglish & Multi-Format Parser) */}
                <div className="p-3.5 rounded-lg bg-gradient-to-r from-violet-50/80 via-indigo-50/70 to-blue-50/80 border border-indigo-200 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="p-1 rounded-md bg-violet-600 text-white shadow-xs">
                        <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-slate-900 font-mono flex items-center gap-1.5">
                          <span>AI Smart Assistant (Tanglish & Multilingual Parser)</span>
                        </h4>
                        <p className="text-[10px] text-slate-500">
                          Write in Tanglish, Hinglish, or informal field notes. AI organizes every event chronologically with timestamps and locations for court-admissible filing.
                        </p>
                      </div>
                    </div>
                  </div>

                  <textarea
                    rows={3}
                    value={createAiRawText}
                    onChange={e => setCreateAiRawText(e.target.value)}
                    placeholder='Example Tanglish: "inniku morning 10 am ku cyber cell ponen, server room check pannom disk image clone eduthom, 2 pm ku bank manager kita statement vaanginom, 5 pm ku office vanthu mudichom"'
                    className="ws-input w-full text-xs font-sans bg-white border-indigo-200 focus:border-indigo-500"
                  />

                  <div className="flex items-center justify-between">
                    <div className="text-[10px] font-mono text-slate-500">
                      {createDetectedLanguage && (
                        <span className="inline-flex items-center gap-1 font-bold text-indigo-700 bg-indigo-100/70 px-2 py-0.5 rounded border border-indigo-200">
                          <Languages className="w-3 h-3 text-indigo-600" />
                          <span>Identified: {createDetectedLanguage}</span>
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={handleAiParseCreate}
                      disabled={createAiParsing || !createAiRawText.trim()}
                      className="ws-btn !bg-violet-700 hover:!bg-violet-800 text-white text-xs font-bold font-mono !py-1 !px-3 inline-flex items-center gap-1.5 cursor-pointer shadow-xs disabled:opacity-50"
                    >
                      {createAiParsing ? (
                        <>
                          <RefreshCw className="w-3 h-3 animate-spin text-white" />
                          <span>Parsing & Ordering Timeline...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3 h-3 text-amber-300" />
                          <span>Auto-Organize with AI</span>
                        </>
                      )}
                    </button>
                  </div>

                  {createAiMessage && (
                    <div className="p-2 rounded bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] font-sans flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                      <span>{createAiMessage}</span>
                    </div>
                  )}

                  {createTimelineEvents.length > 0 && (
                    <div className="p-2.5 rounded bg-white border border-indigo-100 space-y-1.5">
                      <div className="text-[10px] font-bold font-mono text-indigo-900 uppercase flex items-center justify-between">
                        <span>Extracted Chronological Milestones ({createTimelineEvents.length})</span>
                        <span className="text-slate-400 font-normal">Ordered by Time</span>
                      </div>
                      <div className="space-y-1 max-h-32 overflow-y-auto">
                        {createTimelineEvents.map((ev, idx) => (
                          <div key={idx} className="flex items-center gap-2 p-1.5 rounded bg-slate-50 border border-slate-100 text-[11px]">
                            <span className="px-1.5 py-0.2 rounded bg-indigo-100 text-indigo-800 font-mono font-bold text-[10px]">
                              {ev.time}
                            </span>
                            <span className="px-1.5 py-0.2 rounded bg-slate-200 text-slate-700 font-mono text-[9px]">
                              {ev.location}
                            </span>
                            <span className="text-slate-700 text-xs truncate flex-1">{ev.activity}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Date & Time Parameters */}
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Investigation Date <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="date"
                      value={createDiaryDate}
                      onChange={e => setCreateDiaryDate(e.target.value)}
                      required
                      className="ws-input w-full text-xs font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Time Info Received
                    </label>
                    <input
                      type="text"
                      value={createDiaryTimeReceived}
                      onChange={e => setCreateDiaryTimeReceived(e.target.value)}
                      placeholder="e.g. 09:15"
                      className="ws-input w-full text-xs font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Start Time <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={createDiaryStartTime}
                      onChange={e => setCreateDiaryStartTime(e.target.value)}
                      required
                      placeholder="e.g. 09:30"
                      className="ws-input w-full text-xs font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Closing Time <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={createDiaryClosingTime}
                      onChange={e => setCreateDiaryClosingTime(e.target.value)}
                      required
                      placeholder="e.g. 18:00"
                      className="ws-input w-full text-xs font-mono"
                    />
                  </div>
                </div>

                {/* Places Visited */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Place(s) Visited
                  </label>
                  <input
                    type="text"
                    value={createDiaryPlaces}
                    onChange={e => setCreateDiaryPlaces(e.target.value)}
                    placeholder="Separate multiple places with commas, e.g. Cyber Cell HQ, Bank Vault, Server Room B"
                    className="ws-input w-full text-xs"
                  />
                  <span className="text-[10px] text-slate-400 mt-0.5 block">
                    BNSS Sec. 192 requires recording all locations inspected during investigation.
                  </span>
                </div>

                {/* Activities Performed */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Investigation Activities & Proceedings Performed <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    rows={3}
                    value={createDiaryActivities}
                    onChange={e => setCreateDiaryActivities(e.target.value)}
                    required
                    placeholder="Describe day-by-day investigation proceedings, exhibit acquisitions, technical interrogations, logs reviewed..."
                    className="ws-input w-full text-xs font-sans"
                  />
                </div>

                {/* Circumstances and Findings */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Statement of Circumstances & Findings Discovered <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    rows={3}
                    value={createDiaryFindings}
                    onChange={e => setCreateDiaryFindings(e.target.value)}
                    required
                    placeholder="Record circumstances ascertained through investigation, discovered evidence, corroborated signals, anomalies..."
                    className="ws-input w-full text-xs font-sans"
                  />
                </div>

                {/* Related Evidence Exhibits Selection */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Related Evidence Exhibits
                  </label>
                  {evidenceList.length === 0 ? (
                    <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-slate-500 text-xs">
                      No evidence exhibits registered in this case container yet.
                    </div>
                  ) : (
                    <div className="max-h-28 overflow-y-auto p-2.5 rounded bg-slate-50 border border-slate-200 space-y-1.5">
                      {evidenceList.map(ev => {
                        const isChecked = createDiarySelectedEvidence.includes(ev._id);
                        return (
                          <label
                            key={ev._id}
                            className="flex items-center gap-2 cursor-pointer hover:bg-white p-1 rounded transition-colors text-xs"
                          >
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => {
                                setCreateDiarySelectedEvidence(prev =>
                                  isChecked ? prev.filter(id => id !== ev._id) : [...prev, ev._id]
                                );
                              }}
                              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                            />
                            <span className="font-mono text-slate-700 font-semibold">{ev.original_filename}</span>
                            <span className="text-slate-400 font-mono text-[10px]">({ev.sha256_hash.substring(0, 10)}…)</span>
                          </label>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Witness References */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-[11px] font-semibold text-slate-700">
                      Witness-Related References
                    </label>
                    <span className="inline-flex items-center gap-1 text-[10px] text-amber-700 font-bold font-mono">
                      <Lock className="w-3 h-3" />
                      <span>CONFIDENTIAL // BNSS SEC. 192(3)</span>
                    </span>
                  </div>
                  <textarea
                    rows={2}
                    value={createDiaryWitness}
                    onChange={e => setCreateDiaryWitness(e.target.value)}
                    placeholder="Enter confidential witness identity notes or statement references. Redacted for unauthorized roles."
                    className="ws-input w-full text-xs font-sans border-amber-200 focus:border-amber-400"
                  />
                </div>

                {/* Next Steps & Remarks */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Next Steps & Procedural Remarks
                  </label>
                  <textarea
                    rows={2}
                    value={createDiaryNextSteps}
                    onChange={e => setCreateDiaryNextSteps(e.target.value)}
                    placeholder="Forward investigative actions, pending laboratory examinations, judicial deadlines..."
                    className="ws-input w-full text-xs font-sans"
                  />
                </div>

                {/* Cryptographic Guarantee Notice */}
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-[11px] text-slate-500 font-mono flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0" />
                  <span>
                    Saving this entry automatically computes an immutable SHA-256 digest chained to the previous entry,
                    sealing your authenticated investigator ID and server timestamp.
                  </span>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="flex items-center justify-end gap-2.5 px-5 py-3.5 border-t border-slate-200 bg-slate-50 shrink-0">
                <button
                  type="button"
                  onClick={() => setShowCreateDiaryModal(false)}
                  disabled={diarySubmitting}
                  className="ws-btn ws-btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={diarySubmitting}
                  className="ws-btn !bg-[#0B1B3D] hover:!bg-[#152a57] text-amber-300 border border-amber-500/40 text-xs font-bold inline-flex items-center gap-1.5 shadow-sm cursor-pointer"
                >
                  {diarySubmitting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Sealing Entry...</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-3.5 h-3.5 text-amber-300" />
                      <span>Record & Cryptographically Seal</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* AMEND INVESTIGATION DIARY ENTRY MODAL */}
      {amendingEntry && createPortal(
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 overflow-y-auto"
          onClick={() => setAmendingEntry(null)}
        >
          <div 
            className="ws-panel-elevated w-full max-w-2xl max-h-[92vh] flex flex-col my-auto overflow-hidden shadow-2xl animate-fade-in-up"
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-white shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-md bg-amber-500 text-white flex items-center justify-center shrink-0">
                  <FileEdit className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Amend Diary Entry: {amendingEntry.entry_code}
                  </h3>
                  <p className="text-[11px] text-slate-500 font-mono">
                    BNSS Section 192 Amendment Protocol // Case: {caseData.case_number}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setAmendingEntry(null)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleAmendDiarySubmit} className="flex flex-col flex-1 min-h-0 overflow-hidden">
              <div className="overflow-y-auto p-5 space-y-4 flex-1 min-h-0 text-xs">
                {amendFormError && (
                  <div className="p-2.5 rounded bg-red-50 border border-red-200 text-xs text-red-600 font-medium font-mono flex items-center gap-1.5">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{amendFormError}</span>
                  </div>
                )}

                {/* Immutability Policy Banner */}
                <div className="p-3 rounded bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-1">
                  <div className="font-bold font-mono text-[11px] flex items-center gap-1 text-amber-800">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>BNSS SECTION 192 IMMUTABILITY & AMENDMENT POLICY</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    Finalized investigation diary entries are never overwritten or deleted. This modification
                    will be recorded as a permanent, versioned amendment with your investigator ID, server timestamp,
                    and cryptographic hash seal.
                  </p>
                </div>

                {/* Mandatory Reason for Amendment */}
                <div>
                  <label className="block text-[11px] font-bold text-slate-900 mb-1">
                    Mandatory Official Justification for Amendment <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    rows={2}
                    value={amendReason}
                    onChange={e => setAmendReason(e.target.value)}
                    required
                    placeholder="State the official factual reason why this entry is being corrected or supplemented..."
                    className="ws-input w-full text-xs font-sans border-amber-300 focus:border-amber-500"
                  />
                </div>

                {/* AI Smart Assistant for Amendments */}
                <div className="p-3 rounded-lg bg-gradient-to-r from-violet-50/80 via-amber-50/60 to-indigo-50/80 border border-violet-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-violet-600" />
                      <span className="text-xs font-bold text-slate-900 font-mono">
                        AI Re-organizer (Tanglish / Updated Notes)
                      </span>
                    </div>
                  </div>

                  <textarea
                    rows={2}
                    value={amendAiRawText}
                    onChange={e => setAmendAiRawText(e.target.value)}
                    placeholder="Enter updated notes or clarifications in Tanglish or informal text to re-calculate chronological sequence..."
                    className="ws-input w-full text-xs font-sans bg-white border-violet-200 focus:border-violet-500"
                  />

                  <div className="flex items-center justify-between">
                    <div className="text-[10px] font-mono text-slate-500">
                      {amendDetectedLanguage && (
                        <span className="font-bold text-violet-700 bg-violet-100 px-1.5 py-0.5 rounded">
                          Format: {amendDetectedLanguage}
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={handleAiParseAmend}
                      disabled={amendAiParsing || !amendAiRawText.trim()}
                      className="ws-btn !bg-violet-700 hover:!bg-violet-800 text-white text-xs font-bold font-mono !py-0.5 !px-2.5 inline-flex items-center gap-1 cursor-pointer disabled:opacity-50"
                    >
                      {amendAiParsing ? (
                        <>
                          <RefreshCw className="w-3 h-3 animate-spin text-white" />
                          <span>Re-organizing...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3 h-3 text-amber-300" />
                          <span>Re-Organize with AI</span>
                        </>
                      )}
                    </button>
                  </div>

                  {amendAiMessage && (
                    <div className="p-1.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-800 text-[10px] font-sans flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600 shrink-0" />
                      <span>{amendAiMessage}</span>
                    </div>
                  )}

                  {amendTimelineEvents.length > 0 && (
                    <div className="p-2 rounded bg-white border border-violet-100 text-[10px] font-mono text-slate-600">
                      <div className="font-bold text-violet-900 mb-1">Updated Timeline ({amendTimelineEvents.length} Milestones)</div>
                      <div className="max-h-24 overflow-y-auto space-y-1">
                        {amendTimelineEvents.map((ev, idx) => (
                          <div key={idx} className="flex items-center gap-1.5">
                            <span className="bg-violet-100 text-violet-800 px-1 py-0.2 rounded font-bold">{ev.time}</span>
                            <span className="text-slate-500">[{ev.location}]</span>
                            <span className="text-slate-800 truncate">{ev.activity}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Date & Time Parameters */}
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Investigation Date
                    </label>
                    <input
                      type="date"
                      value={amendDate}
                      onChange={e => setAmendDate(e.target.value)}
                      className="ws-input w-full text-xs font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Time Info Received
                    </label>
                    <input
                      type="text"
                      value={amendTimeReceived}
                      onChange={e => setAmendTimeReceived(e.target.value)}
                      placeholder="e.g. 09:15"
                      className="ws-input w-full text-xs font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Start Time
                    </label>
                    <input
                      type="text"
                      value={amendStartTime}
                      onChange={e => setAmendStartTime(e.target.value)}
                      placeholder="e.g. 09:30"
                      className="ws-input w-full text-xs font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Closing Time
                    </label>
                    <input
                      type="text"
                      value={amendClosingTime}
                      onChange={e => setAmendClosingTime(e.target.value)}
                      placeholder="e.g. 18:00"
                      className="ws-input w-full text-xs font-mono"
                    />
                  </div>
                </div>

                {/* Places Visited */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Place(s) Visited
                  </label>
                  <input
                    type="text"
                    value={amendPlaces}
                    onChange={e => setAmendPlaces(e.target.value)}
                    placeholder="Comma-separated locations"
                    className="ws-input w-full text-xs"
                  />
                </div>

                {/* Activities Performed */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Investigation Activities & Proceedings Performed
                  </label>
                  <textarea
                    rows={3}
                    value={amendActivities}
                    onChange={e => setAmendActivities(e.target.value)}
                    className="ws-input w-full text-xs font-sans"
                  />
                </div>

                {/* Circumstances and Findings */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Statement of Circumstances & Findings Discovered
                  </label>
                  <textarea
                    rows={3}
                    value={amendFindings}
                    onChange={e => setAmendFindings(e.target.value)}
                    className="ws-input w-full text-xs font-sans"
                  />
                </div>

                {/* Related Exhibits */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Related Evidence Exhibits
                  </label>
                  <div className="max-h-24 overflow-y-auto p-2 rounded bg-slate-50 border border-slate-200 space-y-1">
                    {evidenceList.map(ev => {
                      const isChecked = amendSelectedEvidence.includes(ev._id);
                      return (
                        <label
                          key={ev._id}
                          className="flex items-center gap-2 cursor-pointer hover:bg-white p-1 rounded text-xs"
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => {
                              setAmendSelectedEvidence(prev =>
                                isChecked ? prev.filter(id => id !== ev._id) : [...prev, ev._id]
                              );
                            }}
                            className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="font-mono text-slate-700">{ev.original_filename}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>

                {/* Witness References */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Witness References (Confidential under BNSS Sec. 192(3))
                  </label>
                  <textarea
                    rows={2}
                    value={amendWitness}
                    onChange={e => setAmendWitness(e.target.value)}
                    className="ws-input w-full text-xs font-sans border-amber-200"
                  />
                </div>

                {/* Next Steps */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Next Steps & Procedural Remarks
                  </label>
                  <textarea
                    rows={2}
                    value={amendNextSteps}
                    onChange={e => setAmendNextSteps(e.target.value)}
                    className="ws-input w-full text-xs font-sans"
                  />
                </div>
              </div>

              {/* Modal Footer */}
              <div className="flex items-center justify-end gap-2.5 px-5 py-3.5 border-t border-slate-200 bg-slate-50 shrink-0">
                <button
                  type="button"
                  onClick={() => setAmendingEntry(null)}
                  disabled={amendSubmitting}
                  className="ws-btn ws-btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={amendSubmitting}
                  className="ws-btn ws-btn-amber text-xs font-bold inline-flex items-center gap-1.5 shadow-sm cursor-pointer"
                >
                  {amendSubmitting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Recording Amendment...</span>
                    </>
                  ) : (
                    <>
                      <FileEdit className="w-3.5 h-3.5" />
                      <span>Submit Verified Amendment</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* VIEW AMENDMENT AUDIT TRAIL MODAL */}
      {historyEntry && createPortal(
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 overflow-y-auto"
          onClick={() => setHistoryEntry(null)}
        >
          <div 
            className="ws-panel-elevated w-full max-w-2xl max-h-[90vh] flex flex-col my-auto overflow-hidden shadow-2xl animate-fade-in-up"
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-white shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-md bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center shrink-0">
                  <History className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Amendment Audit Trail: {historyEntry.entry_code}
                  </h3>
                  <p className="text-[11px] text-slate-500 font-mono">
                    Baseline Entry Created: {new Date(historyEntry.created_at).toISOString().replace('T', ' ').substring(0, 16)} UTC by {historyEntry.created_by_name}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setHistoryEntry(null)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body: List of Amendments */}
            <div className="overflow-y-auto p-5 space-y-4 flex-1 min-h-0 text-xs">
              <div className="p-2.5 rounded bg-slate-50 border border-slate-200 font-mono text-[11px] text-slate-700 flex items-center justify-between">
                <span>Baseline Cryptographic Hash:</span>
                <strong className="text-blue-700">{historyEntry.entry_hash}</strong>
              </div>

              {(!historyEntry.amendments || historyEntry.amendments.length === 0) ? (
                <div className="text-center py-6 text-slate-500">
                  No amendments recorded. This entry retains its pristine original baseline.
                </div>
              ) : (
                <div className="space-y-3.5">
                  {historyEntry.amendments.map((amend, idx) => (
                    <div
                      key={amend.amendment_id || idx}
                      className="p-3.5 rounded-lg bg-white border border-amber-200 shadow-2xs space-y-2.5"
                    >
                      <div className="flex items-center justify-between pb-2 border-b border-slate-100 font-mono text-xs">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-bold">
                            Amendment #{idx + 1}
                          </span>
                          <span className="text-slate-600">
                            By: <strong>{amend.amended_by_name}</strong>
                          </span>
                        </div>
                        <span className="text-slate-400 text-[11px]">
                          {new Date(amend.timestamp).toISOString().replace('T', ' ').substring(0, 16)} UTC
                        </span>
                      </div>

                      {/* Reason */}
                      <div className="p-2 rounded bg-amber-50/50 border border-amber-100 text-xs space-y-0.5">
                        <span className="text-[10px] font-bold font-mono text-amber-800 uppercase tracking-wider block">
                          Recorded Official Justification:
                        </span>
                        <p className="text-slate-800 font-medium italic">"{amend.reason}"</p>
                      </div>

                      {/* State Changes Diff */}
                      <div className="space-y-1.5">
                        <span className="text-[10px] font-bold font-mono text-slate-500 uppercase tracking-wider block">
                          Modified Field Snapshots:
                        </span>
                        {Object.keys(amend.new_state || {}).map(field => (
                          <div key={field} className="p-2 rounded bg-slate-50 border border-slate-200 font-mono text-[11px] space-y-1">
                            <div className="font-bold text-slate-700 capitalize">{field.replace(/_/g, ' ')}:</div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10px]">
                              <div className="text-red-700 bg-red-50/60 p-1.5 rounded border border-red-100 overflow-x-auto">
                                <span className="font-bold block">Previous:</span>
                                {JSON.stringify(amend.previous_state?.[field] ?? 'null')}
                              </div>
                              <div className="text-emerald-700 bg-emerald-50/60 p-1.5 rounded border border-emerald-100 overflow-x-auto">
                                <span className="font-bold block">Amended To:</span>
                                {JSON.stringify(amend.new_state?.[field] ?? 'null')}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Cryptographic Amendment Hash */}
                      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] font-mono text-slate-500">
                        <span>Amendment Hash Seal:</span>
                        <span className="text-amber-700 font-bold">{amend.amendment_hash}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="flex justify-end px-5 py-3.5 border-t border-slate-200 bg-slate-50 shrink-0">
              <button
                type="button"
                onClick={() => setHistoryEntry(null)}
                className="ws-btn ws-btn-secondary text-xs"
              >
                Close Audit Trail
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};

export default CaseDetail;
