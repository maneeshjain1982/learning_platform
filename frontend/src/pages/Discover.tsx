import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type Resource } from "../api";
import { useAsk } from "../components/AskLLM";
import { ErrorBox, Icon, LinkCard, PaperRow, Thinking, VideoCard } from "../components/ui";

const TABS = ["All", "YouTube", "Papers", "Coursera", "Udemy", "Saved"] as const;
type Tab = (typeof TABS)[number];

export default function Discover() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const [input, setInput] = useState(q);
  const [tab, setTab] = useState<Tab>("All");
  const [level, setLevel] = useState("intermediate");
  const [videoSince, setVideoSince] = useState<number | null>(null);

  const papers = useQuery({ queryKey: ["search-papers", q], queryFn: () => api.searchPapers(q), enabled: q.length > 1, staleTime: Infinity });
  const videos = useQuery({
    queryKey: ["search-videos", q, level],
    queryFn: async () => { setVideoSince(Date.now()); try { return await api.searchVideos(q, level); } finally { setVideoSince(null); } },
    enabled: q.length > 1 && (tab === "All" || tab === "YouTube"), staleTime: Infinity, retry: false,
  });
  const links = useQuery({ queryKey: ["links", q], queryFn: () => api.searchLinks(q), enabled: q.length > 0 });
  const saved = useQuery({ queryKey: ["saved"], queryFn: api.saved, enabled: tab === "Saved" });

  const submit = (e: FormEvent) => { e.preventDefault(); if (input.trim()) setParams({ q: input.trim() }); };
  const showVideos = tab === "All" || tab === "YouTube";
  const showPapers = tab === "All" || tab === "Papers";
  const showLinks = tab === "All" || tab === "Coursera" || tab === "Udemy";

  return (
    <main className="max-w-[1280px] mx-auto w-full px-4 sm:px-8 pt-8 pb-28 flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="h-display text-3xl">Discover</h1>
        <p className="text-muted">One search across YouTube, research papers, Coursera and Udemy. Add anything you like to a lesson.</p>
      </div>

      <form role="search" onSubmit={submit} className="flex flex-wrap gap-2.5">
        <div className="flex-[1_1_420px] flex items-center gap-2.5 min-h-[52px] px-4 border border-[#C9CED8] rounded-xl bg-white focus-within:border-accent">
          <Icon.search className="text-muted" size={20} />
          <label htmlFor="dq" className="sr-only">Search</label>
          <input id="dq" type="search" value={input} onChange={(e) => setInput(e.target.value)} placeholder="e.g. function calling agents"
            className="flex-1 min-w-0 text-base outline-none bg-transparent" />
        </div>
        <label htmlFor="lvl" className="sr-only">Level</label>
        <select id="lvl" value={level} onChange={(e) => setLevel(e.target.value)} className="input w-auto min-h-[52px]">
          <option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option>
        </select>
        <button type="submit" className="btn-primary min-h-[52px] px-6">Search</button>
      </form>

      <div role="tablist" aria-label="Source" className="flex flex-wrap gap-1 border-b border-line">
        {TABS.map((t) => (
          <button key={t} type="button" role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
            className={`min-h-[44px] px-4 ${tab === t ? "text-accent-dark font-semibold shadow-[inset_0_-3px_0_#2453D6]" : "text-body font-medium hover:text-ink"}`}>{t}</button>
        ))}
      </div>

      {tab === "Saved" ? (
        <Results items={saved.data ?? []} loading={saved.isLoading} error={saved.error} empty="Nothing saved yet. Use the bookmark button on any video or paper." />
      ) : !q ? (
        <p className="text-muted">Search for a topic to see videos, papers and course links.</p>
      ) : (
        <div className="flex flex-col gap-8">
          {showVideos && (
            <section aria-labelledby="v-h" className="flex flex-col gap-3">
              <h2 id="v-h" className="h-display text-xl">Videos</h2>
              {videos.isFetching ? <Thinking label="The Video Search agent is searching YouTube and checking links…" since={videoSince ?? undefined} /> : null}
              {videos.isError && <ErrorBox error={videos.error} onRetry={() => videos.refetch()} />}
              {videos.data && <Results items={videos.data} empty="No verified videos found. Try different words." />}
            </section>
          )}
          {showPapers && (
            <section aria-labelledby="p-h" className="flex flex-col gap-3">
              <h2 id="p-h" className="h-display text-xl">Papers</h2>
              <Results items={papers.data ?? []} loading={papers.isLoading} error={papers.error} empty="No papers found." />
            </section>
          )}
          {showLinks && links.data && (
            <section aria-labelledby="c-h" className="flex flex-col gap-3">
              <h2 id="c-h" className="h-display text-xl">Full courses</h2>
              <p className="text-sm text-muted">Coursera and Udemy open in a new tab with this search.</p>
              <div className="grid gap-2.5 sm:grid-cols-2 max-w-[760px]">
                {links.data.filter((l) => l.source !== "youtube" && (tab === "All" || l.label === tab))
                  .map((l) => <LinkCard key={l.url} {...l} query={q} />)}
              </div>
            </section>
          )}
        </div>
      )}
    </main>
  );
}

function Results({ items, loading, error, empty }: { items: Resource[]; loading?: boolean; error?: unknown; empty: string }) {
  if (loading) return <Thinking label="Searching…" />;
  if (error) return <ErrorBox error={error} />;
  if (!items.length) return <p className="text-muted">{empty}</p>;
  const videos = items.filter((r) => r.kind === "video");
  const others = items.filter((r) => r.kind !== "video");
  return (
    <div className="flex flex-col gap-4">
      {videos.length > 0 && (
        <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))" }}>
          {videos.map((r) => <VideoCard key={r.id} r={r} footer={<AddToLesson r={r} />} />)}
        </div>
      )}
      {others.map((r) => <PaperRow key={r.id} r={r} footer={<AddToLesson r={r} />} />)}
    </div>
  );
}

function AddToLesson({ r }: { r: Resource }) {
  const qc = useQueryClient();
  const { ask } = useAsk();
  const home = useQuery({ queryKey: ["home", undefined], queryFn: () => api.home() });
  const target = home.data?.active?.continue;
  const m = useMutation({
    mutationFn: () => api.attach(target!.lesson_id, r.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["lesson", target!.lesson_id] }); qc.invalidateQueries({ queryKey: ["home"] }); },
  });
  return (
    <>
      {target && (
        <button type="button" className="btn-outline btn-sm" disabled={m.isPending || m.isSuccess} onClick={() => m.mutate()}
          title={`Add to your current lesson: ${target.title}`}>
          {m.isSuccess ? "Added ✓" : "Add to current lesson"}
        </button>
      )}
      <button type="button" className="btn-outline btn-sm" onClick={() => ask(`Tell me about "${r.title}"${r.author ? ` by ${r.author}` : ""}. What are the key ideas and is it worth my time?`)}>
        Ask LLM
      </button>
    </>
  );
}
