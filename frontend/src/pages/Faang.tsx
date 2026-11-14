import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { NavLink, useParams } from "react-router-dom";
import { api, type Faang, type ReportedQ } from "../api";
import { Field } from "../components/Sources";
import { ErrorBox, Icon, Thinking, ago } from "../components/ui";
import { CareerMain } from "./Jobs";

const ROUND: Record<string, string> = {
  coding: "Coding", system_design: "System design", ml_design: "ML system design", ml_concepts: "ML concepts",
  behavioral: "Behavioral", domain: "Domain depth",
};
const DIFF: Record<string, string> = { medium: "Medium", hard: "Hard", very_hard: "Very hard" };

/** Publicly reported interview questions per big-tech company, found with web search and kept until you refresh. */
export default function FaangPage() {
  const list = useQuery({ queryKey: ["faang"], queryFn: api.faangList });
  const { company = "Google" } = useParams();
  return (
    <CareerMain>
      <header>
        <h1 className="h-display text-3xl">FAANG questions</h1>
        <p className="text-muted mt-1">Interview questions candidates and companies have shared publicly, each with its source.</p>
      </header>
      <nav aria-label="Company" className="flex flex-wrap gap-1.5">
        {(list.data?.companies ?? ["Google", "Meta", "Amazon", "Apple", "Netflix", "Microsoft"]).map((c) => (
          <NavLink key={c} to={`/career/faang/${c}`}
            className={({ isActive }) => `px-4 py-2 rounded-full border text-sm font-semibold ${isActive || (c === company) ? "bg-ink text-white border-ink" : "bg-white border-line2 text-body hover:bg-ground"}`}>
            {c}{list.data?.loaded[c] ? <span className="ml-1.5 inline-block w-1.5 h-1.5 rounded-full bg-ok align-middle" aria-label="loaded" /> : null}
          </NavLink>
        ))}
      </nav>
      <CompanyQuestions key={company} company={company} />
    </CareerMain>
  );
}

function CompanyQuestions({ company }: { company: string }) {
  const qc = useQueryClient();
  const key = ["faang", company];
  const q = useQuery({ queryKey: key, queryFn: () => api.faang(company), refetchInterval: (x) => (x.state.data?.status === "running" ? 4000 : false) });
  const domains = useQuery({ queryKey: ["domains"], queryFn: api.domains });
  const [form, setForm] = useState<{ role: string; domain: string; count: number } | null>(null);
  const [round, setRound] = useState("all");
  const refresh = useMutation({
    mutationFn: (b: { role: string; domain: string; count: number }) => api.refreshFaang({ company, ...b }),
    onSuccess: (d) => { qc.setQueryData(key, d); qc.invalidateQueries({ queryKey: ["faang"], exact: true }); },
  });
  if (q.isLoading) return <Thinking label="Loading…" />;
  if (q.isError) return <ErrorBox error={q.error} onRetry={() => q.refetch()} />;
  const d: Faang = q.data!;
  const f = form ?? { role: d.params.role ?? "", domain: d.params.domain ?? "", count: d.params.count ?? 10 };
  const running = d.status === "running" || refresh.isPending;
  const rounds = Array.from(new Set(d.questions.map((x) => x.round)));
  const shown = d.questions.filter((x) => round === "all" || x.round === round);

  return (<>
    <form onSubmit={(e) => { e.preventDefault(); refresh.mutate(f); }} className="card p-5 grid gap-3 md:grid-cols-[1.4fr_1fr_auto_auto] items-end">
      <Field id="fq-role" label="Role">
        <input id="fq-role" className="input" value={f.role} disabled={running} placeholder="e.g. ML Engineer, L5" onChange={(e) => setForm({ ...f, role: e.target.value })} />
      </Field>
      <Field id="fq-dom" label="Domain">
        <select id="fq-dom" className="input" value={f.domain} disabled={running} onChange={(e) => setForm({ ...f, domain: e.target.value })}>
          <option value="">Any</option>
          {domains.data?.map((x) => <option key={x.id} value={x.name}>{x.name}</option>)}
        </select>
      </Field>
      <Field id="fq-n" label="How many">
        <select id="fq-n" className="input" value={f.count} disabled={running} onChange={(e) => setForm({ ...f, count: Number(e.target.value) })}>
          {[5, 10, 15, 20].map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
      </Field>
      <button type="submit" className="btn-primary" disabled={running}>
        <Icon.refresh size={16} /> {running ? "Searching…" : d.questions.length ? "Refresh" : `Find ${company} questions`}
      </button>
      {d.fetched_at && <p className="text-xs text-muted md:col-span-4">Updated {ago(d.fetched_at)}{d.params.role ? ` · ${d.params.role}` : ""}{d.params.domain ? ` · ${d.params.domain}` : ""}. Saved until you refresh.</p>}
    </form>
    {refresh.isError && <ErrorBox error={refresh.error} />}
    {running && d.started_at && <Thinking label="Searching interview reports and prep guides, and checking each source (2–4 minutes)…" since={new Date(d.started_at).getTime()} />}
    {d.status === "failed" && d.error && <ErrorBox error={`The last search didn't finish: ${d.error}`} onRetry={() => refresh.mutate(f)} />}
    {d.status === "idle" && !running && <p className="card p-6 text-body">Pick a role and domain, then press <strong>Find {company} questions</strong>.</p>}

    {d.process && (
      <section className="card p-5 border-l-4 border-l-accent">
        <h2 className="text-[11px] font-bold uppercase tracking-[0.08em] text-accent mb-1.5">How {company} interviews</h2>
        <p className="text-body">{d.process}</p>
      </section>
    )}
    {rounds.length > 1 && (
      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter by round">
        {["all", ...rounds].map((r) => (
          <button key={r} type="button" aria-pressed={round === r} onClick={() => setRound(r)}
            className={`px-3 py-1.5 rounded-full text-sm border ${round === r ? "bg-accent text-white border-accent" : "bg-white border-line2 text-body hover:bg-ground"}`}>
            {r === "all" ? "All rounds" : ROUND[r] ?? r}
          </button>
        ))}
      </div>
    )}
    <ol className="flex flex-col gap-3">
      {shown.map((x, i) => <QCard key={x.url + i} q={x} n={i + 1} />)}
    </ol>
    {d.dropped > 0 && <p className="text-xs text-muted">{d.dropped} left out because their source link didn't open.</p>}
  </>);
}

function QCard({ q, n }: { q: ReportedQ; n: number }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="card p-5 flex flex-col gap-2.5">
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span className="chip bg-accent-soft text-accent-dark">{ROUND[q.round] ?? q.round}</span>
        <span className="chip bg-[#F1F3F6] text-body">{DIFF[q.difficulty] ?? q.difficulty}</span>
        {q.role && <span className="text-muted">{q.role}</span>}
      </div>
      <p className="font-semibold text-[16px] leading-snug"><span className="text-muted mr-1.5">{n}.</span>{q.question}</p>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <button type="button" className="font-semibold text-accent" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "Hide answer outline" : "Answer outline"}
        </button>
        <a href={q.url} target="_blank" rel="noreferrer" className="text-muted hover:text-accent inline-flex items-center gap-1">
          Reported on {q.source_name}{q.year ? `, ${q.year}` : ""} <Icon.external size={13} />
        </a>
        {!q.verified && <span className="text-xs text-muted" title="The site blocks automated checks">link not checked</span>}
      </div>
      {open && (
        <ul className="rounded-xl bg-ground p-4 flex flex-col gap-1.5 text-[14px] text-body">
          {q.answer_outline.map((a, i) => (
            <li key={i} className="flex gap-2"><Icon.check size={14} className="mt-[3px] shrink-0 text-ok" /><span>{a}</span></li>
          ))}
        </ul>
      )}
    </li>
  );
}
