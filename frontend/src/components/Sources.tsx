import { useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { api, type Access, type SourceKind, type TopicSource } from "../api";
import { useMe } from "./Auth";
import { Dialog } from "./EditItem";
import { ErrorBox, Icon } from "./ui";

export const KIND: Record<SourceKind, { label: string; icon: ReactNode; cls: string }> = {
  video: { label: "Video", icon: <Icon.play size={16} />, cls: "bg-yt-bg text-yt-fg" },
  course: { label: "Course", icon: <Icon.cap size={16} />, cls: "bg-cs-bg text-cs-fg" },
  paper: { label: "Paper", icon: <Icon.paper size={16} />, cls: "bg-pp-bg text-pp-fg" },
  article: { label: "Article", icon: <Icon.doc size={16} />, cls: "bg-[#EEF0F3] text-body" },
  docs: { label: "Docs", icon: <Icon.book size={16} />, cls: "bg-ok-soft text-ok-dark" },
  repo: { label: "Code", icon: <Icon.code size={16} />, cls: "bg-[#E9EBEF] text-ink" },
  model: { label: "Model", icon: <Icon.cube size={16} />, cls: "bg-ud-bg text-ud-fg" },
  dataset: { label: "Dataset", icon: <Icon.db size={16} />, cls: "bg-[#E3F4F4] text-[#145E5E]" },
  book: { label: "Book", icon: <Icon.book size={16} />, cls: "bg-pp-bg text-pp-fg" },
};

export const ACCESS: Record<Access, { label: string; cls: string; hint: string }> = {
  free: { label: "Free", cls: "bg-ok-soft text-ok-dark", hint: "Open without an account" },
  login: { label: "Login needed", cls: "bg-cs-bg text-cs-fg", hint: "Free, but you sign in (e.g. audit a course)" },
  paid: { label: "Paid", cls: "bg-pp-bg text-pp-fg", hint: "Needs a purchase or subscription" },
  limited: { label: "May be paywalled", cls: "bg-pp-bg text-pp-fg", hint: "Some articles need a membership" },
};

export function AccessBadge({ access }: { access: Access }) {
  const a = ACCESS[access] ?? ACCESS.free;
  return <span className={`chip ${a.cls}`} title={a.hint}>{a.label}</span>;
}

/** One link to go deeper: what it is, where it lives, whether you need to log in, and an optional AI summary. */
export const LEVEL = {
  beginner: { label: "Beginner", cls: "bg-ok-soft text-ok-dark" },
  intermediate: { label: "Intermediate", cls: "bg-accent-soft text-accent-dark" },
  advanced: { label: "Advanced", cls: "bg-pp-bg text-pp-fg" },
} as const;

export function SourceCard({ s, queryKey, context }: { s: TopicSource; queryKey: QueryKey; context?: string }) {
  const me = useMe();
  const qc = useQueryClient();
  const k = KIND[s.kind] ?? KIND.article;
  const [show, setShow] = useState(false);
  const [editing, setEditing] = useState(false);
  const summarize = useMutation({
    mutationFn: () => api.summarizeSource(s.id),
    onSuccess: () => { setShow(true); qc.invalidateQueries({ queryKey }); },
  });
  const remove = useMutation({ mutationFn: () => api.deleteSource(s.id), onSuccess: () => qc.invalidateQueries({ queryKey }) });
  const writing = s.summary_status === "writing";
  const meta = [s.site, s.author && s.author !== s.site ? s.author : "", s.published || (s.year ? String(s.year) : ""),
    s.read_minutes ? `${s.read_minutes} min read` : s.duration].filter(Boolean);
  void context;

  return (
    <article className="card p-4 flex gap-3.5 hover:border-line2 transition-colors">
      <span aria-hidden="true" className={`w-10 h-10 shrink-0 rounded-xl flex items-center justify-center ${k.cls}`}>{k.icon}</span>
      <div className="flex-1 min-w-0 flex flex-col gap-1.5">
        <div className="flex items-start gap-2">
          <h4 className="flex-1 min-w-0 font-semibold leading-snug">
            <a href={s.url} target="_blank" rel="noreferrer" className="hover:text-accent">
              {s.title} <Icon.external size={13} className="inline text-muted align-[-1px]" />
              <span className="sr-only">(opens in a new tab)</span>
            </a>
          </h4>
          {me.is_admin && (
            <span className="flex shrink-0 -mt-1 -mr-1">
              <button type="button" className="icon-btn" title="Edit link" aria-label={`Edit ${s.title}`} onClick={() => setEditing(true)}><Icon.edit size={15} /></button>
              <button type="button" className="icon-btn" title="Delete link" aria-label={`Delete ${s.title}`} disabled={remove.isPending}
                onClick={() => { if (confirm(`Delete "${s.title}"?`)) remove.mutate(); }}><Icon.trash size={15} /></button>
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-muted">
          <span className={`chip ${k.cls}`}>{s.blog ? "Blog" : k.label}</span>
          {s.post_level && <span className={`chip ${LEVEL[s.post_level].cls}`}>{LEVEL[s.post_level].label}</span>}
          <AccessBadge access={s.access} />
          {meta.length > 0 && <span className="truncate max-w-full">{meta.join(" · ")}</span>}
        </div>
        {s.summary && <p className="text-[14px] text-body line-clamp-3">{s.summary}</p>}
        {Object.keys(s.facts).length > 0 && (
          <p className="text-[13px] text-muted">
            {Object.entries(s.facts).map(([key, v]) => <span key={key} className="mr-3"><span className="font-semibold text-body capitalize">{key}:</span> {v}</span>)}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-2 pt-0.5">
          {s.ai_summary ? (
            <button type="button" className="text-sm font-semibold text-accent inline-flex items-center gap-1.5 min-h-[32px]"
              aria-expanded={show} onClick={() => setShow(!show)}>
              <Icon.sparkle size={14} /> {show ? "Hide summary" : "AI summary"}
            </button>
          ) : (
            <button type="button" className="text-sm font-semibold text-accent inline-flex items-center gap-1.5 min-h-[32px] disabled:text-muted"
              disabled={writing || summarize.isPending} onClick={() => summarize.mutate()}>
              <Icon.sparkle size={14} /> {writing ? "Summarizing… (about a minute)" : s.summary_status === "failed" ? "Summary failed · Try again" : "Summarize this source"}
            </button>
          )}
          {me.is_admin && s.ai_summary && show && (
            <button type="button" className="text-sm text-muted hover:text-ink min-h-[32px]" disabled={writing}
              onClick={() => summarize.mutate()}>{writing ? "Rewriting…" : "Rewrite"}</button>
          )}
        </div>
        {summarize.isError && <ErrorBox error={summarize.error} />}
        {show && s.ai_summary && <AISummary s={s} />}
      </div>
      {editing && <EditSource s={s} queryKey={queryKey} onClose={() => setEditing(false)} />}
    </article>
  );
}

function AISummary({ s }: { s: TopicSource }) {
  const a = s.ai_summary!;
  const list = (title: string, items?: string[]) => items && items.length > 0 && (
    <div><p className="font-semibold text-ink">{title}</p>
      <ul className="list-disc pl-5 flex flex-col gap-0.5">{items.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
  );
  const read = a.type === "paper" ? a.read_full_text : a.read_source;
  return (
    <div className="mt-1 rounded-xl bg-[#F6F8FF] border border-accent-line p-4 text-[14px] text-body flex flex-col gap-2.5">
      <p className="text-ink">{a.tldr}</p>
      {a.type === "paper" ? (<>
        {a.problem && <p><span className="font-semibold text-ink">Problem: </span>{a.problem}</p>}
        {a.method && <p><span className="font-semibold text-ink">Method: </span>{a.method}</p>}
        {list("Results", a.results)}
        {list("Limitations", a.limitations)}
        {a.why_it_matters && <p><span className="font-semibold text-ink">Why it matters: </span>{a.why_it_matters}</p>}
      </>) : (<>
        {list("Key takeaways", a.key_points)}
        {a.best_for && <p><span className="font-semibold text-ink">Best for: </span>{a.best_for}</p>}
        {(a.time_needed || a.access_note) && <p className="text-muted">{[a.time_needed, a.access_note].filter(Boolean).join(" · ")}</p>}
      </>)}
      {read === false && <p className="text-xs text-muted">Written from the page description; the full source couldn't be opened.</p>}
    </div>
  );
}

function EditSource({ s, queryKey, onClose }: { s: TopicSource; queryKey: QueryKey; onClose: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState({ title: s.title, url: s.url, summary: s.summary, access: s.access, kind: s.kind });
  const save = useMutation({
    mutationFn: () => api.updateSource(s.id, f),
    onSuccess: () => { qc.invalidateQueries({ queryKey }); onClose(); },
  });
  return (
    <Dialog title="Edit link" onClose={onClose}>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        <Field id="es-title" label="Title"><input id="es-title" className="input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field>
        <Field id="es-url" label="Link"><input id="es-url" className="input" type="url" value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} /></Field>
        <Field id="es-sum" label="One-line summary"><textarea id="es-sum" className="input" rows={2} value={f.summary} onChange={(e) => setF({ ...f, summary: e.target.value })} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field id="es-kind" label="Type">
            <select id="es-kind" className="input" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value as SourceKind })}>
              {Object.entries(KIND).map(([v, k]) => <option key={v} value={v}>{k.label}</option>)}
            </select>
          </Field>
          <Field id="es-acc" label="Access">
            <select id="es-acc" className="input" value={f.access} onChange={(e) => setF({ ...f, access: e.target.value as Access })}>
              {Object.entries(ACCESS).map(([v, a]) => <option key={v} value={v}>{a.label}</option>)}
            </select>
          </Field>
        </div>
        {save.isError && <ErrorBox error={save.error} />}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-outline btn-sm" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary btn-sm" disabled={save.isPending}>Save</button>
        </div>
      </form>
    </Dialog>
  );
}

export function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="label text-sm">{label}</label>
      {children}
      {hint && <span className="text-xs text-muted">{hint}</span>}
    </div>
  );
}

/** Admin: paste a link; type and access are worked out from the address. */
export function AddSource({ topicId, queryKey }: { topicId: number; queryKey: QueryKey }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ url: "", title: "", summary: "" });
  const add = useMutation({
    mutationFn: () => api.addSource(topicId, f),
    onSuccess: () => { qc.invalidateQueries({ queryKey }); setF({ url: "", title: "", summary: "" }); setOpen(false); },
  });
  if (!open) return (
    <button type="button" className="btn-outline btn-sm self-start" onClick={() => setOpen(true)}><Icon.plus size={16} /> Add link</button>
  );
  return (
    <form className="card p-4 flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
      <Field id="as-url" label="Link" hint="YouTube, Coursera, a university page, Medium, docs, arXiv… The type and login need are detected.">
        <input id="as-url" className="input" type="url" required placeholder="https://" value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} />
      </Field>
      <div className="grid sm:grid-cols-2 gap-3">
        <Field id="as-title" label="Title"><input id="as-title" className="input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field>
        <Field id="as-sum" label="One-line summary (optional)"><input id="as-sum" className="input" value={f.summary} onChange={(e) => setF({ ...f, summary: e.target.value })} /></Field>
      </div>
      {add.isError && <ErrorBox error={add.error} />}
      <div className="flex gap-2">
        <button type="submit" className="btn-primary btn-sm" disabled={add.isPending}>Add link</button>
        <button type="button" className="btn-outline btn-sm" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  );
}

/** Small hook: refetch a query every few seconds while something is being written. */
export function usePoll<T>(key: QueryKey, fn: () => Promise<T>, busy: (d: T | undefined) => boolean, enabled = true) {
  return useQuery({ queryKey: key, queryFn: fn, enabled, refetchInterval: (q) => (busy(q.state.data as T | undefined) ? 3000 : false) });
}
