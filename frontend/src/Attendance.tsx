import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Attendance as AttendanceEntry, formatUzs, membersApi, Member } from "./api";

const today = new Date().toISOString().slice(0, 10);

function AttendanceRow({ member }: { member: Member }) {
  const client = useQueryClient();
  const [date, setDate] = useState(today);
  const [units, setUnits] = useState("2");
  const [note, setNote] = useState("");
  const summary = useQuery({ queryKey: ["attendance-summary", member.id], queryFn: () => membersApi.summary(member.id, new Date().getFullYear(), new Date().getMonth() + 1) });
  const records = useQuery({ queryKey: ["attendance", member.id], queryFn: () => membersApi.attendance(member.id) });
  const mutation = useMutation({
    mutationFn: () => membersApi.addAttendance(member.id, { attendance_date: date, units: Number(units), note: note || null }),
    onSuccess: () => {
      setNote("");
      void client.invalidateQueries({ queryKey: ["attendance"] });
      void client.invalidateQueries({ queryKey: ["attendance-summary"] });
    },
  });

  return <section className="detail-panel"><div className="detail-title"><div><p className="eyebrow">DAVOMAT</p><h2>{member.full_name}</h2></div><span className="badge">{summary.data ? `${summary.data.attendance_units} birligi` : "0 birligi"}</span></div><div className="detail-facts"><span>Oylik ish haqi<strong>{summary.data ? formatUzs(summary.data.estimated_salary_uzs) : "0 so‘m"}</strong></span><span>Yakuniy stavka<strong>{summary.data ? `${summary.data.days_present} kun` : "0 kun"}</strong></span></div><form className="salary-form" onSubmit={(event: FormEvent) => { event.preventDefault(); mutation.mutate(); }}>
    <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
    <select value={units} onChange={(event) => setUnits(event.target.value)}>
      <option value="2">To‘liq kun</option>
      <option value="1">Yarim kun</option>
      <option value="0">Kechikish / yo‘q</option>
    </select>
    <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="Izoh" />
    <button className="primary-button" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Saqlanmoqda..." : "Davomatni saqlash"}</button>
  </form>{mutation.error && <p className="error-text">{mutation.error.message}</p>}{records.data && <div className="salary-list">{records.data.map((item: AttendanceEntry) => <div className="salary-row" key={item.id}><strong>{item.attendance_date}</strong><span>{item.units} birlik{item.units === 1 ? "" : "ka"}{item.note ? ` · ${item.note}` : ""}</span></div>)}</div>}</section>;
}

export function Attendance() {
  const members = useQuery({ queryKey: ["members", true], queryFn: () => membersApi.list(true) });
  const workerMembers = useMemo(() => members.data?.items.filter((member) => member.role === "WORKER") ?? [], [members.data]);

  return <main><div className="page-heading"><div><p className="eyebrow">JAMOA</p><h1>Davomat</h1><p className="muted">Har kuni yarim-kun birliklari bilan hisobot yuritish.</p></div></div>{members.isLoading && <div className="empty-state">Yuklanmoqda...</div>}{members.error && <div className="empty-state"><h3>Davomatni ko‘rib bo‘lmadi</h3><p>{members.error.message}</p></div>}{workerMembers.length === 0 ? <div className="empty-state"><span className="empty-mark">—</span><h3>Davomat uchun ishchilar yo‘q</h3><p>Faol ishchilar ro‘yxati bo‘sh.</p></div> : workerMembers.map((member) => <AttendanceRow key={member.id} member={member} />)}</main>;
}
