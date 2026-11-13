import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, type PaperRef, type PaperSummaryOut, type PaperSummaryT } from "../api";
import { useMe } from "./Auth";
import { ErrorBox, Thinking } from "./ui";

const key = (ref: PaperRef) => ["paper-summary", ref.resource_id ?? ref.url];

/** "Summarize" button for any paper, with the summary opening underneath. Summaries are shared by all accounts;
 * the admin can regenerate, edit or delete them. */
export function PaperSummary({ paper, has, context }: { paper: PaperRef; has?: boolean; context?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="w-full flex flex-col gap-2">
      <div>
        <button type="button" className="btn-outline btn-sm" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "Hide summary" : has ? "Summary" : "Summarize"}
        </button>
      </div>
      {open && <Panel paper={paper} context={context} />}
    </div>
  );
}

function Panel({ paper, context }: { paper: PaperRef; context?: string }) {
  const qc = useQueryClient();
  const me = useMe();
  const [editing, setEditing] = useState(false);
  const q = useQuery({
    queryKey: key(paper), queryFn: () => api.paperSummary(paper),
    refetchInterval: (s) => (s.state.data?.job.status === "running" ? 3000 : false),
  });
  const set = (d: PaperSummaryOut) => qc.setQueryData(key(paper), d);
  const gen = useMutation({ mutationFn: () => api.summarizePaper({ ...paper, context }), onSuccess: set });
  const del = useMutation({
    mutationFn: () => api.deletePaperSummary(q.data!.resource_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: key(paper) }),
  });
  // Opening a paper with no summary starts writing one.
  const d = q.data;
  useEffect(() => {
    if (d && !d.summary && d.job.status === "idle" && !gen.isPending && !gen.isSuccess) gen.mutate();
  }, [d]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {  // the list's "Summary" label comes from the resource; refresh it once a summary exists
    if (d?.summary) qc.invalidateQueries({ predicate: (x) => ["home", "lesson", "discover"].includes(String(x.queryKey[0])) });
  }, [!!d?.summary]); // eslint-disable-line react-hooks/exhaustive-deps

  if (q.isLoading) return <Thinking label="Loading summary…" />;
  if (q.isError) return <ErrorBox error={q.error} onRetry={() => q.refetch()} />;
  if (!d) return null;
  const running = d.job.status === "running" || gen.isPending;

  return (
    <section aria-label={`Summary of ${d.title}`} className="rounded-xl border border-accent-line bg-accent-soft/40 p-4 flex flex-col gap-3">
      {running && <Thinking label="Reading the paper and writing a summary (about a minute)…" />}
      {d.job.status === "failed" && !running && (
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-sm text-body">Couldn't write the summary: {d.job.error}</p>
          <button type="button" className="btn-outline btn-sm" onClick={() => gen.mutate()}>Try again</button>
        </div>
      )}
      {gen.isError && <ErrorBox error={gen.error} />}
      {d.summary && !editing && <SummaryView s={d.summary} />}
      {d.summary && editing && (
        <EditForm s={d.summary} resourceId={d.resource_id} onDone={(out) => { if (out) set(out); setEditing(false); }} />
      )}
      {d.summary && !editing && me.is_admin && (
        <div className="flex flex-wrap gap-2 pt-1 border-t border-accent-line">
          <button type="button" className="btn-outline btn-sm" onClick={() => setEditing(true)}>Edit</button>
          <button type="button" className="btn-outline btn-sm" disabled={running} onClick={() => gen.mutate()}>Regenerate</button>
          <button type="button" className="btn-outline btn-sm" disabled={del.isPending}
            onClick={() => { if (confirm("Delete this summary for every account?")) del.mutate(); }}>Delete</button>
        </div>
      )}
    </section>
  );
}

function SummaryView({ s }: { s: PaperSummaryT }) {
  const block = (t: string, v: string) => v && (
    <div><h4 className="text-xs font-semibold uppercase tracking-wide text-muted">{t}</h4><p className="text-sm text-body">{v}</p></div>
  );
  const list = (t: string, v: string[]) => v.length > 0 && (
    <div><h4 className="text-xs font-semibold uppercase tracking-wide text-muted">{t}</h4>
      <ul className="list-disc pl-5 text-sm text-body flex flex-col gap-0.5">{v.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
  );
  return (
    <div className="flex flex-col gap-2.5">
      <p className="font-semibold text-ink">{s.tldr}</p>
      <div className="grid gap-3 md:grid-cols-2">
        {block("Problem", s.problem)}
        {block("Method", s.method)}
        {list("Key results", s.results)}
        {list("Limitations", s.limitations)}
      </div>
      {block("Why it matters", s.why_it_matters)}
      <p className="text-xs text-muted">
        {s.read_full_text ? "Written from the full paper" : "Written from the abstract only (full text not readable)"}
        {s.edited ? " · edited" : ""}. Check numbers against the paper.
      </p>
    </div>
  );
}

function EditForm({ s, resourceId, onDone }: { s: PaperSummaryT; resourceId: number; onDone: (out?: PaperSummaryOut) => void }) {
  const [f, setF] = useState({ ...s, results: s.results.join("\n"), limitations: s.limitations.join("\n") });
  const save = useMutation({
    mutationFn: () => api.editPaperSummary(resourceId, {
      ...s, ...f, results: f.results.split("\n"), limitations: f.limitations.split("\n"),
    }),
    onSuccess: (out) => onDone(out),
  });
  const field = (k: keyof typeof f, label: string, rows = 2) => (
    <div className="flex flex-col gap-1">
      <label htmlFor={`ps-${resourceId}-${k}`} className="label">{label}</label>
      <textarea id={`ps-${resourceId}-${k}`} className="input" rows={rows} value={String(f[k])}
        onChange={(e) => setF({ ...f, [k]: e.target.value })} />
    </div>
  );
  return (
    <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      {field("tldr", "TL;DR")}
      {field("problem", "Problem", 3)}
      {field("method", "Method", 3)}
      {field("results", "Key results (one per line)", 4)}
      {field("limitations", "Limitations (one per line)", 3)}
      {field("why_it_matters", "Why it matters")}
      <div className="flex gap-2">
        <button type="submit" className="btn-primary btn-sm" disabled={save.isPending}>Save</button>
        <button type="button" className="btn-outline btn-sm" onClick={() => onDone()}>Cancel</button>
      </div>
      {save.isError && <ErrorBox error={save.error} />}
    </form>
  );
}
