import { useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { Attendance } from "./Attendance";
import { Members } from "./Members";

const metrics = [
  ["Oy daromadi", "0 UZS", "income"],
  ["Xarajatlar", "0 UZS", "expense"],
  ["Hisoblangan ish haqi", "0 UZS", "payroll"],
  ["Sof foyda", "0 UZS", "profit"],
];

function Dashboard() {
  return <main><p className="eyebrow">SENTYABR 2026</p><h1>Bugungi holat</h1><p className="muted">Hisobchi biznesingizning kunlik moliyaviy ko‘rinishi.</p><section className="metric-grid">{metrics.map(([label, value, kind]) => <article className={`metric ${kind}`} key={label}><span>{label}</span><strong>{value}</strong></article>)}</section><section className="section-heading"><div><p className="eyebrow">NAZORAT</p><h2>Davomat</h2></div><span className="badge">0 / 0</span></section><div className="empty-state"><span className="empty-mark">—</span><h3>Bugun davomat kiritilmagan</h3><p>Jamoa ish kunini qayd etish uchun Davomat bo‘limiga o‘ting.</p></div></main>;
}

function Placeholder({ title }: { title: string }) { return <main><p className="eyebrow">HISOBCHI</p><h1>{title}</h1><div className="empty-state"><span className="empty-mark">+</span><h3>Bo‘lim tayyorlanmoqda</h3><p>Bu ekran keyingi bosqichda ishchi ma’lumotlari bilan to‘ldiriladi.</p></div></main>; }

export function App() {
  const [active, setActive] = useState("Bosh sahifa");
  const nav = [["⌂", "Bosh sahifa", "/"], ["♙", "A’zolar", "/members"], ["◷", "Davomat", "/attendance"], ["₸", "Hisobotlar", "/reports"]];
  return <div className="app-shell"><header><div className="brand"><span className="brand-mark">H</span><span>hisobchi</span></div><button className="profile" aria-label="Profil">SA</button></header><Routes><Route path="/" element={<Dashboard />} /><Route path="/members" element={<Members />} /><Route path="/attendance" element={<Attendance />} /><Route path="*" element={<Placeholder title={active} />} /></Routes><nav>{nav.map(([icon, label, path]) => <NavLink key={label} to={path} onClick={() => setActive(label)} className={({ isActive }) => isActive ? "active" : ""}><span>{icon}</span><small>{label}</small></NavLink>)}</nav></div>;
}
