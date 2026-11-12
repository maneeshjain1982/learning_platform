import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, type AIUpdate } from "../api";
import { ErrorBox, Icon, Thinking } from "./ui";

const RANGES = [30, 45, 90];

function ago(isoTime: string) {
  const mins = Math.round((Date.now() - new Date(isoTime).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const h = Math.round(mins / 60);
  if (h < 48) return `${h} hour${h === 1 ? "" : "s"} ago`;
  return `${Math.round(h / 24)} days ago`;
}

function fmtDay(d: string) {
  const t = new Date(`${d}T00:00:00`);
  return isNaN(t.getTime()) ? d : t.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/** "New updates": the LLM searches the web for recent Claude and agent news; every link is checked first. */
export default function AIUpdates() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["ai-updates"], queryFn: api.aiUpdates,
    refetchInterval: (query) => (query.state.data?.status === "running" ? 3000 : false),
  });
  const [days, setDays] = useState<number | null>(null);
  const [cat, setCat] = useState("All");
  const refresh = useMutation({
    mutationFn: (d: number) => api.refreshUpdates(d),
    onSuccess: (data) => qc.setQueryData(["ai-updates"], data),
  });

  const d = q.data;
  const running = d?.status === "running" || refresh.isPending;
  const range = days ?? d?.days ?? 45;
  const items = d?.items ?? [];
  const cats = ["All", ...(d?.categories ?? []).filter((c) => items.some((i) => i.category === c))];
  const shown = cat === "All" ? items : items.filter((i) => i.category === cat);

  return (
    <section aria-labelledby="upd-h" className="card p-5 flex flex-col gap-4">
      <div className="flex flex-wrap items-start gap-3">
        <div className="flex-1 min-w-[240px]">
          <h2 id="upd-h" className="h-display text-2xl">New updates</h2>
          <p className="text-sm text-muted">
            Latest Claude, agent-building and Claude Academy news, found by the LLM with web search. Links are checked
            before they're shown.
            {d?.fetched_at && <> Last refreshed {ago(d.fetched_at)}.</>}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor="upd-days" className="text-sm font-semibold">From the last</label>
          <select id="upd-days" className="input w-auto py-1.5" value={range} disabled={running}
            onChange={(e) => setDays(Number(e.target.value))}>
            {RANGES.map((n) => <option key={n} value={n}>{n} days</option>)}
          </select>
          <button type="button" className="btn-primary" disabled={running} onClick={() => refresh.mutate(range)}>
            <Icon.refresh /> {running ? "Searching…" : "Refresh"}
          </button>
        </div>
      </div>

      {q.isLoading && <Thinking label="Loading…" />}
      {q.isError && <ErrorBox error={q.error} onRetry={() => q.refetch()} />}
      {refresh.isError && <ErrorBox error={refresh.error} />}
      {running && d?.started_at && (
        <Thinking label="Searching the web for updates. This usually takes 1–4 minutes…" since={new Date(d.started_at).getTime()} />
      )}
      {d?.status === "failed" && d.error && (
        <ErrorBox error={`The last refresh didn't finish: ${d.error}`} onRetry={() => refresh.mutate(range)} />
      )}

      {d && items.length === 0 && !running && d.status !== "failed" && (
        <p className="text-body">No updates fetched yet. Press <span className="font-semibold">Refresh</span> to search for the latest news.</p>
      )}

      {items.length > 0 && (
        <>
          {d?.headline && <p className="p-3 rounded-lg bg-[#F6F8FF] border border-accent-line"><span className="font-semibold">Headline: </span>{d.headline}</p>}
          <div role="group" aria-label="Filter by category" className="flex flex-wrap gap-1.5">
            {cats.map((c) => (
              <button key={c} type="button" aria-pressed={cat === c} onClick={() => setCat(c)}
                className={`min-h-[36px] px-3 rounded-full border text-sm font-semibold ${cat === c ? "bg-accent text-white border-accent" : "bg-white border-line2 text-body hover:bg-ground"}`}>
                {c}{c !== "All" && ` (${items.filter((i) => i.category === c).length})`}
              </button>
            ))}
          </div>
          <ul className="flex flex-col divide-y divide-line">
            {shown.map((i) => <UpdateRow key={i.url} i={i} />)}
          </ul>
          {d && d.dropped > 0 && <p className="text-xs text-muted">{d.dropped} item{d.dropped === 1 ? "" : "s"} left out because the link didn't open.</p>}
        </>
      )}
    </section>
  );
}

function UpdateRow({ i }: { i: AIUpdate }) {
  return (
    <li className="py-3.5 flex flex-col gap-1.5">
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span className="chip bg-accent-soft text-accent-dark">{i.category}</span>
        {i.date && <span className="text-muted">{fmtDay(i.date)}</span>}
        {i.is_new && <span className="chip bg-ok-soft text-ok-dark">New since last refresh</span>}
        {i.new_course && <span className="chip bg-pp-bg text-pp-fg">New course, not in the list below yet</span>}
        {!i.verified && <span className="chip bg-[#F1F3F6] text-muted" title="The site blocked our link check, so it couldn't be confirmed">Link not verified</span>}
      </div>
      <h3 className="font-semibold">
        <a href={i.url} target="_blank" rel="noreferrer" className="hover:text-accent inline-flex items-baseline gap-1.5">
          {i.title} <Icon.external size={13} className="text-muted shrink-0" />
        </a>
      </h3>
      <p className="text-body text-sm">{i.summary}</p>
      {i.why_it_matters && <p className="text-sm text-muted"><span className="font-semibold text-body">Why it matters: </span>{i.why_it_matters}</p>}
    </li>
  );
}
