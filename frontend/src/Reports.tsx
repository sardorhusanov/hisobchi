import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { formatUzs, payrollApi } from "./api";

export function Reports() {
  const client = useQueryClient();
  const year = new Date().getFullYear();
  const month = new Date().getMonth() + 1;
  const report = useQuery({ queryKey: ["monthly-report", year, month], queryFn: () => payrollApi.report(year, month) });
  const payroll = useQuery({ queryKey: ["payroll", year, month], queryFn: () => payrollApi.list(year, month) });
  const finalize = useMutation({
    mutationFn: () => payrollApi.finalize(year, month),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["payroll"] });
      void client.invalidateQueries({ queryKey: ["monthly-report"] });
    },
  });

  return <main><div className="page-heading"><div><p className="eyebrow">HISOBOT</p><h1>Oylik hisobot</h1><p className="muted">Daromad, ish haqi va sof foyda</p></div><button className="primary-button" onClick={() => finalize.mutate()} disabled={finalize.isPending}>{finalize.isPending ? "Hisoblanmoqda..." : "Ish haqini yakunlash"}</button></div><div className="metric-grid"><article className="metric income"><span>Daromad</span><strong>{formatUzs(report.data?.income_uzs ?? 0)}</strong></article><article className="metric expense"><span>Xarajat</span><strong>{formatUzs(report.data?.expense_uzs ?? 0)}</strong></article><article className="metric payroll"><span>Ish haqi</span><strong>{formatUzs(report.data?.payroll_uzs ?? 0)}</strong></article><article className="metric profit"><span>Sof foyda</span><strong>{formatUzs(report.data?.profit_uzs ?? 0)}</strong></article></div><section className="salary-list">{payroll.data?.map((item) => <div className="salary-row" key={item.id}><strong>{formatUzs(item.earned_amount_uzs)}</strong><span>{item.attendance_units} davomat birligi · {formatUzs(item.salary_snapshot_uzs)} oylik</span></div>)}</section>{(report.error || finalize.error) && <p className="error-text">{(report.error || finalize.error)?.message}</p>}</main>;
}