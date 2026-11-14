import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { api, type Cert, type CertFind } from "../api";
import { ItemActions, RemovedNote, RemoveFound } from "../components/EditItem";
import { ErrorBox, Icon, Thinking } from "../components/ui";
import { CareerMain } from "./Jobs";

function ago(isoTime: string) {
  const mins = Math.round((Date.now() - new Date(isoTime).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const h = Math.round(mins / 60);
  return h < 48 ? `${h} hour${h === 1 ? "" : "s"} ago` : `${Math.round(h / 24)} days ago`;
}
function fmtDay(d: string) {
  const t = new Date(`${d}T00:00:00`);
  return isNaN(t.getTime()) ? d : t.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
const Chip = ({ children, cls = "bg-[#F1F3F6] text-body" }: { children: React.ReactNode; cls?: string }) =>
  <span className={`chip ${cls}`}>{children}</span>;

/** Certifications worth earning (admin). Hot Jobs has its own page. */
export default function Career() {
  if (location.hash === "#jobs") return <Navigate to="/career/jobs" replace />;  // old link to the jobs tab
  return (
    <CareerMain>
      <header className="flex flex-col gap-1">
        <h1 className="h-display text-3xl">Certifications</h1>
        <p className="text-muted">Agentic AI and Generative AI certifications worth earning. Refresh to check for new ones.</p>
      </header>
      <Certifications />
    </CareerMain>
  );
}

// ---------------------------------------------------------------- certifications

function Certifications() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["certs"], queryFn: api.certifications,
    refetchInterval: (query) => (query.state.data?.refresh.status === "running" ? 4000 : false),
  });
  const refresh = useMutation({ mutationFn: api.refreshCertifications, onSuccess: (d) => qc.setQueryData(["certs"], d) });
  const [tier, setTier] = useState("all");
  const [topOnly, setTopOnly] = useState(false);

  if (q.isLoading) return <Thinking label="Loading…" />;
  if (q.isError) return <ErrorBox error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data!;
  const r = d.refresh;
  const running = r.status === "running" || refresh.isPending;
  const tiers = d.tiers.filter((t) => tier === "all" || t.id === tier);

  return (
    <div className="flex flex-col gap-6">
      <section aria-labelledby="cf-h" className="card p-5 flex flex-col gap-3">
        <div className="flex flex-wrap items-start gap-3">
          <div className="flex-1 min-w-[240px]">
            <h2 id="cf-h" className="font-semibold text-lg">What's new in certifications</h2>
            <p className="text-sm text-muted">
              The list below was researched and checked on {fmtDay(d.checked_on)}. Refresh to have the LLM look for new
              certifications and changes to these ones.{r.fetched_at && <> Last refreshed {ago(r.fetched_at)}.</>}
            </p>
          </div>
          <button type="button" className="btn-primary" disabled={running} onClick={() => refresh.mutate()}>
            <Icon.refresh /> {running ? "Searching…" : "Refresh"}
          </button>
        </div>
        {refresh.isError && <ErrorBox error={refresh.error} />}
        {running && r.started_at && <Thinking label="Searching issuer sites for new and changed certifications…" since={new Date(r.started_at).getTime()} />}
        {r.status === "failed" && r.error && <ErrorBox error={`The last refresh didn't finish: ${r.error}`} onRetry={() => refresh.mutate()} />}
        {r.status === "ready" && (
          <>
            {r.summary && <p className="text-body">{r.summary}</p>}
            {r.items.length === 0 ? <p className="text-sm text-muted">Nothing new or changed found.</p> : (
              <ul className="flex flex-col divide-y divide-line">{r.items.map((c) => <CertFindRow key={c.url} c={c} />)}</ul>
            )}
          </>
        )}
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <label htmlFor="tier" className="text-sm font-semibold">Show</label>
        <select id="tier" className="input w-auto py-1.5" value={tier} onChange={(e) => setTier(e.target.value)}>
          <option value="all">All levels ({d.certs.length})</option>
          {d.tiers.map((t) => <option key={t.id} value={t.id}>{t.title} ({d.certs.filter((c) => c.tier === t.id).length})</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm min-h-[44px]">
          <input type="checkbox" className="w-4 h-4" checked={topOnly} onChange={(e) => setTopOnly(e.target.checked)} />
          Top picks for Agentic AI Architect only
        </label>
      </div>

      <RemovedNote scope="career.certs" count={d.removed} edited={d.certs.some((c) => c._edited)} queryKey={["certs"]} />
      {tiers.map((t) => {
        const list = d.certs.filter((c) => c.tier === t.id && (!topOnly || c.top_pick));
        if (!list.length) return null;
        return (
          <section key={t.id} aria-labelledby={`t-${t.id}`} className="flex flex-col gap-3">
            <div>
              <h2 id={`t-${t.id}`} className="h-display text-2xl">{t.title}</h2>
              <p className="text-muted">{t.summary}</p>
            </div>
            <ul className="grid gap-4 md:grid-cols-2">{list.map((c) => <li key={c.name} className="flex"><CertCard c={c} /></li>)}</ul>
          </section>
        );
      })}
    </div>
  );
}

function CertCard({ c }: { c: Cert }) {
  const facts = [c.code, c.kind, c.price, c.duration, c.validity && `Valid ${c.validity}`].filter(Boolean) as string[];
  return (
    <article className="card p-5 flex flex-col gap-2.5 w-full">
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span className="font-semibold text-muted">{c.issuer}</span>
        {c.top_pick && <Chip cls="bg-ok-soft text-ok-dark">Top pick</Chip>}
        {c.access !== "Open to anyone" && <Chip cls="bg-pp-bg text-pp-fg">Restricted</Chip>}
        <span className="ml-auto">
          <ItemActions scope="career.certs" itemKey={c._key ?? c.name} title={c.name} queryKey={["certs"]} fields={[
            { name: "price", label: "Price", value: c.price }, { name: "duration", label: "Duration", value: c.duration },
            { name: "validity", label: "Validity", value: c.validity }, { name: "format", label: "Format", value: c.format, long: true },
            { name: "focus", label: "What it tests", value: c.focus, long: true }, { name: "fit", label: "For you", value: c.fit, long: true },
            { name: "notes", label: "Note", value: c.notes, long: true }]} />
        </span>
      </div>
      <h3 className="font-semibold text-lg leading-snug">
        <a href={c.url} target="_blank" rel="noreferrer" className="hover:text-accent inline-flex items-baseline gap-1.5">
          {c.name} <Icon.external size={14} className="text-muted shrink-0" />
        </a>
      </h3>
      <div className="flex flex-wrap gap-1.5">{facts.map((f) => <Chip key={f}>{f}</Chip>)}</div>
      {c.focus && <p className="text-sm text-body"><span className="font-semibold">Tests: </span>{c.focus}</p>}
      {c.fit && <p className="text-sm p-3 rounded-lg bg-[#F6F8FF] border border-accent-line"><span className="font-semibold">For you: </span>{c.fit}</p>}
      {c.format && <p className="text-xs text-muted"><span className="font-semibold text-body">Format:</span> {c.format}</p>}
      {c.access !== "Open to anyone" && <p className="text-xs text-muted"><span className="font-semibold text-body">Who can take it:</span> {c.access}</p>}
      {c.notes && <p className="text-xs text-muted"><span className="font-semibold text-body">Note:</span> {c.notes}</p>}
    </article>
  );
}

function CertFindRow({ c }: { c: CertFind }) {
  return (
    <li className="py-3 flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <Chip cls={c.change === "new" ? "bg-ok-soft text-ok-dark" : "bg-accent-soft text-accent-dark"}>{c.change === "new" ? "New" : "Updated"}</Chip>
        <span className="font-semibold text-muted">{c.issuer}{c.code && ` · ${c.code}`}</span>
        {c.price && <Chip>{c.price}</Chip>}
        {!c.verified && <Chip cls="bg-[#F1F3F6] text-muted">Link not verified</Chip>}
        <span className="ml-auto"><RemoveFound job="certs" url={c.url} title={c.name} queryKey={["certs"]} /></span>
      </div>
      <a href={c.url} target="_blank" rel="noreferrer" className="font-semibold hover:text-accent">{c.name}</a>
      {c.what_changed && <p className="text-sm text-body">{c.what_changed}</p>}
      <p className="text-sm text-muted">{c.focus} {c.fit}</p>
    </li>
  );
}
