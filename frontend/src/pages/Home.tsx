import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, type TopicHit } from "../api";
import { useMe } from "../components/Auth";
import { Detail, SideHeading, SideLink, TwoPane } from "../components/Layout";
import { ErrorBox, Icon, Thinking, ago } from "../components/ui";
import { NewDomainButton } from "./Domain";
import { useNews } from "./News";

const DOMAIN_ICON: Record<string, (size: number) => ReactNode> = {
  "gen-ai": (s) => <Icon.sparkle size={s} />, llm: (s) => <Icon.cube size={s} />,
  "agentic-ai": (s) => <Icon.code size={s} />, "voice-ai": (s) => <Icon.mic size={s} />,
};
export const domainIcon = (slug: string, size = 18) => (DOMAIN_ICON[slug] ?? ((s: number) => <Icon.book size={s} />))(size);

/** Left panel shared by Home, Search and Bookmarks: the domains and your bookmarks. */
export function LibrarySide() {
  const me = useMe();
  const domains = useQuery({ queryKey: ["domains"], queryFn: api.domains });
  const marks = useQuery({ queryKey: ["bookmarks"], queryFn: api.bookmarks });
  return (
    <div className="pb-8">
      <SideHeading>Start</SideHeading>
      <SideLink to="/" end icon={<Icon.home size={16} />}>Home</SideLink>
      <SideLink to="/bookmarks" icon={<Icon.star size={16} />} meta={marks.data?.length || undefined}>Bookmarks</SideLink>
      <SideLink to="/news" icon={<Icon.news size={16} />}>Tech News</SideLink>
      <SideHeading action={me.is_admin ? <NewDomainButton className="text-xs font-semibold text-accent inline-flex items-center gap-1" /> : undefined}>Domains</SideHeading>
      {domains.data?.map((d) => (
        <SideLink key={d.id} to={`/d/${d.slug}`} icon={domainIcon(d.slug, 16)} meta={d.topics}>{d.name}</SideLink>
      ))}
      {(marks.data?.length ?? 0) > 0 && (<>
        <SideHeading>Recent bookmarks</SideHeading>
        {marks.data!.slice(0, 6).map((t) => (
          <SideLink key={t.id} to={`/d/${t.domain.slug}/t/${t.id}`}>{t.title}</SideLink>
        ))}
      </>)}
    </div>
  );
}

export default function Home() {
  const me = useMe();
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile });
  const domains = useQuery({ queryKey: ["domains"], queryFn: api.domains });
  const recent = useQuery({ queryKey: ["recent-topics"], queryFn: () => api.recentTopics(6) });
  const name = (profile.data?.name ?? me.name).split(" ")[0];
  const hour = new Date().getHours();
  const hello = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <TwoPane sideLabel="Browse" side={<LibrarySide />}>
      <Detail wide>
        <section className="rounded-2xl bg-ink text-white px-6 sm:px-8 py-8 flex flex-col gap-5 relative overflow-hidden">
          <div aria-hidden="true" className="absolute -right-16 -top-20 w-72 h-72 rounded-full bg-accent/50 blur-3xl" />
          <div className="relative">
            <p className="text-white/60 text-sm">{hello}, {name}</p>
            <h1 className="h-display text-[30px] leading-tight mt-1 text-white">What do you want to learn today?</h1>
          </div>
          <div className="relative"><SearchBox big /></div>
        </section>

        <section aria-labelledby="dom-h" className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-3">
            <h2 id="dom-h" className="h-display text-xl">Domains</h2>
            {me.is_admin && <NewDomainButton className="btn-outline btn-sm" />}
          </div>
          {domains.isLoading && <Thinking label="Loading…" />}
          {domains.isError && <ErrorBox error={domains.error} />}
          <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3">
            {domains.data?.map((d) => (
              <Link key={d.id} to={`/d/${d.slug}`} className="card p-5 flex flex-col gap-3 hover:border-accent hover:shadow-sm transition">
                <span className="w-10 h-10 rounded-xl bg-accent-soft text-accent flex items-center justify-center">{domainIcon(d.slug)}</span>
                <span className="font-semibold text-[17px]">{d.name}</span>
                <span className="text-sm text-muted line-clamp-2 flex-1">{d.description}</span>
                <span className="text-xs text-muted">{d.sections} sections · {d.topics} topics{d.status === "building" ? " · building…" : ""}</span>
              </Link>
            ))}
          </div>
        </section>

        <div className="grid lg:grid-cols-2 gap-5 items-start">
          <section aria-labelledby="rec-h" className="card p-5 flex flex-col gap-2">
            <h2 id="rec-h" className="font-semibold">Recently updated</h2>
            {recent.data?.length === 0 && <p className="text-sm text-muted">Topics appear here once their summaries are written.</p>}
            <TopicList items={recent.data ?? []} meta={(t) => t.updated_at ? ago(t.updated_at) : ""} />
          </section>
          <NewsPeek />
        </div>
      </Detail>
    </TwoPane>
  );
}

function NewsPeek() {
  const news = useNews();
  const live = useQuery({ queryKey: ["news-live"], queryFn: () => api.liveNews(20), staleTime: 5 * 60_000,
    enabled: !!news.data && news.data.items.length === 0 });
  const items = news.data?.items.slice(0, 5).map((i) => ({ title: i.title, url: i.url, meta: i.source })) ?? [];
  const fallback = live.data?.items.slice(0, 5).map((h) => ({ title: h.title, url: h.url, meta: `${h.site} · Hacker News` })) ?? [];
  const list = items.length ? items : fallback;
  return (
    <section aria-labelledby="news-h" className="card p-5 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h2 id="news-h" className="font-semibold">Tech News</h2>
        <Link to="/news" className="text-sm font-semibold text-accent">All news</Link>
      </div>
      <ul className="flex flex-col divide-y divide-line">
        {list.map((i) => (
          <li key={i.url} className="py-2.5">
            <a href={i.url} target="_blank" rel="noreferrer" className="font-medium leading-snug hover:text-accent">{i.title}</a>
            <span className="block text-xs text-muted mt-0.5">{i.meta}</span>
          </li>
        ))}
      </ul>
      {list.length === 0 && <p className="text-sm text-muted">No stories yet. Open Tech News to get your digest.</p>}
    </section>
  );
}

export function TopicList({ items, meta }: { items: TopicHit[]; meta?: (t: TopicHit) => string }) {
  return (
    <ul className="flex flex-col divide-y divide-line">
      {items.map((t) => (
        <li key={t.id}>
          <Link to={`/d/${t.domain.slug}/t/${t.id}`} className="group flex flex-col gap-0.5 py-2.5">
            <span className="font-medium group-hover:text-accent leading-snug">{t.title}</span>
            <span className="text-xs text-muted">{[t.domain.name, t.section, meta?.(t)].filter(Boolean).join(" · ")}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function SearchBox({ big = false, initial = "" }: { big?: boolean; initial?: string }) {
  const navigate = useNavigate();
  const [q, setQ] = useState(initial);
  const go = (e: FormEvent) => { e.preventDefault(); if (q.trim()) navigate(`/search?q=${encodeURIComponent(q.trim())}`); };
  return (
    <form role="search" onSubmit={go} className={`flex items-center gap-2 rounded-xl bg-white text-ink pl-4 pr-1.5 ${big ? "h-14 shadow-lg" : "h-12 border border-line2"}`}>
      <Icon.search className="text-muted shrink-0" />
      <label htmlFor={big ? "hero-q" : "page-q"} className="sr-only">Search topics</label>
      <input id={big ? "hero-q" : "page-q"} type="search" value={q} onChange={(e) => setQ(e.target.value)}
        placeholder="Search topics, e.g. RAG evaluation, MCP, Hindi ASR" className="flex-1 min-w-0 bg-transparent outline-none text-[15px]" />
      <button type="submit" className="btn-primary btn-sm">Search</button>
    </form>
  );
}

/** /search?q= : topics across all domains. */
export function SearchPage() {
  const [params] = useSearchParams();
  const q = params.get("q") ?? "";
  const res = useQuery({ queryKey: ["topic-search", q], queryFn: () => api.searchTopics(q), enabled: !!q });
  return (
    <TwoPane sideLabel="Browse" side={<LibrarySide />}>
      <Detail>
        <h1 className="h-display text-3xl">Search</h1>
        <SearchBox key={q} initial={q} />
        {res.isLoading && q && <Thinking label="Searching…" />}
        {res.isError && <ErrorBox error={res.error} />}
        {res.data && (
          <p className="text-sm text-muted">{res.data.length ? `${res.data.length} topics for "${q}"` : `No topics match "${q}". Try fewer or different words.`}</p>
        )}
        <div className="flex flex-col gap-2.5">
          {res.data?.map((t) => <TopicCard key={t.id} t={t} />)}
        </div>
      </Detail>
    </TwoPane>
  );
}

function TopicCard({ t }: { t: TopicHit }) {
  return (
    <Link to={`/d/${t.domain.slug}/t/${t.id}`} className="card p-4 flex flex-col gap-1 hover:border-accent">
      <span className="text-xs text-muted">{[t.domain.name, t.section].filter(Boolean).join(" · ")}</span>
      <span className="font-semibold text-[16px]">{t.title}</span>
      {t.overview && <span className="text-sm text-body line-clamp-2">{t.overview}</span>}
      <span className="text-xs text-muted">{t.sources} links</span>
    </Link>
  );
}

export function BookmarksPage() {
  const marks = useQuery({ queryKey: ["bookmarks"], queryFn: api.bookmarks });
  return (
    <TwoPane sideLabel="Browse" side={<LibrarySide />}>
      <Detail>
        <h1 className="h-display text-3xl">Bookmarks</h1>
        {marks.isLoading && <Thinking label="Loading…" />}
        {marks.data?.length === 0 && <p className="card p-6 text-body">Use <span className="font-semibold">Bookmark</span> on any topic to keep it here.</p>}
        <div className="flex flex-col gap-2.5">
          {marks.data?.map((t) => <TopicCard key={t.id} t={t} />)}
        </div>
      </Detail>
    </TwoPane>
  );
}
