import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { membersApi, formatUzs, Member, Role } from "./api";

const roleLabels: Record<Role, string> = { SUPER_ADMIN: "Super admin", OWNER: "Egasi", PARTNER: "Hamkor", WORKER: "Ishchi" };

function MemberForm({ member, onDone }: { member?: Member; onDone: () => void }) {
  const client = useQueryClient();
  const [name, setName] = useState(member?.full_name ?? "");
  const [role, setRole] = useState<Role>(member?.role ?? "WORKER");
  const [phone, setPhone] = useState(member?.phone_number ?? "");
  const mutation = useMutation({
    mutationFn: () => member ? membersApi.update(member.id, { full_name: name, role, phone_number: phone || null }) : membersApi.create({ full_name: name, role, phone_number: phone || null }),
    onSuccess: () => { void client.invalidateQueries({ queryKey: ["members"] }); onDone(); },
  });
  return <form className="form-panel" onSubmit={(event: FormEvent) => { event.preventDefault(); mutation.mutate(); }}><label>To‘liq ism<input required value={name} onChange={(event) => setName(event.target.value)} /></label><label>Rol<select value={role} onChange={(event) => setRole(event.target.value as Role)}>{Object.entries(roleLabels).filter(([value]) => value !== "SUPER_ADMIN").map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label><label>Telefon<input value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+998 90 000 00 00" /></label><div className="form-actions"><button type="button" className="quiet-button" onClick={onDone}>Bekor qilish</button><button className="primary-button" disabled={mutation.isPending}>{mutation.isPending ? "Saqlanmoqda..." : "Saqlash"}</button></div>{mutation.error && <p className="error-text">{mutation.error.message}</p>}</form>;
}

function MemberDetails({ member, onClose }: { member: Member; onClose: () => void }) {
  const client = useQueryClient();
  const salaries = useQuery({ queryKey: ["salaries", member.id], queryFn: () => membersApi.salaries(member.id), enabled: member.role === "WORKER" });
  const [salary, setSalary] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const salaryMutation = useMutation({ mutationFn: () => membersApi.addSalary(member.id, { monthly_salary_uzs: Number(salary), effective_from: date }), onSuccess: () => { setSalary(""); void client.invalidateQueries({ queryKey: ["salaries", member.id] }); } });
  const telegramMutation = useMutation({ mutationFn: () => member.telegram_user_id ? membersApi.unlinkTelegram(member.id) : membersApi.linkTelegram(member.id, Number(prompt("Telegram user ID") ?? 0)), onSuccess: () => void client.invalidateQueries({ queryKey: ["members"] }) });
  return <section className="detail-panel"><button className="back-button" onClick={onClose}>← A’zolar ro‘yxati</button><div className="detail-title"><div><p className="eyebrow">A’ZO PROFILI</p><h2>{member.full_name}</h2><span className={`status ${member.employment_status.toLowerCase()}`}>{member.employment_status === "ACTIVE" ? "Faol" : "Faol emas"}</span></div><span className="role-tag">{roleLabels[member.role]}</span></div><div className="detail-facts"><span>Qo‘shilgan sana<strong>{member.joined_on}</strong></span><span>Telefon<strong>{member.phone_number || "Kiritilmagan"}</strong></span><span>Telegram<strong>{member.telegram_user_id ?? "Ulanmagan"}</strong></span></div><button className="quiet-button wide" onClick={() => telegramMutation.mutate()}>{telegramMutation.isPending ? "..." : member.telegram_user_id ? "Telegramni uzish" : "Telegramni ulash"}</button>{member.role === "WORKER" && <><div className="section-heading compact"><div><p className="eyebrow">ISH HAQI TARIXI</p><h2>Oylik maosh</h2></div></div><div className="salary-list">{salaries.data?.map((item) => <div className="salary-row" key={item.id}><strong>{formatUzs(item.monthly_salary_uzs)}</strong><span>{item.effective_from} — {item.effective_to ?? "hozirgacha"}</span></div>)}</div><form className="salary-form" onSubmit={(event) => { event.preventDefault(); salaryMutation.mutate(); }}><input required type="number" min="0" value={salary} onChange={(event) => setSalary(event.target.value)} placeholder="Oylik maosh, UZS" /><input required type="date" value={date} onChange={(event) => setDate(event.target.value)} /><button className="primary-button" disabled={salaryMutation.isPending}>Maoshni o‘zgartirish</button></form></>}</section>;
}

export function Members() {
  const [active, setActive] = useState<boolean | undefined>(true);
  const [selected, setSelected] = useState<Member>();
  const [formOpen, setFormOpen] = useState(false);
  const members = useQuery({ queryKey: ["members", active], queryFn: () => membersApi.list(active) });
  if (selected) return <MemberDetails member={selected} onClose={() => setSelected(undefined)} />;
  return <main><div className="page-heading"><div><p className="eyebrow">JAMOA</p><h1>A’zolar</h1><p className="muted">Ishchilar, egalar va hamkorlar</p></div><button className="primary-button" onClick={() => setFormOpen(true)}>+ A’zo qo‘shish</button></div><div className="filter-row"><button className={active === true ? "filter active" : "filter"} onClick={() => setActive(true)}>Faol</button><button className={active === false ? "filter active" : "filter"} onClick={() => setActive(false)}>Faol emas</button><button className={active === undefined ? "filter active" : "filter"} onClick={() => setActive(undefined)}>Barchasi</button></div>{formOpen && <MemberForm onDone={() => setFormOpen(false)} />}{members.isLoading && <div className="empty-state">Yuklanmoqda...</div>}{members.error && <div className="empty-state"><h3>A’zolarni yuklab bo‘lmadi</h3><p>{members.error.message}</p></div>}<div className="member-list">{members.data?.items.map((member) => <button className="member-row" key={member.id} onClick={() => setSelected(member)}><span className="avatar">{member.full_name.slice(0, 1).toUpperCase()}</span><span className="member-copy"><strong>{member.full_name}</strong><small>{roleLabels[member.role]} · {member.telegram_user_id ? "Telegram ulangan" : "Telegram ulanmagan"}</small></span><span className="chevron">›</span></button>)}</div></main>;
}
