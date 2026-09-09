export type Severity = "low" | "medium" | "high";
export type ChangeType = "NEW_CONSTRUCTION" | "VERTICAL_ADDITION" | "DEMOLITION" | "FACADE_ALTERATION";
export type Status = "pending" | "approved" | "rejected" | "escalated" | "dropped" | "needs_human_rewrite";

export interface Officer { id: string; username: string; display_name: string; role: string; locale: string }
export interface ChangeSummary {
  id: string; building_id: string | null; zone: string; chowkri_id: string | null; change_type: ChangeType;
  change_prob: number; calibration_date: string | null; status: Status; priority: string;
  epoch_before: string; epoch_after: string; severity: Severity | null; created_at: string;
}
export interface Finding { id: string; claim: string; clause_id: string; evidence_ref: string; severity: Severity; is_final: boolean }
export interface Clause { clause_id: string; path: string; text: string; source_page: number }
export interface Decision { id: string; change_id: string; officer_id: string; officer_name: string; decision: string; reason: string | null; created_at: string }
export interface ChangeDetail extends ChangeSummary {
  facade_class: string | null; before_uri: string; after_uri: string; mask_uri: string;
  triage_decision: string | null; triage_reason: string | null; verifier_verdict: string | null;
  verifier_notes: string[]; revision_count: number; findings: Finding[]; clauses: Clause[];
  decisions: Decision[]; centroid: [number, number];
}
export interface QueuePage { items: ChangeSummary[]; total: number }
export interface AuditRow { id: number; ts: string; actor: string; action: string; change_id: string | null; payload: Record<string, unknown>; git_sha: string | null; model_ids: Record<string, unknown>; prompt_versions: Record<string, unknown>; total_tokens: number }
export interface Visit { id: string; change_id: string; scheduled_for: string; assignee_id: string | null; assignee_name: string | null; status: string; field_notes: string | null; change: ChangeSummary }
export interface Notification { id: string; kind: string; title: string; body: string; change_id: string | null; created_at: string; read_at: string | null }
export interface Fairness { status: "measured" | "BLOCKED"; reason?: string | null; fpr_by_chowkri: Record<string, number>; n_by_chowkri: Record<string, number>; disparity_ratio: number | null; max_ratio: number; passes: boolean | null }
export interface HealthMetrics { pipeline: Record<string, unknown> | null; calibration: Record<string, unknown> | null; retrieval: Record<string, unknown>; fairness: Fairness; queue: Record<string, number>; runs: Array<Record<string, unknown>>; agreement_rate: number | null }
export interface AggregateCell { chowkri_id: string; zone: string; counts_by_type: Record<string, number>; counts_by_status: Record<string, number> }
export interface Aggregate { cells: AggregateCell[]; window: [string, string] | null; attribution: string }
export interface Timeline { building_id: string; zone: string; chowkri_id: string | null; entries: Array<{ change: ChangeSummary; decisions: Decision[] }> }
