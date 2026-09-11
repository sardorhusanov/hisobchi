import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { financeApi, formatUzs } from "./api";

export function Projects() {
  const client = useQueryClient();
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const projects = useQuery({ queryKey: ["projects"], queryFn: financeApi.projects });
  const summary = useQuery({
    queryKey: ["finance-summary"],
    queryFn: () => financeApi.summary(new Date().getFullYear(), new Date().getMonth() + 1),
  });
  const transactions = useQuery({ queryKey: ["transactions"], queryFn: financeApi.transactions });
  const projectMutation = useMutation({
    mutationFn: () => financeApi.createProject({ name, status: "ACTIVE" }),
    onSuccess: () => {
      setName("");
      void client.invalidateQueries({ queryKey: ["projects"] });
    },
  });
  const incomeMutation = useMutation({
    mutationFn: () => financeApi.createTransaction({
      transaction_type: "PROJECT_INCOME",
      amount_uzs: Number(amount),
      transaction_date: new Date().toISOString().slice(0, 10),
    }),
    onSuccess: () => {
      setAmount("");
      void client.invalidateQueries({ queryKey: ["transactions"] });
      void client.invalidateQueries({ queryKey: ["finance-summary"] });
    },
  });

  return <main><div className="page-heading"><div><p className="eyebrow">MOLIYA</p><h1>Loyihalar</h1><p className="muted">Loyiha tushumlari va xarajatlari</p></div></div><div className="metric-grid"><article className="metric income"><span>Daromad</span><strong>{formatUzs(summary.data?.income_uzs ?? 0)}</strong></article><article className="metric expense"><span>Xarajat</span><strong>{formatUzs(summary.data?.expense_uzs ?? 0)}</strong></article><article className="metric profit"><span>Sof oqim</span><strong>{formatUzs(summary.data?.net_cashflow_uzs ?? 0)}</strong></article></div><form className="form-panel" onSubmit={(event: FormEvent) => { event.preventDefault(); projectMutation.mutate(); }}><label>Yangi loyiha<input required value={name} onChange={(event) => setName(event.target.value)} placeholder="Masalan, Oshxona ta’miri" /></label><button className="primary-button" disabled={projectMutation.isPending}>Loyiha qo‘shish</button></form><section className="member-list">{projects.data?.map((project) => <div className="member-row" key={project.id}><span className="avatar">L</span><span className="member-copy"><strong>{project.name}</strong><small>{project.status === "ACTIVE" ? "Faol loyiha" : project.status}</small></span></div>)}</section><form className="salary-form" onSubmit={(event: FormEvent) => { event.preventDefault(); incomeMutation.mutate(); }}><input required type="number" min="1" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="Daromad, UZS" /><button className="primary-button" disabled={incomeMutation.isPending}>Daromad kiritish</button></form><section className="salary-list">{transactions.data?.slice(0, 10).map((transaction) => <div className="salary-row" key={transaction.id}><strong>{formatUzs(transaction.amount_uzs)}</strong><span>{transaction.transaction_date} · {transaction.transaction_type}</span></div>)}</section></main>;
}