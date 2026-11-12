import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, type PathDetail, type PathSummary } from "../api";
import { IconButton, Modal, MyLinksSection, PathForm, useRefreshAll } from "../components/Manage";
import { ErrorBox, Icon, ProgressBar, Thinking } from "../components/ui";

type ModuleT = PathDetail["module_list"][number];
type LessonT = ModuleT["lessons"][number];

/** Runs one edit at a time and refreshes every page's data afterwards. */
function useEdit() {
  const refresh = useRefreshAll();
  return useMutation({ mutationFn: (fn: () => Promise<unknown>) => fn(), onSuccess: refresh });
}

// ---------------------------------------------------------------- list

export function PathsList() {
  const paths = useQuery({ queryKey: ["paths"], queryFn: api.paths });
  const navigate = useNavigate();
  const [form, setForm] = useState<PathSummary | "new" | null>(null);
  const edit = useEdit();
  const list = paths.data ?? [];

  return (
    <main className="max-w-[1100px] mx-auto w-full px-4 sm:px-8 py-8 flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="h-display text-3xl">My learning paths</h1>
          <p className="text-muted mt-1">Edit, reorder, hide from home or delete any course. Order here is the order on your home page.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-outline" onClick={() => setForm("new")}><Icon.plus /> Create my own course</button>
          <Link to="/setup" className="btn-primary">+ New learning goal</Link>
        </div>
      </div>
      {paths.isLoading && <Thinking label="Loading…" />}
      {paths.isError && <ErrorBox error={paths.error} onRetry={() => paths.refetch()} />}
      {edit.isError && <ErrorBox error={edit.error} />}
      <ul className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}>
        {list.map((p, i) => (
          <li key={p.id} className={`card h-full p-5 flex flex-col gap-3 ${p.show_on_home ? "" : "bg-ground"}`}>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="chip bg-[#F1F3F6] text-body capitalize">{p.level}</span>
              {p.is_seed && <span className="chip bg-accent-soft text-accent-dark">Starter path</span>}
              {p.kind === "interview" && <span className="chip bg-pp-bg text-pp-fg">Interview prep</span>}
              {!p.show_on_home && <span className="chip bg-[#E3E6EC] text-body">Hidden from home</span>}
              {p.status === "building" && <span className="chip bg-pp-bg text-pp-fg">Building…</span>}
              {p.status === "failed" && <span className="chip bg-yt-bg text-yt-fg">Build failed</span>}
            </div>
            <h2 className="h-display text-xl"><Link to={`/paths/${p.id}`} className="hover:text-accent">{p.title}</Link></h2>
            <p className="text-sm text-body line-clamp-3">{p.summary}</p>
            <div className="mt-auto flex flex-col gap-1.5">
              <ProgressBar pct={p.pct} label={`${p.pct}% complete`} />
              <span className="text-[13px] text-muted">{p.done}/{p.lessons} lessons · {p.modules} modules · {p.hours_per_week} h/week</span>
            </div>
            <div className="flex items-center gap-1.5 pt-1 border-t border-[#EEF0F3]">
              <IconButton label={`Edit "${p.title}"`} onClick={() => setForm(p)}><Icon.edit size={16} /></IconButton>
              <IconButton label="Move earlier" disabled={i === 0 || edit.isPending} onClick={() => edit.mutate(() => api.movePath(p.id, "up"))}><Icon.up size={16} /></IconButton>
              <IconButton label="Move later" disabled={i === list.length - 1 || edit.isPending} onClick={() => edit.mutate(() => api.movePath(p.id, "down"))}><Icon.down size={16} /></IconButton>
              <button type="button" className="btn-outline btn-sm" disabled={edit.isPending}
                onClick={() => edit.mutate(() => api.updatePath(p.id, { show_on_home: !p.show_on_home }))}>
                {p.show_on_home ? "Hide from home" : "Show on home"}
              </button>
              <span className="flex-1" />
              <IconButton danger label={`Delete "${p.title}"`} disabled={edit.isPending}
                onClick={() => { if (confirm(`Delete "${p.title}" with its lessons, notes and progress?`)) edit.mutate(() => api.deletePath(p.id)); }}>
                <Icon.trash size={16} />
              </IconButton>
            </div>
          </li>
        ))}
      </ul>
      {form && (
        <Modal title={form === "new" ? "Create my own course" : "Edit course"} onClose={() => setForm(null)}>
          <PathForm path={form === "new" ? undefined : form}
            onDone={(p) => { const isNew = form === "new"; setForm(null); if (isNew && p) navigate(`/paths/${p.id}?edit=1`); }} />
        </Modal>
      )}
    </main>
  );
}

// ---------------------------------------------------------------- one path

export default function PathPage() {
  const id = Number(useParams().id);
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { hash, search } = useLocation();
  const [editing, setEditing] = useState(() => new URLSearchParams(search).has("edit"));
  const [details, setDetails] = useState(false);
  const path = useQuery({
    queryKey: ["path", id], queryFn: () => api.path(id),
    refetchInterval: (q) => (q.state.data?.module_list.some((m) => m.resources_status === "searching") ? 4000 : false),
  });
  const links = useQuery({ queryKey: ["links", id], queryFn: () => api.links(id) });
  const searching = path.data?.module_list.some((m) => m.resources_status === "searching");

  useEffect(() => {
    if (hash && path.data) document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: "smooth" });
  }, [hash, path.data]);
  useEffect(() => { if (path.data && path.data.modules === 0) setEditing(true); }, [path.data]);

  const find = useMutation({
    mutationFn: (moduleIds?: number[]) => api.findResources(id, moduleIds),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["path", id] }),
  });
  const del = useMutation({
    mutationFn: () => api.deletePath(id),
    onSuccess: () => { qc.invalidateQueries(); navigate("/paths"); },
  });
  const edit = useEdit();

  if (path.isLoading) return <main className="p-8"><Thinking label="Loading path…" /></main>;
  if (path.isError) return <main className="p-8"><ErrorBox error={path.error} onRetry={() => path.refetch()} /></main>;
  const p = path.data!;

  return (
    <main className="max-w-[960px] mx-auto w-full px-4 sm:px-8 py-8 flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        <Link to="/paths" className="text-sm text-accent font-semibold">← My paths</Link>
        <div className="flex flex-wrap items-start gap-3">
          <h1 className="h-display text-3xl sm:text-4xl flex-1 min-w-[240px]">{p.title}</h1>
          <button type="button" aria-pressed={editing} onClick={() => setEditing(!editing)}
            className={editing ? "btn-dark" : "btn-outline"}>
            {editing ? <><Icon.check size={16} /> Done editing</> : <><Icon.edit size={16} /> Edit course</>}
          </button>
        </div>
        {p.summary && <p className="text-body max-w-[720px]">{p.summary}</p>}
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted">
          <span className="capitalize">{p.level}</span>·<span>{p.modules} modules, {p.lessons} lessons</span>·<span>{p.hours_per_week} h/week for {p.weeks} weeks</span>
          {!p.show_on_home && <span className="chip bg-[#E3E6EC] text-body">Hidden from home</span>}
        </div>
        {p.lessons > 0 && <div className="max-w-[480px]"><ProgressBar pct={p.pct} label={`${p.pct}% complete`} /></div>}
        <div className="flex flex-wrap gap-2 pt-1">
          {editing ? (
            <>
              <button type="button" className="btn-outline" onClick={() => setDetails(true)}><Icon.edit size={16} /> Title, description & schedule</button>
              <button type="button" className="btn-outline" disabled={edit.isPending}
                onClick={() => edit.mutate(() => api.updatePath(id, { show_on_home: !p.show_on_home }))}>
                {p.show_on_home ? "Hide from home" : "Show on home"}
              </button>
              <button type="button" className="btn-outline text-yt-fg" disabled={del.isPending}
                onClick={() => { if (confirm(`Delete "${p.title}" with its lessons, notes and progress?`)) del.mutate(); }}>
                <Icon.trash size={16} /> Delete course
              </button>
            </>
          ) : (
            <>
              {p.current_lesson_id && <Link to={`/lessons/${p.current_lesson_id}`} className="btn-primary">{p.done ? "Continue" : "Start"} learning</Link>}
              {p.lessons > 0 && (
                <button type="button" className="btn-outline" disabled={searching || find.isPending} onClick={() => find.mutate(undefined)}>
                  <Icon.search size={16} /> {searching ? "Agents searching…" : "Find videos & papers for all modules"}
                </button>
              )}
            </>
          )}
        </div>
        {find.isError && <ErrorBox error={find.error} />}
        {del.isError && <ErrorBox error={del.error} />}
        {edit.isError && <ErrorBox error={edit.error} />}
      </div>

      {p.module_list.length === 0 && (
        <p className="card p-5 text-body">This course has no modules yet. Add the first one below, then add lessons to it.</p>
      )}

      <ol className="flex flex-col gap-4">
        {p.module_list.map((m, i) => (
          <ModuleCard key={m.id} m={m} editing={editing} first={i === 0} last={i === p.module_list.length - 1}
            busy={!!searching || find.isPending} onFind={() => find.mutate([m.id])} />
        ))}
      </ol>
      {editing && <AddModule pathId={id} />}

      <MyLinksSection links={links.data ?? []} pathId={id} showPath={false} title="Courses & links for this path"
        intro="Your own extra material for this path. It also shows on the home page while this path is selected." />

      {details && (
        <Modal title="Edit course" onClose={() => setDetails(false)}>
          <PathForm path={p} onDone={() => setDetails(false)} />
        </Modal>
      )}
    </main>
  );
}

function ModuleCard({ m, editing, first, last, busy, onFind }: {
  m: ModuleT; editing: boolean; first: boolean; last: boolean; busy: boolean; onFind: () => void;
}) {
  const edit = useEdit();
  const [renaming, setRenaming] = useState(false);
  const [title, setTitle] = useState(m.title);
  const [summary, setSummary] = useState(m.summary);
  const done = m.lessons.filter((l) => l.status === "done").length;
  const saveModule = (e: FormEvent) => {
    e.preventDefault();
    edit.mutate(() => api.updateModule(m.id, { title, summary }).then(() => setRenaming(false)));
  };

  return (
    <li id={`module-${m.id}`} className="card p-5 flex flex-col gap-3 scroll-mt-4">
      {renaming ? (
        <form onSubmit={saveModule} className="flex flex-col gap-2">
          <label className="label text-sm" htmlFor={`mt-${m.id}`}>Module title</label>
          <input id={`mt-${m.id}`} className="input" required value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
          <label className="label text-sm" htmlFor={`ms-${m.id}`}>Description</label>
          <textarea id={`ms-${m.id}`} className="input min-h-[64px]" value={summary} onChange={(e) => setSummary(e.target.value)} />
          <div className="flex gap-2 justify-end">
            <button type="button" className="btn-outline btn-sm" onClick={() => { setRenaming(false); setTitle(m.title); setSummary(m.summary); }}>Cancel</button>
            <button type="submit" className="btn-primary btn-sm" disabled={edit.isPending}>Save</button>
          </div>
        </form>
      ) : (
        <div className="flex flex-wrap items-start gap-3">
          <div className="flex-1 min-w-[240px]">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">Module {m.idx + 1} · {done}/{m.lessons.length} done</p>
            <h2 className="text-lg font-semibold">{m.title}</h2>
            {m.summary && <p className="text-sm text-body">{m.summary}</p>}
          </div>
          {editing ? (
            <div className="flex gap-1.5">
              <IconButton label={`Rename module "${m.title}"`} onClick={() => setRenaming(true)}><Icon.edit size={16} /></IconButton>
              <IconButton label="Move module up" disabled={first || edit.isPending} onClick={() => edit.mutate(() => api.moveModule(m.id, "up"))}><Icon.up size={16} /></IconButton>
              <IconButton label="Move module down" disabled={last || edit.isPending} onClick={() => edit.mutate(() => api.moveModule(m.id, "down"))}><Icon.down size={16} /></IconButton>
              <IconButton danger label={`Delete module "${m.title}"`} disabled={edit.isPending}
                onClick={() => { if (confirm(`Delete module "${m.title}" and its ${m.lessons.length} lessons?`)) edit.mutate(() => api.deleteModule(m.id)); }}>
                <Icon.trash size={16} />
              </IconButton>
            </div>
          ) : m.lessons.length > 0 && (
            m.resources_status === "searching" ? <Thinking label="Searching" /> : (
              <button type="button" className="btn-outline btn-sm" disabled={busy} onClick={onFind}>
                <Icon.refresh size={14} /> {m.resources_status === "ready" ? "Refresh resources" : "Find resources"}
              </button>
            )
          )}
        </div>
      )}
      {edit.isError && <ErrorBox error={edit.error} />}

      <ol className="flex flex-col divide-y divide-[#EEF0F3]">
        {m.lessons.map((l, i) => editing
          ? <LessonEditRow key={l.id} l={l} first={i === 0} last={i === m.lessons.length - 1} />
          : (
            <li key={l.id}>
              <Link to={`/lessons/${l.id}`} className="flex items-center gap-3 py-2.5 px-1 rounded-lg hover:bg-ground">
                <LessonDot l={l} />
                <span className="flex-1 font-medium">{l.title}</span>
                <span className="hidden sm:inline text-xs text-muted">{l.videos ? `${l.videos} video${l.videos > 1 ? "s" : ""}` : ""}{l.videos && l.papers ? " · " : ""}{l.papers ? `${l.papers} paper${l.papers > 1 ? "s" : ""}` : ""}</span>
                <span className="text-xs text-muted w-12 text-right">{l.est_minutes} min</span>
              </Link>
            </li>
          ))}
      </ol>
      {m.lessons.length === 0 && !editing && <p className="text-sm text-muted">No lessons yet. Use “Edit course” to add some.</p>}
      {editing && <AddLesson moduleId={m.id} />}
    </li>
  );
}

function LessonDot({ l }: { l: LessonT }) {
  return (
    <span className={`w-6 h-6 shrink-0 rounded-full flex items-center justify-center text-xs font-bold ${l.status === "done" ? "bg-ok text-white" : l.status === "doing" ? "bg-accent text-white" : "border-2 border-[#C9CED8] text-muted"}`}>
      {l.status === "done" ? <Icon.check size={13} /> : l.idx + 1}
    </span>
  );
}

function LessonFields({ prefix, title, setTitle, minutes, setMinutes, objectives, setObjectives }: {
  prefix: string; title: string; setTitle: (v: string) => void; minutes: number; setMinutes: (v: number) => void;
  objectives: string; setObjectives: (v: string) => void;
}) {
  return (
    <>
      <div className="grid gap-2 sm:grid-cols-[1fr_120px]">
        <div className="flex flex-col gap-1">
          <label className="label text-sm" htmlFor={`${prefix}-t`}>Lesson title</label>
          <input id={`${prefix}-t`} className="input" required value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
        </div>
        <div className="flex flex-col gap-1">
          <label className="label text-sm" htmlFor={`${prefix}-m`}>Minutes</label>
          <input id={`${prefix}-m`} type="number" min={1} max={600} className="input" value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} />
        </div>
      </div>
      <div className="flex flex-col gap-1">
        <label className="label text-sm" htmlFor={`${prefix}-o`}>What you'll learn (optional, one per line)</label>
        <textarea id={`${prefix}-o`} className="input min-h-[64px]" value={objectives} onChange={(e) => setObjectives(e.target.value)} />
      </div>
    </>
  );
}

const lines = (s: string) => s.split("\n").map((x) => x.trim()).filter(Boolean);

function LessonEditRow({ l, first, last }: { l: LessonT; first: boolean; last: boolean }) {
  const edit = useEdit();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState(l.title);
  const [minutes, setMinutes] = useState(l.est_minutes);
  const [objectives, setObjectives] = useState(l.objectives.join("\n"));

  if (open) {
    return (
      <li className="py-3">
        <form className="flex flex-col gap-2"
          onSubmit={(e) => { e.preventDefault(); edit.mutate(() => api.updateLesson(l.id, { title, est_minutes: minutes, objectives: lines(objectives) }).then(() => setOpen(false))); }}>
          <LessonFields prefix={`le-${l.id}`} {...{ title, setTitle, minutes, setMinutes, objectives, setObjectives }} />
          {edit.isError && <ErrorBox error={edit.error} />}
          <div className="flex gap-2 justify-end">
            <button type="button" className="btn-outline btn-sm" onClick={() => setOpen(false)}>Cancel</button>
            <button type="submit" className="btn-primary btn-sm" disabled={edit.isPending}>Save lesson</button>
          </div>
        </form>
      </li>
    );
  }
  return (
    <li className="flex items-center gap-2 py-2 px-1">
      <LessonDot l={l} />
      <span className="flex-1 min-w-0 font-medium truncate">{l.title}</span>
      <span className="hidden sm:inline text-xs text-muted w-12 text-right">{l.est_minutes} min</span>
      <IconButton label={`Edit lesson "${l.title}"`} onClick={() => setOpen(true)}><Icon.edit size={15} /></IconButton>
      <IconButton label="Move lesson up" disabled={first || edit.isPending} onClick={() => edit.mutate(() => api.moveLesson(l.id, "up"))}><Icon.up size={15} /></IconButton>
      <IconButton label="Move lesson down" disabled={last || edit.isPending} onClick={() => edit.mutate(() => api.moveLesson(l.id, "down"))}><Icon.down size={15} /></IconButton>
      <IconButton danger label={`Delete lesson "${l.title}"`} disabled={edit.isPending}
        onClick={() => { if (confirm(`Delete lesson "${l.title}" with its notes?`)) edit.mutate(() => api.deleteLesson(l.id)); }}>
        <Icon.trash size={15} />
      </IconButton>
    </li>
  );
}

function AddLesson({ moduleId }: { moduleId: number }) {
  const edit = useEdit();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [minutes, setMinutes] = useState(20);
  const [objectives, setObjectives] = useState("");
  if (!open) {
    return <button type="button" className="btn-outline btn-sm self-start" onClick={() => setOpen(true)}><Icon.plus size={16} /> Add lesson</button>;
  }
  const reset = () => { setTitle(""); setMinutes(20); setObjectives(""); };
  return (
    <form className="flex flex-col gap-2 p-3 rounded-xl bg-ground"
      onSubmit={(e) => { e.preventDefault(); edit.mutate(() => api.addLesson(moduleId, { title, est_minutes: minutes, objectives: lines(objectives) }).then(reset)); }}>
      <LessonFields prefix={`nl-${moduleId}`} {...{ title, setTitle, minutes, setMinutes, objectives, setObjectives }} />
      {edit.isError && <ErrorBox error={edit.error} />}
      <div className="flex gap-2 justify-end">
        <button type="button" className="btn-outline btn-sm" onClick={() => { setOpen(false); reset(); }}>Close</button>
        <button type="submit" className="btn-primary btn-sm" disabled={edit.isPending}>Add lesson</button>
      </div>
    </form>
  );
}

function AddModule({ pathId }: { pathId: number }) {
  const edit = useEdit();
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  return (
    <form className="card border-dashed p-5 flex flex-col gap-2"
      onSubmit={(e) => { e.preventDefault(); edit.mutate(() => api.addModule(pathId, { title, summary }).then(() => { setTitle(""); setSummary(""); })); }}>
      <h2 className="font-semibold">Add a module</h2>
      <label className="label text-sm" htmlFor="new-mod-t">Module title</label>
      <input id="new-mod-t" className="input" required value={title} onChange={(e) => setTitle(e.target.value)} />
      <label className="label text-sm" htmlFor="new-mod-s">Description (optional)</label>
      <textarea id="new-mod-s" className="input min-h-[56px]" value={summary} onChange={(e) => setSummary(e.target.value)} />
      {edit.isError && <ErrorBox error={edit.error} />}
      <button type="submit" className="btn-primary self-end" disabled={edit.isPending}><Icon.plus size={16} /> Add module</button>
    </form>
  );
}
