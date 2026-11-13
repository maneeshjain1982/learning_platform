import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Cert, type CertFind, type JobPosting, type JobsParams } from "../api";
import { ItemActions, RemovedNote, RemoveFound } from "../components/EditItem";
import { ErrorBox, Icon, Thinking } from "../components/ui";

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

export default function Career() {
  const [tab, setTab] = useState<"certs" | "jobs">(() => (location.hash === "#jobs" ? "jobs" : "certs"));
  useEffect(() => { history.replaceState(null, "", tab === "jobs" ? "#jobs" : "#certifications"); }, [tab]);
  return (
    <main className="max-w-[1100px] mx-auto w-full px-4 sm:px-8 py-8 flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <h1 className="h-display text-3xl">Career</h1>
        <p className="text-body max-w-[760px]">
          Certifications worth earning and the jobs hiring now for Agentic AI and Generative AI. Both can be refreshed:
          the LLM searches the web and every link is checked before it's shown.
        </p>
      </header>
      <div role="tablist" aria-label="Career sections" className="flex gap-1 border-b border-line">
        {([["certs", "Certifications"], ["jobs", "Hot jobs"]] as const).map(([id, label]) => (
          <button key={id} role="tab" type="button" aria-selected={tab === id} aria-controls={`panel-${id}`} id={`tab-${id}`}
            onClick={() => setTab(id)}
            className={`px-4 min-h-[44px] -mb-px border-b-2 font-semibold ${tab === id ? "border-accent text-accent-dark" : "border-transparent text-body hover:text-ink"}`}>
            {label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "certs" ? <Certifications /> : <HotJobs />}
      </div>
    </main>
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

// ---------------------------------------------------------------- jobs

function HotJobs() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["jobs"], queryFn: api.jobs,
    refetchInterval: (query) => (query.state.data?.status === "running" ? 4000 : false),
  });
  const [form, setForm] = useState<JobsParams | null>(null);
  const refresh = useMutation({ mutationFn: (b: JobsParams) => api.refreshJobs(b), onSuccess: (d) => qc.setQueryData(["jobs"], d) });
  const [skill, setSkill] = useState<string | null>(null);

  if (q.isLoading) return <Thinking label="Loading…" />;
  if (q.isError) return <ErrorBox error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data!;
  const f = form ?? d.params;
  const running = d.status === "running" || refresh.isPending;
  const set = <K extends keyof JobsParams>(k: K, v: JobsParams[K]) => setForm({ ...f, [k]: v });
  const onSubmit = (e: FormEvent) => { e.preventDefault(); refresh.mutate(f); };
  const tagsOf = (j: JobPosting) => j.skill_tags ?? j.must_have;
  const shown = skill ? d.jobs.filter((j) => tagsOf(j).includes(skill)) : d.jobs;

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={onSubmit} className="card p-5 grid gap-3 md:grid-cols-[2fr_1fr_auto_auto] items-end">
        <div className="flex flex-col gap-1">
          <label htmlFor="roles" className="label text-sm">Roles</label>
          <input id="roles" className="input" value={f.roles} disabled={running} onChange={(e) => set("roles", e.target.value)} />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="loc" className="label text-sm">Location</label>
          <input id="loc" className="input" value={f.location} disabled={running} placeholder="Anywhere, incl. remote"
            onChange={(e) => set("location", e.target.value)} />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="cnt" className="label text-sm">How many</label>
          <select id="cnt" className="input w-auto" value={f.count} disabled={running} onChange={(e) => set("count", Number(e.target.value))}>
            {[5, 10, 15, 20].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <button type="submit" className="btn-primary" disabled={running || f.roles.trim().length < 3}>
          <Icon.search /> {running ? "Searching…" : d.jobs.length ? "Refresh jobs" : "Find jobs"}
        </button>
        <p className="text-xs text-muted md:col-span-4">
          The LLM searches company career pages and job boards for postings from the last 30 days and breaks down each
          job description.{d.fetched_at && <> Last searched {ago(d.fetched_at)}.</>} Postings close quickly, so check the link before applying.
        </p>
      </form>

      {refresh.isError && <ErrorBox error={refresh.error} />}
      {running && d.started_at && <Thinking label="Searching for open roles and reading their job descriptions. This usually takes 2–5 minutes…" since={new Date(d.started_at).getTime()} />}
      {d.status === "failed" && d.error && <ErrorBox error={`The last search didn't finish: ${d.error}`} onRetry={() => refresh.mutate(f)} />}
      {d.status === "idle" && !running && <p className="text-body">No search yet. Set the roles and location, then press <span className="font-semibold">Find jobs</span>.</p>}

      {d.jobs.length > 0 && (
        <>
          <section aria-labelledby="mk-h" className="card p-5 flex flex-col gap-3">
            <h2 id="mk-h" className="font-semibold text-lg">The market right now</h2>
            {d.market_summary && <p className="text-body">{d.market_summary}</p>}
            {d.trends.length > 0 && <ul className="list-disc pl-5 text-sm text-body flex flex-col gap-0.5">{d.trends.map((t) => <li key={t}>{t}</li>)}</ul>}
            {d.top_skills.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="text-sm font-semibold">Most-asked skills in these JDs <span className="font-normal text-muted">(select one to filter)</span></p>
                <div className="flex flex-wrap gap-1.5">
                  {d.top_skills.map((s) => (
                    <button key={s.skill} type="button" aria-pressed={skill === s.skill} onClick={() => setSkill(skill === s.skill ? null : s.skill)}
                      className={`min-h-[36px] px-3 rounded-full border text-sm ${skill === s.skill ? "bg-accent text-white border-accent" : "bg-white border-line2 text-body hover:bg-ground"}`}>
                      {s.skill} <span className={skill === s.skill ? "text-white/80" : "text-muted"}>×{s.count}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </section>
          <p className="text-sm text-muted">
            {shown.length} of {d.jobs.length} jobs{skill && <> asking for <span className="font-semibold text-body">{skill}</span></>}
            {d.dropped > 0 && <> · {d.dropped} left out because the posting link didn't open</>}
          </p>
          <ul className="flex flex-col gap-4">{shown.map((j) => <li key={j.url}><JobCard j={j} /></li>)}</ul>
        </>
      )}
    </div>
  );
}

function jdText(j: JobPosting) {
  return [
    `${j.title} at ${j.company} (${j.location})`, "", j.summary, "",
    "Responsibilities:", ...j.responsibilities.map((r) => `- ${r}`), "",
    "Must have:", ...j.must_have.map((r) => `- ${r}`),
    ...(j.nice_to_have.length ? ["", "Nice to have:", ...j.nice_to_have.map((r) => `- ${r}`)] : []),
    "", `Posting: ${j.url}`,
  ].join("\n");
}

function JobCard({ j }: { j: JobPosting }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const facts = [j.location, j.work_mode !== "unknown" && j.work_mode, j.seniority, j.salary].filter(Boolean) as string[];
  const toPrep = () => navigate("/upskill/new", {
    state: { prefill: { role_title: j.title, company: j.company, jd_text: jdText(j) } },
  });
  return (
    <article className="card p-5 flex flex-col gap-2.5">
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span className="font-semibold text-body">{j.company}</span>
        {j.posted && <span className="text-muted">Posted {fmtDay(j.posted)}</span>}
        {j.why_hot && <Chip cls="bg-ok-soft text-ok-dark">{j.why_hot}</Chip>}
        {!j.verified && <Chip cls="bg-[#F1F3F6] text-muted">Link not verified</Chip>}
        <span className="ml-auto"><RemoveFound job="jobs" url={j.url} title={j.title} queryKey={["jobs"]} /></span>
      </div>
      <h3 className="font-semibold text-lg leading-snug">
        <a href={j.url} target="_blank" rel="noreferrer" className="hover:text-accent inline-flex items-baseline gap-1.5">
          {j.title} <Icon.external size={14} className="text-muted shrink-0" />
        </a>
      </h3>
      <div className="flex flex-wrap gap-1.5">{facts.map((f) => <Chip key={f}>{f}</Chip>)}</div>
      <p className="text-body">{j.summary}</p>
      {(j.skill_tags ?? []).length > 0 && (
        <div className="flex flex-wrap gap-1.5">{j.skill_tags!.map((s) => <Chip key={s} cls="bg-accent-soft text-accent-dark">{s}</Chip>)}</div>
      )}
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-outline btn-sm" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "Hide JD breakdown" : "Show JD breakdown"}
        </button>
        <button type="button" className="btn-outline btn-sm" onClick={toPrep}>Prepare in Upskill Prep</button>
      </div>
      {open && (
        <div className="grid gap-4 md:grid-cols-2 text-sm pt-1">
          <div>
            <p className="font-semibold mb-1">Responsibilities</p>
            <ul className="list-disc pl-5 text-body flex flex-col gap-0.5">{j.responsibilities.map((r) => <li key={r}>{r}</li>)}</ul>
          </div>
          <div className="flex flex-col gap-3">
            <div>
              <p className="font-semibold mb-1">Must have</p>
              <ul className="list-disc pl-5 text-body flex flex-col gap-0.5">{j.must_have.map((r) => <li key={r}>{r}</li>)}</ul>
            </div>
            {j.nice_to_have.length > 0 && (
              <div>
                <p className="font-semibold mb-1">Nice to have</p>
                <ul className="list-disc pl-5 text-body flex flex-col gap-0.5">{j.nice_to_have.map((r) => <li key={r}>{r}</li>)}</ul>
              </div>
            )}
          </div>
        </div>
      )}
    </article>
  );
}
