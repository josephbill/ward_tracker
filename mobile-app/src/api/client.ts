/**
 * Thin wrapper around the shared Flask backend (Section 3: "one backend").
 * Every write (submitReport) goes through the offline queue in
 * src/offline/queue.ts rather than calling this directly, so it works the
 * same whether the device is online now or syncing later.
 */

// Override for a physical device / different host: the Expo dev tools print
// your machine's LAN IP, e.g. http://192.168.1.20:5055.
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL || "http://localhost:5055";

export type CountyClaimedStatus = "delivered" | "ongoing" | "not_started" | "planned";
export type VerificationStatus = "reported" | "confirmed" | "partially_delivered" | "not_delivered" | "disputed";
export type Claim = "confirmed_delivered" | "not_delivered" | "partially_delivered";

export interface Project {
  id: string;
  ward: string;
  county: string;
  subward: string;
  sector: string;
  project_name: string;
  description: string;
  financial_year: string;
  allocated_amount_ksh: number;
  county_claimed_status: CountyClaimedStatus;
  county_remarks: string;
  source_document: string;
  source_page: number;
  verification_status: VerificationStatus;
  statement: string;
}

export interface ReportPayload {
  project_id: string;
  phone: string;
  claim: Claim;
  channel: "app" | "bluetooth";
  gps_lat?: number | null;
  gps_lon?: number | null;
  lang?: string;
  // Typed or voice-transcribed free text (Section 9 item 1).
  remarks?: string | null;
  // Local device URI (e.g. file://...) — never sent as JSON; submitReport()
  // switches to a multipart upload automatically when this is present.
  photoUri?: string | null;
}

async function apiFetch(path: string, init?: RequestInit) {
  const resp = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${resp.status}`);
  }
  return resp.json();
}

export interface ProjectListResponse {
  projects: Project[];
  count: number;
  delivered_count: number;
  // The county's own claimed completion rate — NOT citizen-verified, hence
  // "purported". See Project.verification_status per project for what
  // residents actually say.
  purported_completion_rate: number;
}

export function fetchProjects(ward: string, lang: string, county?: string): Promise<ProjectListResponse> {
  const params = new URLSearchParams({ ward, lang });
  if (county) params.set("county", county);
  return apiFetch(`/api/projects?${params.toString()}`);
}

export function fetchProject(id: string, lang: string): Promise<Project & { reports: any[] }> {
  return apiFetch(`/api/projects/${encodeURIComponent(id)}?lang=${encodeURIComponent(lang)}`);
}

export function fetchAuditTrail(projectId: string, lang: string) {
  return apiFetch(`/api/projects/${encodeURIComponent(projectId)}/audit-trail?lang=${encodeURIComponent(lang)}`);
}

export function fetchCounties(): Promise<{ counties: string[] }> {
  return apiFetch("/api/counties");
}

export function fetchWards(county?: string): Promise<{ wards: string[] }> {
  const params = county ? `?county=${encodeURIComponent(county)}` : "";
  return apiFetch(`/api/wards${params}`);
}

export interface MyReport {
  id: string;
  project_id: string;
  project_name: string;
  ward: string | null;
  claim: Claim;
  channel: string;
  submitted_at: string;
  active: boolean;
  ledger_ref: string | null;
  verification_status: VerificationStatus | null;
  statement: string | null;
}

export function fetchMyReports(phone: string, lang: string): Promise<{ reports: MyReport[]; count: number }> {
  const params = new URLSearchParams({ phone, lang });
  return apiFetch(`/api/reports/mine?${params.toString()}`);
}

export async function submitReport(payload: ReportPayload) {
  const { photoUri, ...rest } = payload;
  if (!photoUri) {
    return apiFetch("/api/reports", { method: "POST", body: JSON.stringify(rest) });
  }

  // Photo present: switch to multipart so the backend can store the image
  // file (Section 7: "compress/lazy-load photos" — compression happens at
  // capture time in ReportScreen via expo-image-picker's quality option).
  const form = new FormData();
  Object.entries(rest).forEach(([key, value]) => {
    if (value !== undefined && value !== null) form.append(key, String(value));
  });
  form.append("photo", { uri: photoUri, name: "report.jpg", type: "image/jpeg" } as any);

  const resp = await fetch(`${API_BASE_URL}/api/reports`, { method: "POST", body: form });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${resp.status}`);
  }
  return resp.json();
}

export function requestOtp(phone: string) {
  return apiFetch("/api/auth/request-otp", { method: "POST", body: JSON.stringify({ phone }) });
}

export function verifyOtp(phone: string, code: string) {
  return apiFetch("/api/auth/verify-otp", { method: "POST", body: JSON.stringify({ phone, code }) });
}

// --- Voice-to-text (native path only — web transcribes client-side via the
// Web Speech API, see services/voice.ts) ---

export async function transcribeVoice(audioUri: string, lang: string): Promise<{ transcript: string }> {
  const form = new FormData();
  form.append("lang", lang);
  form.append("audio", { uri: audioUri, name: "voice.m4a", type: "audio/m4a" } as any);
  const resp = await fetch(`${API_BASE_URL}/api/voice/transcribe`, { method: "POST", body: form });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${resp.status}`);
  }
  return resp.json();
}

// --- Issues: citizen-reported infrastructure/improvement needs not tied to
// an existing budgeted project (Section 9 item 3) ---

export type IssueCategory = "roads" | "water" | "health" | "education" | "electricity" | "security" | "sanitation" | "other";
export type IssueStatus = "open" | "acknowledged" | "resolved";

export interface Issue {
  id: string;
  county: string;
  ward: string;
  category: IssueCategory;
  title: string;
  description: string | null;
  status: IssueStatus;
  has_photo: boolean;
  gps_lat: number | null;
  gps_lon: number | null;
  ledger_ref: string | null;
  submitted_at: string;
}

export interface IssuePayload {
  phone: string;
  county: string;
  ward: string;
  category: IssueCategory;
  title: string;
  description?: string | null;
  gps_lat?: number | null;
  gps_lon?: number | null;
  photoUri?: string | null;
}

export function fetchIssueCategories(): Promise<{ categories: IssueCategory[] }> {
  return apiFetch("/api/issues/categories");
}

export function fetchIssues(ward: string, county: string): Promise<{ issues: Issue[]; count: number }> {
  const params = new URLSearchParams({ ward, county });
  return apiFetch(`/api/issues?${params.toString()}`);
}

export async function submitIssue(payload: IssuePayload) {
  const { photoUri, ...rest } = payload;
  if (!photoUri) {
    return apiFetch("/api/issues", { method: "POST", body: JSON.stringify(rest) });
  }
  const form = new FormData();
  Object.entries(rest).forEach(([key, value]) => {
    if (value !== undefined && value !== null) form.append(key, String(value));
  });
  form.append("photo", { uri: photoUri, name: "issue.jpg", type: "image/jpeg" } as any);
  const resp = await fetch(`${API_BASE_URL}/api/issues`, { method: "POST", body: form });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${resp.status}`);
  }
  return resp.json();
}
