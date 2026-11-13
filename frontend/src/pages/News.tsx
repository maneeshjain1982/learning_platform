import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, type NewsDigest, type NewsItem } from "../api";
import { ErrorBox, Icon, Thinking, ago, fmtDay } from "../components/ui";

const DAYS = [3, 7, 14, 30];

/** Tech News: an LLM digest of the topics you pick (links checked) and live Hacker News headlines. */
export default function News() {
  return (
    <main className="max-w-[1180px] mx-auto w-full px-4 sm:px-8 py-8 flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="h-display text-3xl">Tech News</h1>
        <p className="text-muted">Your digest by topic, and what's live on Hacker News.</p>
      </header>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px] items-start">
        <Digest />
        <Live />
      </div>
    </main>
  );
}

export function useNews() {
  return useQuery({
    queryKey: ["news"], queryFn: api.news,
    refetchInterval: (q) => (q.state.data?.status === "running" ? 4000 : false),
  });
}

function Digest() {
  const qc = useQueryClient();
  const q = useNews();
  const [topics, setTopics] = useState<string[] | null>(null);
  const [days, setDays] = useState(7);
  const [show, setShow] = useState("all");
  useEffect(() => { if (q.data && topics === null) { setTopics(q.data.topics); setDays(q.data.days); } }, [q.data, topics]);
  const refresh = useMutation({
    mutationFn: () => api.refreshNews({ days, topics: topics ?? undefined }),
    onSuccess: (d) => qc.setQueryData(["news"], d),
  });
  const hide = useMutation({
    mutationFn: (url: string) => api.hideNews(url),
    onMutate: (url) => qc.setQueryData<NewsDigest>(["news"], (d) => d && { ...d, items: d.items.filter((i) => i.url !== url) }),
  });
  if (q.isLoading) return <Thinking label="Loading…" />;
  if (q.isError) return <ErrorBox error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data!;
  const running = d.status === "running" || refresh.isPending;
  const label = Object.fromEntries(d.all_topics.map((t) => [t.id, t.label]));
  const sel = topics ?? d.topics;
  const toggle = (id: string) => setTopics(sel.includes(id) ? sel.filter((t) => t !== id) : [...sel, id]);
  const items = d.items.filter((i) => show === "all" || i.topic === show);
  const present = d.all_topics.filter((t) => d.items.some((i) => i.topic === t.id));

  return (
    <section aria-labelledby="dig-h" className="flex flex-col gap-4 min-w-0">
      <div className="card p-4 flex flex-col gap-3">
        <h2 id="dig-h" className="font-semibold">Digest topics</h2>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Topics">
          {d.all_topics.map((t) => (
            <button key={t.id} type="button" aria-pressed={sel.includes(t.id)} onClick={() => toggle(t.id)}
              className={`pill text-sm ${sel.includes(t.id) ? "bg-ink text-white border-ink" : "bg-white text-body border-line2 hover:bg-ground"}`}>
              {t.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label htmlFor="news-days" className="text-sm font-semibold">Last</label>
          <select id="news-days" className="input w-auto py-1.5" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {DAYS.map((n) => <option key={n} value={n}>{n} days</option>)}
          </select>
          <button type="button" className="btn-primary btn-sm" disabled={running || sel.length === 0} onClick={() => refresh.mutate()}>
            <Icon.refresh size={15} /> {running ? "Searching…" : d.fetched_at ? "Refresh" : "Get my digest"}
          </button>
          {d.fetched_at && !running && <span className="text-xs text-muted">Updated {ago(d.fetched_at)}</span>}
        </div>
        {running && <Thinking label="Searching the web and checking every link (2–4 minutes)…" />}
        {d.status === "failed" && !running && <p className="text-sm text-[#B42318]">The last refresh failed: {d.error}</p>}
        {refresh.isError && <ErrorBox error={refresh.error} />}
      </div>

      {d.headline && <p className="text-lg font-semibold text-ink">{d.headline}</p>}
      {present.length > 1 && (
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Show topic">
          {[{ id: "all", label: "All" }, ...present].map((t) => (
            <button key={t.id} type="button" aria-pressed={show === t.id} onClick={() => setShow(t.id)}
              className={`px-3 py-1.5 rounded-full text-sm font-semibold ${show === t.id ? "bg-accent-soft text-accent-dark" : "text-body hover:bg-ground"}`}>
              {t.label}
            </button>
          ))}
        </div>
      )}
      {d.items.length === 0 && !running && (
        <p className="card p-6 text-body">{d.fetched_at ? "Nothing left in this digest. Refresh for new stories." : "Pick your topics and get your first digest."}</p>
      )}
      <ul className="flex flex-col gap-3">
        {items.map((i) => <NewsCard key={i.url} i={i} topic={label[i.topic] ?? i.topic} onHide={() => hide.mutate(i.url)} />)}
      </ul>
    </section>
  );
}

function NewsCard({ i, topic, onHide }: { i: NewsItem; topic: string; onHide: () => void }) {
  return (
    <li className="card p-4 flex flex-col gap-1.5">
      <p className="text-xs text-muted flex flex-wrap gap-x-2">
        <span className="font-semibold text-accent-dark">{topic}</span>
        <span>{i.source}</span>
        {i.date && <span>{fmtDay(i.date)}</span>}
        {!i.verified && <span title="The site blocks automated checks">link not checked</span>}
      </p>
      <h3 className="font-semibold leading-snug">
        <a href={i.url} target="_blank" rel="noreferrer" className="hover:text-accent">{i.title}</a>
      </h3>
      <p className="text-sm text-body">{i.summary}</p>
      <p className="text-sm text-muted">{i.why_it_matters}</p>
      <div className="flex gap-2 pt-1">
        <button type="button" className="text-sm text-muted hover:text-ink inline-flex items-center gap-1" onClick={onHide}>
          <Icon.close size={14} /> Hide
        </button>
      </div>
    </li>
  );
}

function Live() {
  const q = useQuery({ queryKey: ["news-live"], queryFn: () => api.liveNews(20), staleTime: 5 * 60_000 });
  return (
    <aside aria-labelledby="live-h" className="card p-4 flex flex-col gap-3 lg:sticky lg:top-4">
      <div className="flex items-center justify-between gap-2">
        <h2 id="live-h" className="font-semibold">Live on Hacker News</h2>
        <button type="button" className="text-muted hover:text-ink" aria-label="Reload headlines" onClick={() => q.refetch()}><Icon.refresh size={16} /></button>
      </div>
      {q.isLoading && <Thinking label="Loading…" />}
      {q.data?.error && <p className="text-sm text-muted">{q.data.error}</p>}
      <ol className="flex flex-col divide-y divide-line">
        {q.data?.items.map((h) => (
          <li key={h.id} className="py-2.5 flex flex-col gap-0.5">
            <a href={h.url} target="_blank" rel="noreferrer" className="font-medium leading-snug hover:text-accent">{h.title}</a>
            <span className="text-xs text-muted">
              {h.site} · {h.points} points · <a href={h.discussion} target="_blank" rel="noreferrer" className="hover:underline">{h.comments} comments</a> · {ago(h.at)}
            </span>
          </li>
        ))}
      </ol>
    </aside>
  );
}
