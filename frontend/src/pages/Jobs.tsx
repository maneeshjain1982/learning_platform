import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type CompanyType, type InterviewConfig, type JobPosting, type Jobs as JobsT, type JobsParams, type SearchParams, type Seniority, type WorkMode } from "../api";
import { ProfileCard, cap, useProfile } from "./CVProfile";
import { Dialog, RemoveFound } from "../components/EditItem";
import { Field } from "../components/Sources";
import { ErrorBox, Icon, Thinking, ago, fmtDay } from "../components/ui";

export const COUNTRIES = [
  "India", "United States", "United Kingdom", "Canada", "Germany", "Netherlands", "France", "Ireland", "Switzerland",
  "Singapore", "United Arab Emirates", "Australia", "Japan", "South Korea",
];
const Chip = ({ children, cls = "bg-[#F1F3F6] text-body" }: { children: ReactNode; cls?: string }) =>
  <span className={`chip ${cls}`}>{children}</span>;

export function CareerMain({ children }: { children: ReactNode }) {
  return <main className="w-full max-w-[1180px] px-4 sm:px-8 lg:px-10 py-6 lg:py-8 flex flex-col gap-6">{children}</main>;
}

export function CountrySelect({ id, value, onChange, disabled }: { id: string; value: string; onChange: (v: string) => void; disabled?: boolean }) {
  return (
    <select id={id} className="input" value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
      <option value="">Anywhere</option>
      <option value="Remote">Remote only</option>
      {COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}
    </select>
  );
}

/** Hot Jobs (admin): the most attractive open roles by country, refreshed on demand. */
export default function Jobs() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["jobs"], queryFn: api.jobs,
    refetchInterval: (query) => (query.state.data?.status === "running" ? 4000 : false),
  });
  const [form, setForm] = useState<JobsParams | null>(null);
  const refresh = useMutation({ mutationFn: (b: JobsParams) => api.refreshJobs(b), onSuccess: (d) => qc.setQueryData(["jobs"], d) });

  if (q.isLoading) return <CareerMain><Thinking label="Loading…" /></CareerMain>;
  if (q.isError) return <CareerMain><ErrorBox error={q.error} onRetry={() => q.refetch()} /></CareerMain>;
  const d = q.data!;
  const f: JobsParams = form ?? { ...d.params, country: d.params.country ?? "" };
  const running = d.status === "running" || refresh.isPending;
  const set = <K extends keyof JobsParams>(k: K, v: JobsParams[K]) => setForm({ ...f, [k]: v });
  const onSubmit = (e: FormEvent) => { e.preventDefault(); refresh.mutate(f); };
  const searchedIn = [d.params.location, d.params.country || "Anywhere"].filter(Boolean).join(", ");

  return (
    <CareerMain>
      <header>
        <h1 className="h-display text-3xl">Hot Jobs</h1>
        <p className="text-muted mt-1">The most attractive open roles from the last 30 days.</p>
      </header>
      <form onSubmit={onSubmit} className="card p-5 grid gap-3 md:grid-cols-[2fr_1.2fr_1fr_auto_auto] items-end">
        <Field id="roles" label="Roles"><input id="roles" className="input" value={f.roles} disabled={running} onChange={(e) => set("roles", e.target.value)} /></Field>
        <Field id="country" label="Country"><CountrySelect id="country" value={f.country} disabled={running} onChange={(v) => set("country", v)} /></Field>
        <Field id="city" label="City (optional)">
          <input id="city" className="input" value={f.location} disabled={running || f.country === "Remote"} placeholder="e.g. Bengaluru" onChange={(e) => set("location", e.target.value)} />
        </Field>
        <Field id="cnt" label="How many">
          <select id="cnt" className="input w-auto" value={f.count} disabled={running} onChange={(e) => set("count", Number(e.target.value))}>
            {[5, 8, 10, 15, 20].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </Field>
        <button type="submit" className="btn-primary" disabled={running || f.roles.trim().length < 3}>
          <Icon.refresh size={16} /> {running ? "Searching…" : d.jobs.length ? "Refresh" : "Find jobs"}
        </button>
        {d.fetched_at && <p className="text-xs text-muted md:col-span-5">Last searched {ago(d.fetched_at)} · {searchedIn}. Postings close quickly; check the link before applying.</p>}
      </form>
      {refresh.isError && <ErrorBox error={refresh.error} />}
      <JobResults d={d} running={running} job="jobs" queryKey={["jobs"]} onRetry={() => refresh.mutate(f)}
        idle={<>Choose roles and a country, then press <strong>Find jobs</strong>.</>} />
    </CareerMain>
  );
}

/** Job search (admin): jobs matching your CV, or your own search; filters for experience, level, work mode and more. */
export function JobSearch() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["job-search"], queryFn: api.jobSearch,
    refetchInterval: (query) => (query.state.data?.status === "running" ? 4000 : false),
  });
  const domains = useQuery({ queryKey: ["domains"], queryFn: api.domains });
  const prof = useProfile();
  const [form, setForm] = useState<SearchParams | null>(null);
  const run = useMutation({ mutationFn: (b: SearchParams) => api.runJobSearch(b), onSuccess: (d) => qc.setQueryData(["job-search"], d) });

  if (q.isLoading || prof.isLoading) return <CareerMain><Thinking label="Loading…" /></CareerMain>;
  if (q.isError) return <CareerMain><ErrorBox error={q.error} onRetry={() => q.refetch()} /></CareerMain>;
  const d = q.data!;
  const profile = prof.data?.profile;
  const f: SearchParams = form ?? { ...d.params, use_profile: d.params.use_profile || (!d.fetched_at && !!profile) };
  const useCV = f.use_profile && !!profile;
  const running = d.status === "running" || run.isPending;
  const set = <K extends keyof SearchParams>(k: K, v: SearchParams[K]) => setForm({ ...f, [k]: v });
  const p = d.params;
  const what = [p.use_profile && "Matching my CV", p.query, p.domain && `${p.domain} domain`].filter(Boolean).join(" · ");
  const extras = [f.work_mode !== "any", f.company_type !== "any", f.posted_days !== 30, f.min_salary, f.visa, f.extra].filter(Boolean).length;
  const canRun = useCV || !!f.query.trim() || !!f.domain;

  return (
    <CareerMain>
      <header>
        <h1 className="h-display text-3xl">Job search</h1>
        <p className="text-muted mt-1">Find jobs that match your CV, or search by role and domain.</p>
      </header>
      <ProfileCard />
      <form onSubmit={(e) => { e.preventDefault(); run.mutate({ ...f, use_profile: useCV }); }} className="card p-5 flex flex-col gap-4">
        <div role="radiogroup" aria-label="Search mode" className="inline-flex self-start rounded-lg border border-line2 p-0.5 bg-ground">
          {[{ v: true, l: "Matching my CV" }, { v: false, l: "Custom search" }].map((m) => (
            <button key={m.l} type="button" role="radio" aria-checked={useCV === m.v} disabled={running || (m.v && !profile)}
              title={m.v && !profile ? "Add your CV first" : undefined} onClick={() => set("use_profile", m.v)}
              className={`px-3 min-h-[34px] rounded-md text-sm font-medium disabled:opacity-50 ${useCV === m.v ? "bg-white shadow-sm text-ink" : "text-muted hover:text-ink"}`}>
              {m.l}
            </button>
          ))}
        </div>
        <div className="grid gap-3 md:grid-cols-6 items-end">
          <div className="md:col-span-3"><Field id="sq" label={useCV ? "Narrow it down (optional)" : "Search"}>
            <input id="sq" className="input" value={f.query} disabled={running}
              placeholder={useCV ? `e.g. ${profile?.roles[0] ?? "Staff ML Engineer"}` : "Role, company or skills"} onChange={(e) => set("query", e.target.value)} />
          </Field></div>
          <div className="md:col-span-3"><Field id="sd" label="Domain">
            <select id="sd" className="input" value={f.domain} disabled={running} onChange={(e) => set("domain", e.target.value)}>
              <option value="">{useCV ? "From my CV" : "Any domain"}</option>
              {domains.data?.map((x) => <option key={x.id} value={x.name}>{x.name}</option>)}
            </select>
          </Field></div>
          <Field id="sy" label="Years of experience">
            <input id="sy" type="number" min={0} max={60} className="input" disabled={running} value={f.years ?? ""}
              placeholder={useCV && profile ? String(profile.years) : "Any"} onChange={(e) => set("years", e.target.value === "" ? null : Number(e.target.value))} />
          </Field>
          <Field id="sl" label="Level">
            <select id="sl" className="input" value={f.level} disabled={running} onChange={(e) => set("level", e.target.value)}>
              <option value="">{useCV && profile ? `${cap(profile.level)} (CV)` : "Any"}</option>
              {["mid", "senior", "staff", "principal", "lead", "manager", "director"].map((l) => <option key={l} value={l}>{cap(l)}</option>)}
            </select>
          </Field>
          <div className="md:col-span-2"><Field id="sc" label="Country"><CountrySelect id="sc" value={f.country} disabled={running} onChange={(v) => set("country", v)} /></Field></div>
          <div className="md:col-span-2"><Field id="scity" label="City (optional)">
            <input id="scity" className="input" value={f.location} disabled={running || f.country === "Remote"} onChange={(e) => set("location", e.target.value)} />
          </Field></div>
        </div>
        <details className="group/more" open={extras > 0 ? true : undefined}>
          <summary className="cursor-pointer text-sm font-medium text-accent-dark inline-flex items-center gap-1.5 list-none">
            <Icon.chevron size={14} className="transition-transform group-open/more:rotate-90" /> More filters{extras > 0 && ` (${extras})`}
          </summary>
          <div className="grid gap-3 md:grid-cols-6 items-end pt-3">
            <div className="md:col-span-2"><Field id="sw" label="Work mode">
              <select id="sw" className="input" value={f.work_mode} disabled={running} onChange={(e) => set("work_mode", e.target.value as WorkMode)}>
                <option value="any">Any</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="onsite">On-site</option>
              </select>
            </Field></div>
            <div className="md:col-span-2"><Field id="sct" label="Company type">
              <select id="sct" className="input" value={f.company_type} disabled={running} onChange={(e) => set("company_type", e.target.value as CompanyType)}>
                <option value="any">Any</option><option value="big_tech">Big Tech and AI labs</option><option value="startup">Startups</option><option value="enterprise">Enterprises</option>
              </select>
            </Field></div>
            <div className="md:col-span-2"><Field id="sp" label="Posted within">
              <select id="sp" className="input" value={f.posted_days} disabled={running} onChange={(e) => set("posted_days", Number(e.target.value) as 7 | 14 | 30)}>
                <option value={7}>7 days</option><option value={14}>14 days</option><option value={30}>30 days</option>
              </select>
            </Field></div>
            <div className="md:col-span-2"><Field id="ss" label="Minimum salary (optional)">
              <input id="ss" className="input" value={f.min_salary} disabled={running} placeholder="e.g. ₹60 LPA or $200k" onChange={(e) => set("min_salary", e.target.value)} />
            </Field></div>
            <div className="md:col-span-3"><Field id="sx" label="Anything else (optional)">
              <input id="sx" className="input" value={f.extra} disabled={running} placeholder="e.g. speech products, no defence" onChange={(e) => set("extra", e.target.value)} />
            </Field></div>
            <label className="md:col-span-1 flex items-center gap-2 text-sm min-h-[42px]">
              <input type="checkbox" checked={f.visa} disabled={running} onChange={(e) => set("visa", e.target.checked)} /> Visa sponsorship
            </label>
          </div>
        </details>
        <div className="flex flex-wrap items-center gap-3">
          <label htmlFor="scnt" className="text-sm text-muted">How many</label>
          <select id="scnt" className="input w-auto" value={f.count} disabled={running} onChange={(e) => set("count", Number(e.target.value))}>
            {[5, 8, 10, 15, 20].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          <button type="submit" className="btn-primary ml-auto" disabled={running || !canRun}>
            <Icon.search size={16} /> {running ? "Searching…" : useCV ? "Find matching jobs" : "Search"}
          </button>
        </div>
        {d.fetched_at && <p className="text-xs text-muted">Last search: {what} · {[p.location, p.country || "Anywhere"].filter(Boolean).join(", ")} · {ago(d.fetched_at)}</p>}
      </form>
      {run.isError && <ErrorBox error={run.error} />}
      <JobResults d={d} running={running} job="job-search" queryKey={["job-search"]} onRetry={() => run.mutate(f)}
        idle={profile ? <>Press <strong>Find matching jobs</strong> to search with your CV.</> : <>Add your CV, or type a search or pick a domain, then press <strong>Search</strong>.</>} />
    </CareerMain>
  );
}

function JobResults({ d, running, job, queryKey, onRetry, idle }: {
  d: Omit<JobsT, "params">; running: boolean; job: string; queryKey: string[]; onRetry: () => void; idle: ReactNode;
}) {
  const preps = useQuery({ queryKey: ["interviews"], queryFn: api.interviews });
  const [skill, setSkill] = useState<string | null>(null);
  const [prepFor, setPrepFor] = useState<JobPosting | null>(null);
  const tagsOf = (j: JobPosting) => j.skill_tags ?? j.must_have;
  const shown = skill ? d.jobs.filter((j) => tagsOf(j).includes(skill)) : d.jobs;
  const prepOf = (j: JobPosting) => preps.data?.find((p) => p.role_title === j.title && p.company === j.company);
  return (<>
    {running && d.started_at && <Thinking label="Searching career pages and job boards, and reading each JD (2–5 minutes)…" since={new Date(d.started_at).getTime()} />}
    {d.status === "failed" && d.error && <ErrorBox error={`The last search didn't finish: ${d.error}`} onRetry={onRetry} />}
    {d.status === "idle" && !running && <p className="card p-6 text-body">{idle}</p>}
    {d.status === "ready" && d.jobs.length === 0 && !running && <p className="card p-6 text-body">No open postings could be confirmed. Try a wider location or different words.</p>}
    {d.jobs.length > 0 && (
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px] items-start">
        <section aria-label="Jobs" className="flex flex-col gap-3 min-w-0">
          <p className="text-sm text-muted">
            {shown.length} of {d.jobs.length} jobs{skill && <> asking for <strong className="text-body">{skill}</strong></>}
            {d.dropped > 0 && <> · {d.dropped} left out because the posting link didn't open</>}
          </p>
          <ul className="flex flex-col gap-4">
            {shown.map((j) => <li key={j.url}><JobCard j={j} prep={prepOf(j)?.id} onPrep={() => setPrepFor(j)} job={job} queryKey={queryKey} /></li>)}
          </ul>
        </section>
        <aside aria-labelledby={`mk-${job}`} className="card p-5 flex flex-col gap-3 xl:sticky xl:top-[85px]">
          <h2 id={`mk-${job}`} className="font-semibold">Market now</h2>
          {d.market_summary && <p className="text-sm text-body">{d.market_summary}</p>}
          {d.top_skills.length > 0 && (
            <div className="flex flex-col gap-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Most-asked skills · filter</p>
              <div className="flex flex-wrap gap-1.5">
                {d.top_skills.map((s) => (
                  <button key={s.skill} type="button" aria-pressed={skill === s.skill} onClick={() => setSkill(skill === s.skill ? null : s.skill)}
                    className={`min-h-[32px] px-2.5 rounded-full border text-[13px] ${skill === s.skill ? "bg-accent text-white border-accent" : "bg-white border-line2 text-body hover:bg-ground"}`}>
                    {s.skill} <span className={skill === s.skill ? "text-white/80" : "text-muted"}>×{s.count}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </aside>
      </div>
    )}
    {prepFor && <PrepDialog j={prepFor} onClose={() => setPrepFor(null)} />}
  </>);
}

export function jdText(j: JobPosting) {
  return [
    `${j.title} at ${j.company} (${j.location})`, "", j.summary, "",
    "Responsibilities:", ...j.responsibilities.map((r) => `- ${r}`), "",
    "Must have:", ...j.must_have.map((r) => `- ${r}`),
    ...(j.nice_to_have.length ? ["", "Nice to have:", ...j.nice_to_have.map((r) => `- ${r}`)] : []),
    "", `Posting: ${j.url}`,
  ].join(String.fromCharCode(10));
}

function JobCard({ j, prep, onPrep, job, queryKey }: { j: JobPosting; prep?: number; onPrep: () => void; job: string; queryKey: string[] }) {
  const [open, setOpen] = useState(false);
  const facts = [j.location, j.work_mode !== "unknown" && j.work_mode, j.seniority, j.salary].filter(Boolean) as string[];
  return (
    <article className="card p-5 flex flex-col gap-2.5">
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span className="font-semibold text-body">{j.company}</span>
        {j.posted && <span className="text-muted">Posted {fmtDay(j.posted)}</span>}
        {j.why_hot && <Chip cls="bg-ok-soft text-ok-dark">{j.why_hot}</Chip>}
        {!j.verified && <Chip cls="bg-[#F1F3F6] text-muted">Link not verified</Chip>}
        {typeof j.match === "number" && (
          <span className={`chip font-semibold ${j.match >= 75 ? "bg-ok-soft text-ok-dark" : j.match >= 50 ? "bg-accent-soft text-accent-dark" : "bg-[#F1F3F6] text-body"}`}>
            {j.match}% match
          </span>
        )}
        <span className="ml-auto"><RemoveFound job={job} url={j.url} title={j.title} queryKey={queryKey} /></span>
      </div>
      <h3 className="font-semibold text-lg leading-snug">
        <a href={j.url} target="_blank" rel="noreferrer" className="hover:text-accent inline-flex items-baseline gap-1.5">
          {j.title} <Icon.external size={14} className="text-muted shrink-0" />
        </a>
      </h3>
      <div className="flex flex-wrap gap-1.5">{facts.map((f) => <Chip key={f}>{f}</Chip>)}</div>
      <p className="text-body text-sm">{j.summary}</p>
      {((j.fits?.length ?? 0) > 0 || (j.gaps?.length ?? 0) > 0) && (
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {(j.fits?.length ?? 0) > 0 && <div className="rounded-lg bg-ok-soft px-3 py-2">
            <p className="text-xs font-semibold text-ok-dark mb-0.5">Why it fits</p>
            <ul className="text-body flex flex-col gap-0.5">{j.fits!.map((x) => <li key={x}>{x}</li>)}</ul>
          </div>}
          {(j.gaps?.length ?? 0) > 0 && <div className="rounded-lg bg-[#FFF6E5] px-3 py-2">
            <p className="text-xs font-semibold text-[#8A5A00] mb-0.5">Gaps</p>
            <ul className="text-body flex flex-col gap-0.5">{j.gaps!.map((x) => <li key={x}>{x}</li>)}</ul>
          </div>}
        </div>
      )}
      {(j.skill_tags ?? []).length > 0 && (
        <div className="flex flex-wrap gap-1.5">{j.skill_tags!.map((s) => <Chip key={s} cls="bg-accent-soft text-accent-dark">{s}</Chip>)}</div>
      )}
      <div className="flex flex-wrap gap-2 pt-1">
        {prep
          ? <Link to={`/career/prep/${prep}`} className="btn-primary btn-sm"><Icon.check size={15} /> Open interview prep</Link>
          : <button type="button" className="btn-primary btn-sm" onClick={onPrep}><Icon.brief size={15} /> Interview prep for this job</button>}
        <button type="button" className="btn-outline btn-sm" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "Hide JD" : "JD breakdown"}
        </button>
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

const LEVELS: { value: Seniority; label: string }[] = [
  { value: "senior", label: "Senior" }, { value: "staff", label: "Staff" },
  { value: "principal", label: "Principal" }, { value: "lead", label: "Lead / Manager" },
];

/** Interview prep from this job's description: suggested topics, questions with sourced answers, and mock practice. */
function PrepDialog({ j, onClose }: { j: JobPosting; onClose: () => void }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const guess: Seniority = /principal/i.test(j.title) ? "principal" : /staff/i.test(j.title) ? "staff" : /lead|manager|head/i.test(j.title) ? "lead" : "senior";
  const [level, setLevel] = useState<Seniority>(guess);
  const [qs, setQs] = useState(6);
  const [focus, setFocus] = useState("");
  const hasCV = !!useProfile().data?.profile;
  const create = useMutation({
    mutationFn: () => {
      const cfg: InterviewConfig = {
        role_title: j.title, company: j.company, jd_text: jdText(j), seniority: level, interview_date: null,
        hours_per_week: 8, background: "", focus_notes: focus, question_types: ["concept", "design", "scenario", "hands_on", "behavioral"],
        questions_per_area: qs, question_bar: "top_ai", web_research: true,
      };
      return api.createInterview(cfg);
    },
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["interviews"] }); navigate(`/career/prep/${r.id}`); },
  });
  return (
    <Dialog title="Interview prep for this job" onClose={onClose}>
      <p className="text-sm text-body -mt-2"><strong>{j.title}</strong> · {j.company}</p>
      <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
        <p className="text-sm text-muted">Reads the JD, links the skills it asks for to topics in your domains, and writes interview questions with sourced answers. About 5–10 minutes.</p>
        {hasCV && <p className="text-sm text-body flex items-center gap-2"><Icon.check size={15} className="text-ok" /> Uses your CV, so skills you haven't shown yet stand out.</p>}
        <div className="grid gap-3 sm:grid-cols-2">
          <Field id="pl-l" label="Level">
            <select id="pl-l" className="input" value={level} onChange={(e) => setLevel(e.target.value as Seniority)}>
              {LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
          </Field>
          <Field id="pl-q" label="Questions">
            <select id="pl-q" className="input" value={qs} onChange={(e) => setQs(Number(e.target.value))}>
              {[3, 6, 10].map((n) => <option key={n} value={n}>{n} per skill area</option>)}
            </select>
          </Field>
        </div>
        <Field id="pl-f" label="Focus (optional)">
          <input id="pl-f" className="input" value={focus} placeholder="e.g. strong on LLMs, new to MLOps" onChange={(e) => setFocus(e.target.value)} />
        </Field>
        {create.isError && <ErrorBox error={create.error} />}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-outline btn-sm" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary btn-sm" disabled={create.isPending}>{create.isPending ? "Starting…" : "Start interview prep"}</button>
        </div>
      </form>
    </Dialog>
  );
}
