const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type Role = "SUPER_ADMIN" | "OWNER" | "PARTNER" | "WORKER";
export type EmploymentStatus = "ACTIVE" | "INACTIVE";

export type Member = {
  id: string;
  full_name: string;
  role: Role;
  phone_number: string | null;
  telegram_user_id: number | null;
  employment_status: EmploymentStatus;
  joined_on: string;
  ended_on: string | null;
  notes: string | null;
};

export type Salary = {
  id: string;
  member_id: string;
  monthly_salary_uzs: number;
  effective_from: string;
  effective_to: string | null;
  created_by_user_id: string | null;
};

export type Attendance = {
  id: string;
  member_id: string;
  attendance_date: string;
  units: number;
  note: string | null;
};

export type AttendanceSummary = {
  member_id: string;
  year: number;
  month: number;
  attendance_units: number;
  days_present: number;
  estimated_salary_uzs: number;
  monthly_salary_uzs: number;
};

export type Project = {
  id: string;
  name: string;
  status: "ACTIVE" | "COMPLETED" | "ARCHIVED";
  notes: string | null;
};

export type Transaction = {
  id: string;
  transaction_type: "PROJECT_INCOME" | "PROJECT_EXPENSE" | "GENERAL_EXPENSE";
  amount_uzs: number;
  transaction_date: string;
  project_id: string | null;
  category: string | null;
  note: string | null;
  idempotency_key: string | null;
};

export type FinanceSummary = {
  year: number;
  month: number;
  income_uzs: number;
  expense_uzs: number;
  net_cashflow_uzs: number;
};

export type Payroll = {
  id: string;
  member_id: string;
  year: number;
  month: number;
  salary_snapshot_uzs: number;
  attendance_units: number;
  earned_amount_uzs: number;
};

export type MonthlyReport = FinanceSummary & {
  payroll_uzs: number;
  profit_uzs: number;
  workers_count: number;
};

export type AuditEntry = {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
};

type MemberPage = { items: Member[]; total: number; offset: number; limit: number };

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("hisobchi_access_token");
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  if (!response.ok) throw new Error((await response.json()).detail ?? "So‘rov bajarilmadi");
  return response.json() as Promise<T>;
}

export const membersApi = {
  list: (active?: boolean) => request<MemberPage>(`/api/v1/members?${active === undefined ? "" : `active=${active}`}`),
  get: (id: string) => request<Member>(`/api/v1/members/${id}`),
  create: (payload: object) => request<Member>("/api/v1/members", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: string, payload: object) => request<Member>(`/api/v1/members/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deactivate: (id: string) => request<Member>(`/api/v1/members/${id}/deactivate`, { method: "POST" }),
  linkTelegram: (id: string, telegramUserId: number) => request<Member>(`/api/v1/members/${id}/telegram`, { method: "POST", body: JSON.stringify({ telegram_user_id: telegramUserId }) }),
  unlinkTelegram: (id: string) => request<Member>(`/api/v1/members/${id}/telegram`, { method: "DELETE" }),
  salaries: (id: string) => request<Salary[]>(`/api/v1/members/${id}/salary`),
  addSalary: (id: string, payload: object) => request<Salary>(`/api/v1/members/${id}/salary`, { method: "POST", body: JSON.stringify(payload) }),
  attendance: (id: string) => request<Attendance[]>(`/api/v1/members/${id}/attendance`),
  addAttendance: (id: string, payload: object) => request<Attendance>(`/api/v1/members/${id}/attendance`, { method: "POST", body: JSON.stringify(payload) }),
  summary: (id: string, year: number, month: number) => request<AttendanceSummary>(`/api/v1/members/${id}/attendance/summary?year=${year}&month=${month}`),
};

export const financeApi = {
  projects: () => request<Project[]>("/api/v1/projects"),
  createProject: (payload: object) => request<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(payload) }),
  transactions: () => request<Transaction[]>("/api/v1/transactions"),
  createTransaction: (payload: object) => request<Transaction>("/api/v1/transactions", { method: "POST", body: JSON.stringify(payload) }),
  summary: (year: number, month: number) => request<FinanceSummary>(`/api/v1/finance/summary?year=${year}&month=${month}`),
};

export const payrollApi = {
  list: (year: number, month: number) => request<Payroll[]>(`/api/v1/payroll?year=${year}&month=${month}`),
  finalize: (year: number, month: number) => request<Payroll[]>(`/api/v1/payroll/finalize?year=${year}&month=${month}`, { method: "POST" }),
  report: (year: number, month: number) => request<MonthlyReport>(`/api/v1/reports/monthly?year=${year}&month=${month}`),
};

export const auditApi = {
  list: () => request<AuditEntry[]>("/api/v1/audit?limit=100"),
};

export function formatUzs(value: number): string {
  return `${new Intl.NumberFormat("uz-UZ").format(value)} so‘m`;
}
