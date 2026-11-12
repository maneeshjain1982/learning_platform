// Editing UI: your own courses & links, and the add/edit course form.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from "react";
import { api, type LinkKind, type MyLink, type PathInput, type PathSummary } from "../api";
import { ErrorBox, Icon, SourceBadge } from "./ui";

/** Refresh everything after an edit (home, paths, path pages, links all read the same data). */
export function useRefreshAll() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries();
}

// ---------------------------------------------------------------- dialog

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    const d = ref.current;
    if (d && !d.open) d.showModal();
    return () => d?.close();
  }, []);
  return (
    <dialog ref={ref} aria-labelledby={id} onCancel={(e) => { e.preventDefault(); onClose(); }}
      className="rounded-2xl p-0 w-[min(560px,calc(100vw-32px))] max-h-[calc(100vh-48px)] backdrop:bg-black/40">
      <div className="flex items-center gap-3 px-5 py-4 border-b border-line">
        <h2 id={id} className="h-display text-lg flex-1">{title}</h2>
        <button type="button" onClick={onClose} aria-label="Close"
          className="w-10 h-10 rounded-lg flex items-center justify-center hover:bg-ground"><Icon.close /></button>
      </div>
      <div className="p-5">{children}</div>
    </dialog>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: (id: string) => ReactNode }) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="label text-sm">{label}</label>
      {children(id)}
      {hint && <p className="text-[13px] text-muted">{hint}</p>}
    </div>
  );
}

export function IconButton({ label, onClick, disabled, children, danger }: {
  label: string; onClick: () => void; disabled?: boolean; children: ReactNode; danger?: boolean;
}) {
  return (
    <button type="button" aria-label={label} title={label} disabled={disabled} onClick={onClick}
      className={`w-9 h-9 shrink-0 rounded-lg border border-line2 bg-white flex items-center justify-center hover:bg-ground disabled:opacity-40 disabled:cursor-not-allowed ${danger ? "text-yt-fg" : "text-body"}`}>
      {children}
    </button>
  );
}

// ---------------------------------------------------------------- link form

const KINDS: { value: LinkKind; label: string }[] = [
  { value: "course", label: "Course" }, { value: "video", label: "Video or playlist" },
  { value: "doc", label: "Docs or book" }, { value: "paper", label: "Paper" }, { value: "link", label: "Other link" },
];

export function LinkForm({ link, defaultPathId, onDone }: { link?: MyLink; defaultPathId?: number | null; onDone: () => void }) {
  const refresh = useRefreshAll();
  const paths = useQuery({ queryKey: ["paths"], queryFn: api.paths });
  const [url, setUrl] = useState(link?.url ?? "");
  const [title, setTitle] = useState(link?.title ?? "");
  const [kind, setKind] = useState<LinkKind | "auto">(link?.kind ?? "auto");
  const [note, setNote] = useState(link?.note ?? "");
  const [pathId, setPathId] = useState<number | null>(link ? link.path_id : defaultPathId ?? null);
  const [onHome, setOnHome] = useState(link?.show_on_home ?? true);
  const [status, setStatus] = useState<MyLink["status"]>(link?.status ?? "todo");

  const save = useMutation({
    mutationFn: () => {
      const body = { url, title: title.trim(), note, show_on_home: onHome, ...(kind === "auto" ? {} : { kind }) };
      if (!link) return api.createLink({ ...body, path_id: pathId });
      return api.updateLink(link.id, { ...body, status, ...(pathId === null ? { clear_path: true } : { path_id: pathId }) });
    },
    onSuccess: () => { refresh(); onDone(); },
  });
  const submit = (e: FormEvent) => { e.preventDefault(); save.mutate(); };

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <Field label="Web address" hint="Paste a link to a Udemy or Coursera course, a YouTube playlist, docs, a blog post…">
        {(id) => <input id={id} className="input" required value={url} onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.udemy.com/course/…" inputMode="url" autoFocus={!link} />}
      </Field>
      <Field label="Title" hint={link ? undefined : "Leave blank and the page's own title is used."}>
        {(id) => <input id={id} className="input" value={title} onChange={(e) => setTitle(e.target.value)} required={!!link} />}
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Type">
          {(id) => (
            <select id={id} className="input" value={kind} onChange={(e) => setKind(e.target.value as LinkKind | "auto")}>
              {!link && <option value="auto">Detect from the address</option>}
              {KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
            </select>
          )}
        </Field>
        <Field label="Belongs to">
          {(id) => (
            <select id={id} className="input" value={pathId ?? ""} onChange={(e) => setPathId(e.target.value ? Number(e.target.value) : null)}>
              <option value="">All paths (general)</option>
              {paths.data?.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
          )}
        </Field>
      </div>
      {link && (
        <Field label="Progress">
          {(id) => (
            <select id={id} className="input" value={status} onChange={(e) => setStatus(e.target.value as MyLink["status"])}>
              <option value="todo">Not started</option><option value="doing">In progress</option><option value="done">Finished</option>
            </select>
          )}
        </Field>
      )}
      <Field label="Note (optional)">
        {(id) => <textarea id={id} className="input min-h-[72px]" value={note} onChange={(e) => setNote(e.target.value)}
          placeholder="Why it matters, which sections to watch…" />}
      </Field>
      <label className="flex items-center gap-2.5 font-medium">
        <input type="checkbox" className="w-5 h-5 accent-accent" checked={onHome} onChange={(e) => setOnHome(e.target.checked)} />
        Show on my home page
      </label>
      {save.isError && <ErrorBox error={save.error} />}
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-outline" onClick={onDone}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={save.isPending}>{save.isPending ? "Saving…" : link ? "Save changes" : "Add"}</button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------- link card + section

const KIND_LABEL: Record<LinkKind, string> = { course: "Course", video: "Video", doc: "Docs", paper: "Paper", link: "Link" };
const STATUS_NEXT = { todo: "doing", doing: "done", done: "todo" } as const;
const STATUS_LABEL = { todo: "Not started", doing: "In progress", done: "Finished" };
const STATUS_CLS = { todo: "bg-[#F1F3F6] text-muted", doing: "bg-accent-soft text-accent-dark", done: "bg-ok-soft text-ok-dark" };

export function MyLinkCard({ link, onEdit, first, last, showPath = true }: {
  link: MyLink; onEdit: () => void; first: boolean; last: boolean; showPath?: boolean;
}) {
  const refresh = useRefreshAll();
  const m = useMutation({ mutationFn: (fn: () => Promise<unknown>) => fn(), onSuccess: refresh });
  return (
    <article className="card p-4 flex flex-col gap-2">
      <div className="flex items-center gap-2 flex-wrap">
        <SourceBadge source={link.provider} />
        <span className="chip bg-[#F1F3F6] text-body">{KIND_LABEL[link.kind]}</span>
        <button type="button" onClick={() => m.mutate(() => api.updateLink(link.id, { status: STATUS_NEXT[link.status] }))}
          className={`chip ${STATUS_CLS[link.status]} hover:ring-1 hover:ring-line2`}
          title="Change progress" aria-label={`Progress: ${STATUS_LABEL[link.status]}. Click to change.`}>
          {link.status === "done" && <Icon.check size={12} />}{STATUS_LABEL[link.status]}
        </button>
      </div>
      <h3 className="font-semibold leading-snug">
        <a href={link.url} target="_blank" rel="noreferrer" className="hover:text-accent inline-flex gap-1.5 items-start">
          <span>{link.title}</span><Icon.external size={14} className="mt-1 shrink-0 text-muted" />
        </a>
      </h3>
      {link.note && <p className="text-[13px] text-body whitespace-pre-line">{link.note}</p>}
      <p className="text-[13px] text-muted">
        {showPath && (link.path_title ? `For ${link.path_title}` : "General")}
        {!link.show_on_home && <>{showPath ? " · " : ""}Hidden from home</>}
      </p>
      <div className="mt-auto pt-1 flex items-center gap-1.5">
        <IconButton label={`Edit "${link.title}"`} onClick={onEdit}><Icon.edit size={16} /></IconButton>
        <IconButton label="Move earlier" disabled={first || m.isPending} onClick={() => m.mutate(() => api.moveLink(link.id, "up"))}><Icon.up size={16} /></IconButton>
        <IconButton label="Move later" disabled={last || m.isPending} onClick={() => m.mutate(() => api.moveLink(link.id, "down"))}><Icon.down size={16} /></IconButton>
        <span className="flex-1" />
        <IconButton danger label={`Delete "${link.title}"`} disabled={m.isPending}
          onClick={() => { if (confirm(`Delete "${link.title}"?`)) m.mutate(() => api.deleteLink(link.id)); }}><Icon.trash size={16} /></IconButton>
      </div>
      {m.isError && <ErrorBox error={m.error} />}
    </article>
  );
}

/** "My courses & links" block used on Home, a path page, and the My links page. */
export function MyLinksSection({ links, title, intro, pathId, showPath = true, headingLevel = 2 }: {
  links: MyLink[]; title: string; intro?: string; pathId?: number | null; showPath?: boolean; headingLevel?: 1 | 2;
}) {
  const [editing, setEditing] = useState<MyLink | "new" | null>(null);
  const H = headingLevel === 1 ? "h1" : "h2";
  const id = useId();
  return (
    <section aria-labelledby={id} className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <H id={id} className={`h-display ${headingLevel === 1 ? "text-3xl" : "text-[22px]"}`}>{title}</H>
          {intro && <p className="text-muted mt-1">{intro}</p>}
        </div>
        <button type="button" className="btn-outline" onClick={() => setEditing("new")}><Icon.plus /> Add course or link</button>
      </div>
      {links.length === 0 ? (
        <button type="button" onClick={() => setEditing("new")}
          className="card border-dashed p-6 text-left hover:border-accent flex items-center gap-4">
          <span className="w-11 h-11 rounded-full bg-accent-soft text-accent flex items-center justify-center shrink-0"><Icon.link /></span>
          <span>
            <span className="block font-semibold">Add a course or an important link</span>
            <span className="block text-sm text-muted">A course you're taking on Udemy or Coursera, a playlist, docs or an article.</span>
          </span>
        </button>
      ) : (
        <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))" }}>
          {links.map((l, i) => (
            <MyLinkCard key={l.id} link={l} showPath={showPath} first={i === 0} last={i === links.length - 1} onEdit={() => setEditing(l)} />
          ))}
        </div>
      )}
      {editing && (
        <Modal title={editing === "new" ? "Add a course or link" : "Edit course or link"} onClose={() => setEditing(null)}>
          <LinkForm link={editing === "new" ? undefined : editing} defaultPathId={pathId} onDone={() => setEditing(null)} />
        </Modal>
      )}
    </section>
  );
}

// ---------------------------------------------------------------- course (path) form

export function PathForm({ path, onDone }: { path?: PathSummary; onDone: (p?: PathSummary) => void }) {
  const refresh = useRefreshAll();
  const [f, setF] = useState<PathInput>({
    title: path?.title ?? "", summary: path?.summary ?? "", level: path?.level ?? "intermediate",
    hours_per_week: path?.hours_per_week ?? 5, weeks: path?.weeks ?? 6, show_on_home: path?.show_on_home ?? true,
  });
  const [modules, setModules] = useState("");
  const set = <K extends keyof PathInput>(k: K, v: PathInput[K]) => setF((o) => ({ ...o, [k]: v }));
  const save = useMutation({
    mutationFn: () => path ? api.updatePath(path.id, f)
      : api.createPath({ ...f, modules: modules.split("\n").map((s) => s.trim()).filter(Boolean) }),
    onSuccess: (p) => { refresh(); onDone(p); },
  });
  return (
    <form onSubmit={(e) => { e.preventDefault(); save.mutate(); }} className="flex flex-col gap-4">
      <Field label="Course title">
        {(id) => <input id={id} className="input" required maxLength={200} value={f.title} onChange={(e) => set("title", e.target.value)} autoFocus />}
      </Field>
      <Field label="Description">
        {(id) => <textarea id={id} className="input min-h-[80px]" value={f.summary} onChange={(e) => set("summary", e.target.value)} />}
      </Field>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Level">
          {(id) => (
            <select id={id} className="input" value={f.level} onChange={(e) => set("level", e.target.value)}>
              <option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option>
            </select>
          )}
        </Field>
        <Field label="Hours per week">
          {(id) => <input id={id} type="number" min={1} max={60} className="input" value={f.hours_per_week} onChange={(e) => set("hours_per_week", Number(e.target.value))} />}
        </Field>
        <Field label="Weeks">
          {(id) => <input id={id} type="number" min={1} max={52} className="input" value={f.weeks} onChange={(e) => set("weeks", Number(e.target.value))} />}
        </Field>
      </div>
      {!path && (
        <Field label="Modules (optional)" hint="One per line. You can add lessons to each module afterwards.">
          {(id) => <textarea id={id} className="input min-h-[96px]" value={modules} onChange={(e) => setModules(e.target.value)}
            placeholder={"Basics\nHands-on project\nAdvanced topics"} />}
        </Field>
      )}
      <label className="flex items-center gap-2.5 font-medium">
        <input type="checkbox" className="w-5 h-5 accent-accent" checked={f.show_on_home} onChange={(e) => set("show_on_home", e.target.checked)} />
        Show on my home page
      </label>
      {save.isError && <ErrorBox error={save.error} />}
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-outline" onClick={() => onDone()}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={save.isPending}>{save.isPending ? "Saving…" : path ? "Save changes" : "Create course"}</button>
      </div>
    </form>
  );
}
