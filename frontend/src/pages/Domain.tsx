import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, Navigate, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, type DomainDetail, type SourceKind, type TopicDetail } from "../api";
import { useMe } from "../components/Auth";
import { Dialog } from "../components/EditItem";
import { Crumbs, Detail, SideGroup, SideHeading, SideLink, TwoPane } from "../components/Layout";
import { AddSource, Field, KIND, LEVEL, SourceCard, usePoll } from "../components/Sources";
import { ErrorBox, Icon, Markdown, Thinking, ago } from "../components/ui";

/** /d/:slug and /d/:slug/t/:topicId : a domain's sections and topics on the left, the chosen topic on the right. */
export default function DomainPage() {
  const { slug = "", topicId } = useParams();
  const tid = topicId ? Number(topicId) : null;
  const domain = usePoll(["domain", slug], () => api.domain(slug), (d) => d?.status === "building");
  if (domain.isLoading) return <main className="p-8"><Thinking label="Loading…" /></main>;
  if (domain.isError) return <main className="p-8"><ErrorBox error={domain.error} onRetry={() => domain.refetch()} /></main>;
  const d = domain.data!;
  return (
    <TwoPane sideLabel={`${d.name} topics`} side={<DomainSide d={d} tid={tid} />}>
      {tid ? <TopicView id={tid} d={d} /> : <DomainOverview d={d} />}
    </TwoPane>
  );
}

/** /domains: first domain (or the empty state). */
export function DomainsIndex() {
  const q = useQuery({ queryKey: ["domains"], queryFn: api.domains });
  const me = useMe();
  if (q.isLoading) return <main className="p-8"><Thinking label="Loading…" /></main>;
  if (q.data?.length) return <Navigate to={`/d/${q.data[0].slug}`} replace />;
  return (
    <main className="max-w-[640px] mx-auto p-10 flex flex-col gap-3 items-start">
      <h1 className="h-display text-2xl">No domains yet</h1>
      {me.is_admin ? <NewDomainButton /> : <p className="text-body">The admin hasn't added any domains yet.</p>}
    </main>
  );
}

// ---------------------------------------------------------------- left panel

function DomainSide({ d, tid }: { d: DomainDetail; tid: number | null }) {
  const me = useMe();
  const navigate = useNavigate();
  const domains = useQuery({ queryKey: ["domains"], queryFn: api.domains });
  const [filter, setFilter] = useState("");
  const f = filter.trim().toLowerCase();
  const sections = d.section_list.map((s) => ({
    ...s, topics: f ? s.topics.filter((t) => t.title.toLowerCase().includes(f) || s.title.toLowerCase().includes(f)) : s.topics,
  })).filter((s) => !f || s.topics.length);

  return (
    <div className="pb-8">
      <div className="px-5 pt-5 flex flex-col gap-3">
        <label htmlFor="dom-switch" className="sr-only">Domain</label>
        <select id="dom-switch" className="input font-semibold py-2" value={d.slug} onChange={(e) => navigate(`/d/${e.target.value}`)}>
          {(domains.data ?? [d]).map((x) => <option key={x.slug} value={x.slug}>{x.name}</option>)}
        </select>
        <div className="flex items-center gap-2 px-3 h-10 rounded-[10px] border border-line2 bg-ground focus-within:border-accent">
          <Icon.search size={16} className="text-muted" />
          <label htmlFor="topic-filter" className="sr-only">Filter topics</label>
          <input id="topic-filter" type="search" value={filter} onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter topics" className="flex-1 min-w-0 bg-transparent outline-none text-sm" />
        </div>
      </div>
      <SideHeading>{d.sections} sections · {d.topics} topics</SideHeading>
      <SideLink to={`/d/${d.slug}`} end icon={<Icon.grid size={16} />}>Overview</SideLink>
      <div className="mt-1 flex flex-col gap-0.5">
        {sections.map((s) => (
          <SideGroup key={s.id} title={s.title} count={s.topics.length} active={!!f || s.topics.some((t) => t.id === tid)}
            actions={me.is_admin ? <SectionMenu id={s.id} title={s.title} slug={d.slug} /> : undefined}>
            {s.topics.map((t) => (
              <SideLink key={t.id} to={`/d/${d.slug}/t/${t.id}`}
                meta={t.status === "writing" ? <span className="dot inline-block" aria-label="writing" /> : undefined}>
                {t.title}
              </SideLink>
            ))}
            {me.is_admin && !f && <AddTopicLink sectionId={s.id} slug={d.slug} />}
          </SideGroup>
        ))}
      </div>
      {me.is_admin && !f && <div className="px-5 pt-3"><AddSectionButton domainId={d.id} slug={d.slug} /></div>}
    </div>
  );
}

function SectionMenu({ id, title, slug }: { id: number; title: string; slug: string }) {
  const qc = useQueryClient();
  const done = () => qc.invalidateQueries({ queryKey: ["domain", slug] });
  const rename = useMutation({ mutationFn: (t: string) => api.renameSection(id, t), onSuccess: done });
  const remove = useMutation({ mutationFn: () => api.deleteSection(id), onSuccess: done });
  return (
    <span className="flex">
      <button type="button" className="icon-btn" title="Rename section" aria-label={`Rename ${title}`}
        onClick={() => { const t = prompt("Section name", title); if (t?.trim()) rename.mutate(t.trim()); }}><Icon.edit size={14} /></button>
      <button type="button" className="icon-btn" title="Delete section" aria-label={`Delete ${title}`}
        onClick={() => { if (confirm(`Delete the section "${title}" and all its topics?`)) remove.mutate(); }}><Icon.trash size={14} /></button>
    </span>
  );
}

function AddTopicLink({ sectionId, slug }: { sectionId: number; slug: string }) {
  const [open, setOpen] = useState(false);
  return (<>
    <button type="button" className="mx-2 px-3 py-1.5 text-sm text-accent font-semibold inline-flex items-center gap-1.5" onClick={() => setOpen(true)}>
      <Icon.plus size={14} /> Add topic
    </button>
    {open && <AddTopicDialog sectionId={sectionId} slug={slug} onClose={() => setOpen(false)} />}
  </>);
}

function AddTopicDialog({ sectionId, slug, onClose }: { sectionId: number; slug: string; onClose: () => void }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [f, setF] = useState({ title: "", blurb: "", auto: true });
  const add = useMutation({
    mutationFn: () => api.addTopic(sectionId, f),
    onSuccess: (t) => { qc.invalidateQueries({ queryKey: ["domain", slug] }); onClose(); navigate(`/d/${slug}/t/${t.id}`); },
  });
  return (
    <Dialog title="Add topic" onClose={onClose}>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <Field id="at-title" label="Topic"><input id="at-title" className="input" required minLength={2} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="e.g. Speculative decoding" /></Field>
        <Field id="at-blurb" label="Scope (optional)"><input id="at-blurb" className="input" value={f.blurb} onChange={(e) => setF({ ...f, blurb: e.target.value })} placeholder="What it should cover" /></Field>
        <label className="flex items-start gap-2.5 text-sm">
          <input type="checkbox" className="mt-1 w-4 h-4" checked={f.auto} onChange={(e) => setF({ ...f, auto: e.target.checked })} />
          <span><span className="font-semibold">Write the summary and find links with AI</span><br />
            <span className="text-muted">Takes 1–3 minutes. Untick to write it yourself.</span></span>
        </label>
        {add.isError && <ErrorBox error={add.error} />}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-outline btn-sm" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary btn-sm" disabled={add.isPending}>Add topic</button>
        </div>
      </form>
    </Dialog>
  );
}

function AddSectionButton({ domainId, slug }: { domainId: number; slug: string }) {
  const qc = useQueryClient();
  const add = useMutation({
    mutationFn: (t: string) => api.addSection(domainId, t),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["domain", slug] }),
  });
  return (
    <button type="button" className="btn-outline btn-sm w-full" disabled={add.isPending}
      onClick={() => { const t = prompt("New section name"); if (t?.trim()) add.mutate(t.trim()); }}>
      <Icon.plus size={16} /> Add section
    </button>
  );
}

// ---------------------------------------------------------------- domain overview (no topic chosen)

function DomainOverview({ d }: { d: DomainDetail }) {
  const me = useMe();
  return (
    <Detail wide>
      <Crumbs items={[{ label: "Domains", to: "/domains" }, { label: d.name }]} />
      <header className="flex flex-wrap items-start gap-4">
        <div className="flex-1 min-w-[260px]">
          <h1 className="h-display text-3xl">{d.name}</h1>
          {d.description && <p className="text-body text-[16px] mt-1.5 max-w-[720px]">{d.description}</p>}
        </div>
        {me.is_admin && <DomainAdmin d={d} />}
      </header>

      {d.status === "building" && (
        <div className="card p-5"><Thinking label="Designing the outline, then writing each topic with its links. This takes several minutes; topics appear as they are ready." /></div>
      )}
      {d.status === "failed" && <ErrorBox error={new Error(d.error ?? "Building the domain failed.")} />}

      {d.section_list.length === 0 && d.status !== "building" ? (
        <div className="card p-8 flex flex-col items-start gap-3">
          <h2 className="font-semibold text-lg">This domain is empty</h2>
          <p className="text-body">{me.is_admin ? "Let AI design the sections and topics, or add sections yourself from the left panel." : "The admin hasn't added topics yet."}</p>
          {me.is_admin && <BuildButton d={d} />}
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {d.section_list.map((s) => (
            <section key={s.id} className="card p-5 flex flex-col gap-3" aria-labelledby={`sec-${s.id}`}>
              <div className="flex items-baseline justify-between gap-3">
                <h2 id={`sec-${s.id}`} className="font-semibold text-[16px]">{s.title}</h2>
                <span className="text-xs text-muted shrink-0">{s.topics.length} topics</span>
              </div>
              <ul className="flex flex-col">
                {s.topics.slice(0, 6).map((t) => (
                  <li key={t.id}>
                    <Link to={`/d/${d.slug}/t/${t.id}`} className="group flex items-start gap-2 py-1.5 text-[14px]">
                      <Icon.chevron size={14} className="mt-[3px] shrink-0 text-muted group-hover:text-accent" />
                      <span className="flex-1 text-body group-hover:text-accent">{t.title}</span>
                      {t.sources > 0 && <span className="text-xs text-muted shrink-0">{t.sources} links</span>}
                    </Link>
                  </li>
                ))}
                {s.topics.length > 6 && (
                  <li className="text-sm text-muted pl-[22px] pt-1">+ {s.topics.length - 6} more in the left panel</li>
                )}
              </ul>
            </section>
          ))}
        </div>
      )}
    </Detail>
  );
}

function BuildButton({ d }: { d: DomainDetail }) {
  const qc = useQueryClient();
  const build = useMutation({ mutationFn: () => api.buildDomain(d.id), onSuccess: () => qc.invalidateQueries({ queryKey: ["domain", d.slug] }) });
  return (<>
    <button type="button" className="btn-primary" disabled={build.isPending} onClick={() => build.mutate()}>
      <Icon.sparkle size={16} /> Build outline with AI
    </button>
    {build.isError && <ErrorBox error={build.error} />}
  </>);
}

function DomainAdmin({ d }: { d: DomainDetail }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const drafts = d.section_list.reduce((n, s) => n + s.topics.filter((t) => t.status === "draft" || t.status === "failed").length, 0);
  const fill = useMutation({ mutationFn: () => api.fillDomain(d.id), onSuccess: () => qc.invalidateQueries({ queryKey: ["domain", d.slug] }) });
  const blogsAll = useMutation({ mutationFn: () => api.domainBlogs(d.id) });
  const remove = useMutation({
    mutationFn: () => api.deleteDomain(d.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["domains"] }); navigate("/domains"); },
  });
  return (
    <div className="flex flex-wrap gap-2">
      {drafts > 0 && (
        <button type="button" className="btn-outline btn-sm" disabled={fill.isPending} title="Otherwise each summary is written the first time someone opens the topic"
          onClick={() => { if (confirm(`Write executive summaries for ${drafts} topics now? This runs three at a time and can take a while.`)) fill.mutate(); }}>
          <Icon.sparkle size={15} /> Write {drafts} summaries
        </button>
      )}
      <button type="button" className="btn-outline btn-sm" disabled={blogsAll.isPending} title="Blog Scout finds explainer posts for every topic that hasn't had a search yet"
        onClick={() => { if (confirm(`Find blog posts for every topic in ${d.name}? This runs three at a time and can take a while.`)) blogsAll.mutate(); }}>
        <Icon.sparkle size={15} /> {blogsAll.data ? `Finding blogs for ${blogsAll.data.started} topics` : "Find blogs for all topics"}
      </button>
      <button type="button" className="btn-outline btn-sm" onClick={() => setEditing(true)}><Icon.edit size={15} /> Edit</button>
      <button type="button" className="btn-outline btn-sm" disabled={remove.isPending}
        onClick={() => { if (confirm(`Delete the domain "${d.name}" with all its topics and links, for every account?`)) remove.mutate(); }}>
        <Icon.trash size={15} /> Delete
      </button>
      {editing && <EditDomain d={d} onClose={() => setEditing(false)} />}
    </div>
  );
}

function EditDomain({ d, onClose }: { d: DomainDetail; onClose: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState({ name: d.name, description: d.description });
  const [blogs, setBlogs] = useState((d.trusted_blogs ?? []).map((b) => `${b.name} | ${b.url}`).join(String.fromCharCode(10)));
  const parsed = blogs.split(String.fromCharCode(10)).map((l) => l.trim()).filter(Boolean).map((l) => {
    const [a, b] = l.includes("|") ? l.split("|").map((x) => x.trim()) : ["", l];
    const url = /^https?:[/][/]/.test(b) ? b : `https://${b}`;
    return { name: a || url.replace(/^https?:[/][/](www[.])?/, "").split("/")[0], url };
  });
  const save = useMutation({
    mutationFn: () => api.updateDomain(d.id, { ...f, trusted_blogs: parsed }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["domains"] }); qc.invalidateQueries({ queryKey: ["domain", d.slug] }); onClose(); },
  });
  return (
    <Dialog title="Edit domain" onClose={onClose}>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        <Field id="ed-name" label="Name"><input id="ed-name" className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field id="ed-desc" label="Description"><textarea id="ed-desc" className="input" rows={3} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
        <Field id="ed-blogs" label="Trusted blogs (optional)" hint="One per line: Name | link. Blog Scout checks these first.">
          <textarea id="ed-blogs" className="input font-mono text-[13px]" rows={4} value={blogs} onChange={(e) => setBlogs(e.target.value)}
            placeholder={"AI4Bharat | https://ai4bharat.iitm.ac.in/blog" + String.fromCharCode(10) + "Lil'Log | https://lilianweng.github.io"} />
        </Field>
        {save.isError && <ErrorBox error={save.error} />}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-outline btn-sm" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary btn-sm" disabled={save.isPending}>Save</button>
        </div>
      </form>
    </Dialog>
  );
}

/** Admin: add a domain (from the Domains menu or the empty state). */
export function NewDomainButton({ className = "btn-primary" }: { className?: string }) {
  const [open, setOpen] = useState(false);
  return (<>
    <button type="button" className={className} onClick={() => setOpen(true)}><Icon.plus size={16} /> Add domain</button>
    {open && <NewDomainDialog onClose={() => setOpen(false)} />}
  </>);
}

export function NewDomainDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [f, setF] = useState({ name: "", description: "", build: true, max_topics: 18 });
  const add = useMutation({
    mutationFn: () => api.createDomain(f),
    onSuccess: (d) => { qc.invalidateQueries({ queryKey: ["domains"] }); onClose(); navigate(`/d/${d.slug}`); },
  });
  return (
    <Dialog title="Add domain" onClose={onClose}>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <Field id="nd-name" label="Name"><input id="nd-name" className="input" required minLength={2} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="e.g. Computer Vision" /></Field>
        <Field id="nd-desc" label="Scope (optional)"><textarea id="nd-desc" className="input" rows={2} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} placeholder="What this domain should cover" /></Field>
        <label className="flex items-start gap-2.5 text-sm">
          <input type="checkbox" className="mt-1 w-4 h-4" checked={f.build} onChange={(e) => setF({ ...f, build: e.target.checked })} />
          <span><span className="font-semibold">Build the outline with AI</span><br />
            <span className="text-muted">Sections and topics, each with an executive summary and links. Several minutes.</span></span>
        </label>
        {f.build && (
          <Field id="nd-max" label="Number of topics">
            <select id="nd-max" className="input" value={f.max_topics} onChange={(e) => setF({ ...f, max_topics: Number(e.target.value) })}>
              {[8, 12, 18, 24, 30].map((n) => <option key={n} value={n}>About {n}</option>)}
            </select>
          </Field>
        )}
        {add.isError && <ErrorBox error={add.error} />}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-outline btn-sm" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary btn-sm" disabled={add.isPending}>Add domain</button>
        </div>
      </form>
    </Dialog>
  );
}

// ---------------------------------------------------------------- topic (right panel)

const busy = (t?: TopicDetail) => !!t && (t.status === "writing" || t.status === "draft" || t.blog_status === "finding"
  || t.source_list.some((s) => s.summary_status === "writing"));
type Level = keyof typeof LEVEL;

function TopicView({ id, d }: { id: number; d: DomainDetail }) {
  const me = useMe();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const key = ["topic", id];
  const q = usePoll(key, () => api.topic(id), busy);
  const [kind, setKind] = useState<SourceKind | "all">("all");
  const [freeOnly, setFreeOnly] = useState(false);
  const [level, setLevel] = useState<Level | "all">("all");
  const [editing, setEditing] = useState(false);
  const { hash } = useLocation();
  const flat = useMemo(() => d.section_list.flatMap((s) => s.topics), [d]);
  const refresh = () => { qc.invalidateQueries({ queryKey: key }); qc.invalidateQueries({ queryKey: ["domain", d.slug] }); };
  const mark = useMutation({ mutationFn: (on: boolean) => api.bookmarkTopic(id, on), onSuccess: () => { refresh(); qc.invalidateQueries({ queryKey: ["bookmarks"] }); } });
  const rewrite = useMutation({ mutationFn: (find: boolean) => api.rewriteTopic(id, find), onSuccess: refresh });
  const scout = useMutation({ mutationFn: () => api.topicBlogs(id), onSuccess: (d) => qc.setQueryData(key, d) });
  const remove = useMutation({ mutationFn: () => api.deleteTopic(id), onSuccess: () => { qc.invalidateQueries({ queryKey: ["domain", d.slug] }); navigate(`/d/${d.slug}`); } });
  void hash;

  if (q.isLoading) return <Detail><Thinking label="Loading…" /></Detail>;
  if (q.isError) return <Detail><ErrorBox error={q.error} onRetry={() => q.refetch()} /></Detail>;
  const t = q.data!;
  const writing = t.status === "writing" || t.status === "draft";
  const blogs = t.source_list.filter((s) => s.kind === "article");
  const links = t.source_list.filter((s) => s.kind !== "article");
  const levels = (["beginner", "intermediate", "advanced"] as const).filter((l) => blogs.some((b) => b.post_level === l));
  const blogsShown = blogs.filter((s) => (level === "all" || s.post_level === level) && (!freeOnly || s.access === "free"));
  const kinds = Array.from(new Set(links.map((s) => s.kind)));
  const shown = links.filter((s) => (kind === "all" || s.kind === kind) && (!freeOnly || s.access === "free"));
  const scouting = t.blog_status === "finding" || scout.isPending;
  const i = flat.findIndex((x) => x.id === id);
  const prev = i > 0 ? flat[i - 1] : null;
  const next = i >= 0 && i < flat.length - 1 ? flat[i + 1] : null;

  return (
    <Detail>
      <Crumbs items={[{ label: t.domain.name, to: `/d/${d.slug}` }, { label: t.section.title }]} />
      <header className="flex flex-wrap items-start gap-3">
        <h1 className="h-display text-[28px] leading-tight flex-1 min-w-[240px]">{t.title}</h1>
        <div className="flex flex-wrap gap-1.5">
          <button type="button" className={`btn-sm btn ${t.bookmarked ? "bg-pp-bg text-pp-fg" : "btn-outline"}`} aria-pressed={t.bookmarked}
            disabled={mark.isPending} onClick={() => mark.mutate(!t.bookmarked)}>
            <Icon.star size={15} /> {t.bookmarked ? "Bookmarked" : "Bookmark"}
          </button>
          {me.is_admin && (<>
            <button type="button" className="btn-outline btn-sm" onClick={() => setEditing(true)}><Icon.edit size={15} /> Edit</button>
            <button type="button" className="btn-outline btn-sm" disabled={writing || rewrite.isPending} title="Rewrite the executive summary with AI"
              onClick={() => rewrite.mutate(false)}><Icon.sparkle size={15} /> Rewrite</button>
            <button type="button" className="icon-btn w-9 h-9" title="Delete topic" aria-label="Delete topic" disabled={remove.isPending}
              onClick={() => { if (confirm(`Delete "${t.title}" and its links for every account?`)) remove.mutate(); }}><Icon.trash size={16} /></button>
          </>)}
        </div>
      </header>

      <section aria-labelledby="exec-h" className="card p-6 flex flex-col gap-4 border-l-4 border-l-accent">
        <h2 id="exec-h" className="text-[11px] font-bold uppercase tracking-[0.08em] text-accent">Executive summary</h2>
        {writing && !t.overview ? (
          <div className="flex flex-col gap-3">
            <Thinking label={t.sources < 3 ? "Writing the summary and finding the best links… (1–3 minutes)" : "Writing the executive summary… (about a minute)"} />
            {(t.key_points.length > 0 || t.blurb) && (
              <div className="text-body text-[15px]">
                <p className="text-xs text-muted mb-1">From the outline:</p>
                {t.blurb && <p>{t.blurb}</p>}
                <ul className="list-disc pl-5 mt-1">{t.key_points.map((k, n) => <li key={n}>{k}</li>)}</ul>
              </div>
            )}
          </div>
        ) : t.status === "failed" && !t.overview ? (
          <div className="flex flex-col gap-2 items-start">
            <ErrorBox error={new Error(t.error ?? "Writing the summary failed.")} />
            <button type="button" className="btn-outline btn-sm" onClick={() => rewrite.mutate(false)}>Try again</button>
          </div>
        ) : (<>
          {t.overview && <p className="text-[17px] leading-relaxed text-ink">{t.overview}</p>}
          {t.key_points.length > 0 && (
            <ul className="flex flex-col gap-2">
              {t.key_points.map((k, n) => (
                <li key={n} className="flex gap-2.5 text-[15px] text-body">
                  <span className="mt-[3px] w-5 h-5 shrink-0 rounded-full bg-accent-soft text-accent flex items-center justify-center"><Icon.check size={12} /></span>
                  <span>{k}</span>
                </li>
              ))}
            </ul>
          )}
          {t.why && (
            <p className="text-[14px] rounded-xl bg-ground px-4 py-3 text-body"><span className="font-semibold text-ink">Why it matters: </span>{t.why}</p>
          )}
          {writing && <Thinking label="Updating…" />}
        </>)}
      </section>

      {t.details_md && (
        <details className="card group">
          <summary className="cursor-pointer list-none flex items-center gap-2 px-5 py-3.5 font-semibold">
            <Icon.chevron size={15} className="text-muted transition-transform group-open:rotate-90" /> More detail
          </summary>
          <div className="px-5 pb-5"><Markdown className="text-[15px]">{t.details_md}</Markdown></div>
        </details>
      )}

      <section aria-labelledby="blog-h" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <h2 id="blog-h" className="h-display text-xl flex-1">Blogs &amp; explainers <span className="text-muted font-sans text-base font-normal">· {blogs.length} posts</span></h2>
          {me.is_admin && (
            <button type="button" className="btn-outline btn-sm" disabled={scouting} title="Blog Scout searches Medium, Hugging Face, Kaggle and well-known AI blogs"
              onClick={() => scout.mutate()}><Icon.sparkle size={15} /> {blogs.length ? "Find more blogs" : "Find blogs"}</button>
          )}
        </div>
        <p className="text-sm text-muted -mt-2">Plain-language posts that explain this topic, easiest first.</p>
        {(levels.length > 1 || blogs.length > 2) && (
          <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter posts by level">
            {(["all", ...levels] as const).map((l) => (
              <button key={l} type="button" aria-pressed={level === l} onClick={() => setLevel(l)}
                className={`px-3 py-1.5 rounded-full text-sm border ${level === l ? "bg-ink text-white border-ink" : "bg-white border-line2 text-body hover:bg-ground"}`}>
                {l === "all" ? "All" : LEVEL[l].label}
                <span className="opacity-60 ml-1">{l === "all" ? blogs.length : blogs.filter((b) => b.post_level === l).length}</span>
              </button>
            ))}
            <label className="ml-auto inline-flex items-center gap-2 text-sm text-body">
              <input type="checkbox" className="w-4 h-4" checked={freeOnly} onChange={(e) => setFreeOnly(e.target.checked)} /> Free only
            </label>
          </div>
        )}
        {scouting && <Thinking label="Blog Scout is finding the clearest explainer posts… (1–2 minutes)" />}
        {t.blog_status === "failed" && !scouting && (
          <div className="flex flex-col gap-2 items-start">
            <ErrorBox error={new Error(t.blog_error ?? "Finding blog posts failed.")} />
            <button type="button" className="btn-outline btn-sm" onClick={() => scout.mutate()}>Try again</button>
          </div>
        )}
        {scout.isError && <ErrorBox error={scout.error} />}
        {blogs.length === 0 && !scouting && t.blog_status !== "failed" && <p className="text-muted">No blog posts yet.</p>}
        <div className="flex flex-col gap-2.5">
          {blogsShown.map((s) => <SourceCard key={s.id} s={s} queryKey={key} />)}
        </div>
      </section>

      <section aria-labelledby="src-h" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <h2 id="src-h" className="h-display text-xl flex-1">Courses, videos &amp; docs <span className="text-muted font-sans text-base font-normal">· {links.length} links</span></h2>
          {me.is_admin && t.source_list.length > 0 && (
            <button type="button" className="btn-outline btn-sm" disabled={writing || rewrite.isPending} onClick={() => rewrite.mutate(true)}>
              <Icon.search size={15} /> Find more links
            </button>
          )}
        </div>
        {kinds.length > 1 && (
          <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter links">
            {(["all", ...kinds] as const).map((k) => (
              <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)}
                className={`px-3 py-1.5 rounded-full text-sm border ${kind === k ? "bg-ink text-white border-ink" : "bg-white border-line2 text-body hover:bg-ground"}`}>
                {k === "all" ? "All" : KIND[k].label}
                <span className="opacity-60 ml-1">{k === "all" ? links.length : links.filter((s) => s.kind === k).length}</span>
              </button>
            ))}
            <label className="ml-auto inline-flex items-center gap-2 text-sm text-body">
              <input type="checkbox" className="w-4 h-4" checked={freeOnly} onChange={(e) => setFreeOnly(e.target.checked)} /> Free only
            </label>
          </div>
        )}
        {links.length === 0 && !writing && (
          <p className="text-muted">No links yet.{me.is_admin ? " Add one, or let AI find the best ones." : ""}</p>
        )}
        {me.is_admin && t.source_list.length === 0 && !writing && (
          <button type="button" className="btn-primary btn-sm self-start" onClick={() => rewrite.mutate(true)}><Icon.sparkle size={15} /> Find links with AI</button>
        )}
        <div className="flex flex-col gap-2.5">
          {shown.map((s) => <SourceCard key={s.id} s={s} queryKey={key} />)}
        </div>
        {me.is_admin && <AddSource topicId={t.id} queryKey={key} />}
      </section>

      {(prev || next) && (
        <nav aria-label="Next and previous topic" className="grid sm:grid-cols-2 gap-3 pt-2">
          {prev ? <Link to={`/d/${d.slug}/t/${prev.id}`} className="card px-4 py-3 hover:border-accent"><span className="text-xs text-muted">Previous</span><span className="block font-semibold truncate">{prev.title}</span></Link> : <span />}
          {next && <Link to={`/d/${d.slug}/t/${next.id}`} className="card px-4 py-3 text-right hover:border-accent"><span className="text-xs text-muted">Next</span><span className="block font-semibold truncate">{next.title}</span></Link>}
        </nav>
      )}
      {t.updated_at && t.status === "ready" && <p className="text-xs text-muted">Updated {ago(t.updated_at)}</p>}
      {editing && <EditTopic t={t} onClose={() => setEditing(false)} onSaved={refresh} />}
    </Detail>
  );
}

function EditTopic({ t, onClose, onSaved }: { t: TopicDetail; onClose: () => void; onSaved: () => void }) {
  const NL = String.fromCharCode(10);
  const [f, setF] = useState({ title: t.title, overview: t.overview, key_points: t.key_points.join(NL), why: t.why, details_md: t.details_md });
  const save = useMutation({
    mutationFn: () => api.updateTopic(t.id, { ...f, key_points: f.key_points.split(NL) }),
    onSuccess: () => { onSaved(); onClose(); },
  });
  return (
    <Dialog title="Edit topic" onClose={onClose}>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        <Field id="et-title" label="Title"><input id="et-title" className="input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field>
        <Field id="et-ov" label="Executive summary"><textarea id="et-ov" className="input" rows={3} value={f.overview} onChange={(e) => setF({ ...f, overview: e.target.value })} /></Field>
        <Field id="et-kp" label="Key points" hint="One per line"><textarea id="et-kp" className="input" rows={5} value={f.key_points} onChange={(e) => setF({ ...f, key_points: e.target.value })} /></Field>
        <Field id="et-why" label="Why it matters"><textarea id="et-why" className="input" rows={2} value={f.why} onChange={(e) => setF({ ...f, why: e.target.value })} /></Field>
        <Field id="et-md" label="More detail (Markdown, optional)"><textarea id="et-md" className="input font-mono text-sm" rows={5} value={f.details_md} onChange={(e) => setF({ ...f, details_md: e.target.value })} /></Field>
        {save.isError && <ErrorBox error={save.error} />}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-outline btn-sm" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary btn-sm" disabled={save.isPending}>Save</button>
        </div>
      </form>
    </Dialog>
  );
}
