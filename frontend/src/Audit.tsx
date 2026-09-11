import { useQuery } from "@tanstack/react-query";

import { auditApi } from "./api";

export function Audit() {
  const entries = useQuery({ queryKey: ["audit"], queryFn: auditApi.list });
  return <main><div className="page-heading"><div><p className="eyebrow">NAZORAT</p><h1>Harakatlar tarixi</h1><p className="muted">Hisobchi tizimidagi muhim o‘zgarishlar</p></div></div>{entries.isLoading && <div className="empty-state">Yuklanmoqda...</div>}{entries.error && <div className="empty-state"><h3>Tarixni yuklab bo‘lmadi</h3><p>{entries.error.message}</p></div>}<section className="salary-list">{entries.data?.map((entry) => <div className="salary-row" key={entry.id}><strong>{entry.action}</strong><span>{entry.entity_type} · {entry.created_at.slice(0, 19).replace("T", " ")}</span></div>)}</section>{entries.data?.length === 0 && <div className="empty-state"><h3>Hozircha harakatlar yo‘q</h3></div>}</main>;
}