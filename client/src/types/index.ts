export type UserRole = 'admin' | 'investigator' | 'readonly' | 'portal_manager';

export interface User {
  _id: string;
  email: string;
  name: string;
  role: UserRole;
  rfid?: string;
  fingerprint_id?: number;
  is_active: boolean;
  created_at: string;
}

export type CaseStatus = 'OPEN' | 'IN_PROGRESS' | 'ON_HOLD' | 'CLOSED' | 'ARCHIVED' | 'active' | 'closed' | 'archived';

export type CasePriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type CaseType =
  | 'PHISHING'
  | 'MALWARE'
  | 'INSIDER_THREAT'
  | 'DATA_BREACH'
  | 'FINANCIAL_FRAUD'
  | 'UNAUTHORIZED_ACCESS'
  | 'OTHER';

export interface CaseNote {
  id?: string;
  _id?: string;
  author_id?: string;
  author_name?: string;
  author?: string;
  content: string;
  timestamp?: string;
  created_at?: string;
}

export interface Case {
  _id: string;
  case_number: string;
  title: string;
  description: string;
  case_type: CaseType;
  priority: CasePriority;
  status: CaseStatus;
  created_by: string;
  created_by_name?: string;
  assigned_investigator?: string;
  assigned_investigator_name?: string;
  created_at: string;
  updated_at: string;
  closed_at?: string;
  tags: string[];
  notes: CaseNote[];
  assigned_investigators?: string[];
}

export interface CaseStats {
  total_cases: number;
  active_cases: number;
  open_cases: number;
  critical_cases: number;
  closed_cases: number;
  archived_cases: number;
}

export interface InvestigatorOption {
  _id: string;
  name: string;
  email: string;
  role: string;
}

export type MetadataStatus = 'PENDING' | 'EXTRACTED' | 'FAILED';

export interface EvidenceMetadata {
  _id: string;
  evidence_id: string;
  case_id: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  file_extension: string;
  source_device: string;
  source_type: string;
  collector: string;
  collection_timestamp: string;
  description?: string;
  tags: string[];
  latitude?: number;
  longitude?: number;
  metadata_status: MetadataStatus;
  extracted_attributes: Record<string, any>;
  error_message?: string;
  created_at?: string;
  modified_at?: string;
}

export type EvidenceType =
  | 'image'
  | 'video'
  | 'pdf'
  | 'log'
  | 'pcap'
  | 'memory_dump'
  | 'zip'
  | 'text'
  | 'other';

export type IntegrityStatus =
  | 'PENDING'
  | 'VERIFIED'
  | 'INTACT'
  | 'TAMPERED'
  | 'INTEGRITY_MISMATCH'
  | 'UNDER_INVESTIGATION';

export type CustodyAction =
  | 'EVIDENCE_COLLECTED'
  | 'EVIDENCE_UPLOADED'
  | 'EVIDENCE_VIEWED'
  | 'EVIDENCE_DOWNLOADED'
  | 'EVIDENCE_VERIFIED'
  | 'EVIDENCE_INTEGRITY_FAILURE'
  | 'EVIDENCE_METADATA_UPDATED'
  | 'EVIDENCE_ANALYZED'
  | 'ORIGINAL_BACKUP_CREATED'
  | 'BACKUP_INTEGRITY_VERIFIED'
  | 'BACKUP_INTEGRITY_FAILURE'
  | 'TAMPER_DETECTED_VS_ORIGINAL'
  | 'BACKUP_DOWNLOADED'
  | 'BACKUP_ACCESSED'
  | 'AUTHORIZED_MODIFICATION'
  | 'TAMPER_CONFIRMED'
  | 'INTEGRITY_DISCREPANCY_FLAGGED';

export interface EvidenceStats {
  total_evidence: number;
  verified_evidence: number;
  tampered_evidence: number;
  pending_evidence: number;
  integrity_rate: number;
}

export interface CustodyEvent {
  _id: string;
  event_id: string;
  evidence_id: string;
  case_id: string;
  action: CustodyAction;
  actor_id: string;
  actor_name: string;
  timestamp: string;
  ip_address: string;
  device_id: string;
  previous_hash: string;
  event_hash: string;
  details: string;
  is_chain_valid?: boolean;
}

export interface EvidenceVerifyResult {
  evidence_id: string;
  original_filename: string;
  stored_hash: string;
  calculated_hash: string;
  integrity: IntegrityStatus;
  verified_at: string;
  message: string;
  has_original_backup?: boolean;
  original_sha256_hash?: string;
}

export interface Evidence {
  _id: string;
  case_id: string;
  case_number?: string;
  case_title?: string;
  original_filename: string;
  stored_filename?: string;
  file_size: number;
  mime_type: string;
  file_extension: string;
  source_device: string;
  source_type: string;
  collector_id: string;
  collector_name: string;
  collection_timestamp: string;
  created_at: string;
  sha256_hash: string;
  original_sha256_hash?: string;
  version?: number;
  version_history?: Array<{
    version: number;
    sha256_hash: string;
    file_size: number;
    modified_at: string;
    modified_by_name: string;
    reason: string;
    notes?: string;
  }>;
  has_original_backup?: boolean;
  original_backup_created_at?: string;
  tamper_details?: {
    confirmed_at: string;
    confirmed_by?: string;
    confirmed_by_name: string;
    reason: string;
    attacker_attribution: string;
    investigation_notes?: string;
  };
  integrity_status: IntegrityStatus;
  last_verified_at?: string;
  last_calculated_hash?: string;
  metadata_id?: string;
  description?: string;
  tags?: string[];
  metadata_status?: MetadataStatus;
  extracted_attributes?: Record<string, any>;
  
  // Legacy compatibility fields
  title?: string;
  file_name?: string;
  original_name?: string;
  evidence_type?: EvidenceType;
  file_path?: string;
  metadata?: Record<string, any>;
  uploaded_by?: string;
  upload_time?: string;
  latitude?: number;
  longitude?: number;
  investigator_name?: string;
}

export interface PortalManagerOverview {
  total_users: number;
  active_users: number;
  inactive_users: number;
  total_cases: number;
  total_assigned_officers: number;
  assignment_overview: {
    assigned_cases: number;
    unassigned_cases: number;
    assignment_rate: number;
    open_cases: number;
    in_progress_cases: number;
    closed_cases: number;
    on_hold_cases: number;
  };
}

export interface PortalUser {
  _id: string;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  assigned_cases_count?: number;
}

export interface PortalCaseOversight {
  _id: string;
  case_id: string;
  case_number: string;
  title: string;
  description: string;
  case_type: CaseType;
  priority: CasePriority;
  status: CaseStatus;
  created_at: string;
  updated_at: string;
  assigned_officer_id?: string | null;
  assigned_officer_name: string;
  assigned_officer_email?: string | null;
  assignment_status: 'ASSIGNED' | 'UNASSIGNED';
}

export interface EvidenceHashAudit {
  _id: string;
  evidence_id: string;
  calculated_hash: string;
  expected_hash: string;
  status: 'verified' | 'tampered';
  verified_by: string;
  timestamp: string;
}

export type AuditAction =
  | 'login'
  | 'logout'
  | 'register'
  | 'upload'
  | 'download'
  | 'view'
  | 'verify'
  | 'analyze'
  | 'report'
  | 'delete'
  | 'tampering_alert'
  | 'device_heartbeat'
  | 'device_offline';

export interface AuditLog {
  _id: string;
  case_id?: string;
  evidence_id?: string;
  user_id: string;
  action: AuditAction;
  ip_address: string;
  user_agent: string;
  device_id: string;
  details: string;
  timestamp: string;
  // Join fields
  user_name?: string;
  user_email?: string;
}

export interface Device {
  _id: string;
  device_id: string;
  mac_address: string;
  firmware_version: string;
  status: 'online' | 'offline';
  last_seen: string;
  created_at: string;
}

export type EventType =
  | 'LOGIN'
  | 'FILE_CREATED'
  | 'FILE_MODIFIED'
  | 'FILE_DELETED'
  | 'FILE_ACCESSED'
  | 'EMAIL_RECEIVED'
  | 'EMAIL_SENT'
  | 'PROCESS_EXECUTED'
  | 'USB_CONNECTED'
  | 'NETWORK_CONNECTION'
  | 'MALWARE_DETECTED'
  | 'EVIDENCE_COLLECTED'
  | 'EVIDENCE_UPLOADED'
  | 'EVIDENCE_VERIFIED'
  | 'EVIDENCE_TAMPERED'
  | 'CASE_EVENT'
  | 'INVESTIGATOR_NOTE'
  | 'OTHER';

export type EventSourceType =
  | 'EVIDENCE_METADATA'
  | 'AUDIT_LOG'
  | 'MANUAL_ENTRY'
  | 'SYSTEM'
  | 'DEVICE'
  | 'AI_ANALYSIS';

export type TimePrecision = 'EXACT' | 'APPROXIMATE' | 'UNKNOWN';
export type EventConfidence = 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN';
export type EventSeverity = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface TimelineEvent {
  _id: string;
  event_id: string;
  case_id: string;
  evidence_id?: string;
  evidence_filename?: string;
  event_type: string;
  event_time?: string;
  event_time_end?: string;
  time_precision: TimePrecision;
  time_start?: string;
  time_end?: string;
  title: string;
  description: string;
  source: string;
  source_type: EventSourceType;
  source_reference?: string;
  actor_id?: string;
  actor_name?: string;
  device_id?: string;
  location?: string;
  latitude?: number;
  longitude?: number;
  confidence: EventConfidence;
  severity: EventSeverity;
  tags?: string[];
  metadata?: Record<string, any>;
  is_system_generated?: boolean;
  created_at: string;
  created_by?: string;

  // Legacy fields
  timestamp?: string;
  event?: string;
  details?: string;
  source_evidence?: string;
}

export interface TimelineResponse {
  case_id: string;
  total_events: number;
  returned_events: number;
  start_filter?: string;
  end_filter?: string;
  events: TimelineEvent[];
}

export interface TimelineStats {
  total_events: number;
  critical_events: number;
  high_events: number;
  medium_events: number;
  low_events: number;
  info_events: number;
  system_events: number;
  manual_events: number;
  first_event_time?: string;
  last_event_time?: string;
  event_types: Record<string, number>;
}

export interface CreateEventPayload {
  event_type: EventType;
  title: string;
  description?: string;
  event_time?: string;
  event_time_end?: string;
  time_precision?: TimePrecision;
  time_start?: string;
  time_end?: string;
  evidence_id?: string;
  source?: string;
  source_type?: EventSourceType;
  device_id?: string;
  location?: string;
  latitude?: number;
  longitude?: number;
  confidence?: EventConfidence;
  severity?: EventSeverity;
  tags?: string[];
  metadata?: Record<string, any>;
}

export interface AIResult {
  _id: string;
  case_id: string;
  evidence_ids: string[];
  incident_classification: string;
  risk_score: number;
  summary: string;
  detected_attack_patterns: string[];
  timeline_events: TimelineEvent[];
  recommendations: string[];
  created_at: string;
}

export interface Report {
  _id: string;
  case_id: string;
  generated_by: string;
  pdf_path: string;
  digital_signature: string;
  qr_code_content: string;
  created_at: string;
}

export interface Notification {
  _id: string;
  title: string;
  message: string;
  type: 'info' | 'warning' | 'alert';
  read: boolean;
  created_at: string;
}

// Milestone 4: Evidence Graph Types
export type GraphNodeType =
  | 'CASE'
  | 'EVIDENCE'
  | 'EVENT'
  | 'DEVICE'
  | 'INVESTIGATOR'
  | 'LOCATION'
  | 'CUSTODY'
  | 'ACTOR'
  | 'IP_ADDRESS'
  | 'SECURITY_ALERT'
  | 'BACKUP'
  | 'THREAT_ACTOR';

export type GraphEdgeType =
  | 'CONTAINS'
  | 'GENERATED_EVENT'
  | 'COLLECTED_FROM'
  | 'OCCURRED_ON'
  | 'LOCATED_AT'
  | 'HANDLED_BY'
  | 'HAS_CUSTODY_EVENT'
  | 'CORRELATED_WITH'
  | 'ATTEMPTED_ACCESS'
  | 'HAS_BACKUP'
  | 'TAMPER_DETECTED';

export interface GraphNode {
  id: string;
  node_type: GraphNodeType;
  label: string;
  case_id: string;
  source_id: string;
  severity?: string;
  metadata?: Record<string, any>;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  edge_type: GraphEdgeType;
  label: string;
  metadata?: Record<string, any>;
}

export interface EvidenceGraphResponse {
  case_id: string;
  total_nodes: number;
  total_edges: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// Milestone 4: Deterministic AI Risk & Recommendations Types
export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';

export interface RiskSignal {
  signal_type: string;
  count: number;
  impact_score: number;
  reason: string;
  associated_ids: string[];
}

export interface RiskScoreResponse {
  case_id: string;
  score: number;
  risk_level: RiskLevel;
  signals: RiskSignal[];
  explanation: string;
  calculated_at: string;
}

export interface AIAnalysisResponse {
  case_id: string;
  summary: string;
  risk_explanation: string;
  facts: string[];
  ai_interpretations: string[];
  detected_attack_patterns: string[];
  investigation_considerations: string[];
  ai_provider: string;
  is_fallback: boolean;
  generated_at: string;
}

export interface ForensicRecommendation {
  recommendation_id: string;
  title: string;
  description: string;
  reason: string;
  severity: string;
  source_signals: string[];
  action_category: string;
  created_at: string;
}

export interface RecommendationsResponse {
  case_id: string;
  total_recommendations: number;
  recommendations: ForensicRecommendation[];
}

export interface GlobalRiskStats {
  average_risk_score: number;
  critical_risk_cases: number;
  high_risk_cases: number;
  moderate_risk_cases: number;
  low_risk_cases: number;
  total_assessed_cases: number;
}

// Milestone 5: Forensic Report Types
export interface ForensicReport {
  report_id: string;
  _id?: string;
  case_id: string;
  case_number: string;
  title: string;
  version: number;
  classification: string;
  file_size: number;
  sha256_hash: string;
  generated_by: string;
  generated_by_name: string;
  compiled_by_name?: string;
  generated_at?: string;
  created_at?: string;
  download_url?: string;
}

export interface ReportListResponse {
  case_id: string;
  total_reports: number;
  reports: ForensicReport[];
}

// ─── Secure Backup & Tamper Detection Types ───────────────────────────────────

export type BackupStatus = 'PROTECTED' | 'TAMPERED' | 'MISSING' | 'CORRUPT';

export interface BackupRecord {
  backup_id: string;
  evidence_id: string;
  case_id: string;
  version: number;
  original_filename: string;
  storage_reference: string;    // Logical reference only — no physical path
  original_sha256: string;
  backup_sha256: string;
  file_size: number;
  created_at: string;
  created_by: string;
  created_by_name: string;
  status: BackupStatus;
}

export interface BackupListResponse {
  evidence_id?: string;
  case_id?: string;
  total_backups: number;
  backups: BackupRecord[];
}

export interface BackupIntegrityResult {
  backup_id: string;
  evidence_id: string;
  case_id: string;
  storage_reference: string;
  original_sha256: string;
  backup_sha256_stored: string;
  backup_sha256_calculated: string;
  backup_status: BackupStatus;
  integrity_verified: boolean;
  message: string;
  verified_at: string;
}

export interface DiaryAmendment {
  amendment_id: string;
  amended_by: string;
  amended_by_name: string;
  timestamp: string;
  reason: string;
  previous_state: Record<string, any>;
  new_state: Record<string, any>;
  amendment_hash: string;
}

export interface DiaryTimelineMilestone {
  time: string;
  location: string;
  activity: string;
}

export interface DiaryEntry {
  _id: string;
  case_id: string;
  entry_number: number;
  entry_code: string;
  investigation_date: string;
  time_info_received?: string | null;
  start_time: string;
  closing_time: string;
  places_visited: string[];
  activities_performed: string;
  findings: string;
  related_evidence_ids: string[];
  witness_references?: string | null;
  is_witness_redacted?: boolean;
  next_steps?: string | null;
  timeline_events?: DiaryTimelineMilestone[];
  raw_input?: string | null;
  detected_language?: string | null;
  created_by: string;
  created_by_name: string;
  created_at: string;
  updated_at: string;
  entry_hash: string;
  previous_hash: string;
  amendments: DiaryAmendment[];
  is_amended: boolean;
}

export interface DiaryEntryCreatePayload {
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
  timeline_events?: DiaryTimelineMilestone[];
  raw_input?: string;
  detected_language?: string;
}

export interface DiaryEntryAmendPayload {
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
  timeline_events?: DiaryTimelineMilestone[];
  raw_input?: string;
  detected_language?: string;
}

export interface DiaryListResponse {
  entries: DiaryEntry[];
  total: number;
  case_id: string;
  legal_disclaimer: string;
}

export interface DiaryVerificationResult {
  entry_id: string;
  entry_number: number;
  stored_hash: string;
  recalculated_hash: string;
  is_valid: boolean;
  previous_hash_matches: boolean;
  status: string;
  verified_at: string;
}

export interface DiaryParseRequest {
  raw_text: string;
  investigation_date?: string;
}

export interface DiaryParseResponse {
  detected_language: string;
  investigation_date: string;
  time_info_received?: string | null;
  start_time: string;
  closing_time: string;
  places_visited: string[];
  activities_performed: string;
  findings: string;
  timeline_events: DiaryTimelineMilestone[];
  witness_references?: string | null;
  next_steps?: string | null;
  ai_provider: string;
  raw_text: string;
}

