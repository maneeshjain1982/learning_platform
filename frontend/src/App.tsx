import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, Navigate, NavLink, Outlet, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { api } from "./api";
import { AskDrawer, AskFab, AskProvider } from "./components/AskLLM";
import { AuthGate, useMe, useSignOut } from "./components/Auth";
import { SideHeading, SideLink, TwoPane } from "./components/Layout";
import { Icon } from "./components/ui";
import Career from "./pages/Career";
import DomainPage, { DomainsIndex, NewDomainDialog } from "./pages/Domain";
import FaangPage from "./pages/Faang";
import Home, { BookmarksPage, SearchPage, domainIcon } from "./pages/Home";
import InterviewPage from "./pages/Interview";
import { InterviewConfigure, InterviewList } from "./pages/InterviewSetup";
import Jobs, { JobSearch } from "./pages/Jobs";
import News from "./pages/News";
import Settings from "./pages/Settings";

const CAREER = [
  { to: "/career/jobs", label: "Hot Jobs", hint: "Top open roles by country", icon: <Icon.star size={16} /> },
  { to: "/career/search", label: "Job search", hint: "Your search, or jobs for a domain", icon: <Icon.search size={16} /> },
  { to: "/career/prep", label: "Interview prep", hint: "Topics and questions from a JD, mock interview", icon: <Icon.brief size={16} /> },
  { to: "/career/faang", label: "FAANG questions", hint: "Publicly reported questions by company", icon: <Icon.chat size={16} /> },
  { to: "/career/certs", label: "Certifications", hint: "AI certifications worth earning", icon: <Icon.cap size={16} /> },
];

function useOutside(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) close(); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open, close]);
  return ref;
}

/** A top-menu button that opens a panel of links. On small screens the panel opens inline in the menu. */
function Menu({ id, label, active, open, setOpen, children }: {
  id: string; label: string; active: boolean; open: boolean; setOpen: (v: boolean) => void; children: ReactNode;
}) {
  const ref = useOutside(open, () => setOpen(false));
  return (
    <div ref={ref} className="relative">
      <button type="button" aria-expanded={open} aria-controls={`nav-${id}`} onClick={() => setOpen(!open)}
        className={`w-full md:w-auto px-3.5 py-2 rounded-lg inline-flex items-center justify-between gap-1.5 ${active ? "bg-accent-soft text-accent-dark font-semibold" : "text-body hover:bg-ground"}`}>
        {label}
        <Icon.chevron size={14} className={`transition-transform ${open ? "-rotate-90" : "rotate-90"}`} />
      </button>
      {open && (
        <div id={`nav-${id}`} onClick={() => setOpen(false)}
          className="md:absolute md:left-0 md:top-full md:mt-2 z-30 md:w-[320px] flex flex-col gap-0.5 p-1.5 md:bg-white md:border md:border-line md:rounded-xl md:shadow-lg ml-3 md:ml-0 border-l-2 border-line md:border-l">
          {children}
        </div>
      )}
    </div>
  );
}

const menuItem = ({ isActive }: { isActive: boolean }) =>
  `flex items-start gap-3 px-3 py-2.5 rounded-lg ${isActive ? "bg-accent-soft text-accent-dark" : "text-body hover:bg-ground"}`;

function Nav() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const me = useMe();
  const [q, setQ] = useState("");
  const [menu, setMenu] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  useEffect(() => { setOpen(null); setMenu(false); }, [pathname]);
  const domains = useQuery({ queryKey: ["domains"], queryFn: api.domains });
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile });
  const onSearch = (e: FormEvent) => {
    e.preventDefault();
    if (q.trim()) navigate(`/search?q=${encodeURIComponent(q.trim())}`);
  };
  const link = ({ isActive }: { isActive: boolean }) =>
    `px-3.5 py-2 rounded-lg ${isActive ? "bg-accent-soft text-accent-dark font-semibold" : "text-body hover:bg-ground"}`;
  const setter = (id: string) => (v: boolean) => setOpen(v ? id : null);

  return (
    <header className="bg-white/95 backdrop-blur border-b border-line sticky top-0 z-30">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 sm:px-6 py-2.5 md:h-[68px] md:py-0">
        <Link to="/" className="flex items-center gap-2.5 mr-2">
          <span className="w-8 h-8 rounded-lg bg-accent text-white font-display font-bold flex items-center justify-center">S</span>
          <span className="font-display font-semibold text-lg">Study Companion</span>
        </Link>
        <button type="button" className="ml-auto md:hidden w-11 h-11 rounded-lg border border-line2 flex items-center justify-center"
          aria-expanded={menu} aria-controls="main-nav" aria-label="Menu" onClick={() => setMenu(!menu)}><Icon.menu /></button>
        <nav id="main-nav" aria-label="Main" className={`${menu ? "flex" : "hidden"} md:flex w-full md:w-auto flex-col md:flex-row md:items-center gap-1 pb-2 md:pb-0`}>
          <NavLink to="/" end className={link}>Home</NavLink>
          <Menu id="domains" label="Domains" active={pathname.startsWith("/d/") || pathname === "/domains"} open={open === "domains"} setOpen={setter("domains")}>
            {domains.data?.map((d) => (
              <NavLink key={d.id} to={`/d/${d.slug}`} className={menuItem}>
                <span className="mt-0.5 text-accent">{domainIcon(d.slug, 16)}</span>
                <span className="flex flex-col"><span className="font-semibold">{d.name}</span>
                  <span className="text-xs text-muted line-clamp-1">{d.topics} topics · {d.description}</span></span>
              </NavLink>
            ))}
            {me.is_admin && (
              <button type="button" className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-accent font-semibold hover:bg-ground border-t border-line mt-1"
                onClick={() => setAdding(true)}><Icon.plus size={16} /> Add domain</button>
            )}
          </Menu>
          <NavLink to="/news" className={link}>Tech News</NavLink>
          {me.is_admin && (
            <Menu id="career" label="Career" active={pathname.startsWith("/career")} open={open === "career"} setOpen={setter("career")}>
              {CAREER.map((c) => (
                <NavLink key={c.to} to={c.to} className={menuItem}>
                  <span className="mt-0.5 text-accent">{c.icon}</span>
                  <span className="flex flex-col"><span className="font-semibold">{c.label}</span><span className="text-xs text-muted">{c.hint}</span></span>
                </NavLink>
              ))}
            </Menu>
          )}
        </nav>
        <form role="search" onSubmit={onSearch}
          className="hidden md:flex flex-1 min-w-[200px] max-w-[400px] ml-auto items-center gap-2 px-3 h-10 rounded-[10px] border border-line2 bg-ground focus-within:border-accent focus-within:bg-white">
          <Icon.search size={16} className="text-muted" />
          <label htmlFor="nav-q" className="sr-only">Search topics</label>
          <input id="nav-q" type="search" value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search topics…" className="flex-1 min-w-0 bg-transparent outline-none text-sm" />
        </form>
        <AccountMenu name={profile.data?.name ?? me.name} open={open === "account"} setOpen={setter("account")} />
      </div>
      {adding && <NewDomainDialog onClose={() => setAdding(false)} />}
    </header>
  );
}

/** The round avatar: who is signed in, Bookmarks, Settings and Sign out. */
function AccountMenu({ name, open, setOpen }: { name: string; open: boolean; setOpen: (v: boolean) => void }) {
  const me = useMe();
  const signOut = useSignOut();
  const ref = useOutside(open, () => setOpen(false));
  const item = "flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-body hover:bg-ground text-left";
  return (
    <div ref={ref} className="relative max-md:absolute max-md:right-[68px] max-md:top-2.5">
      <button type="button" aria-label={`Account: ${name}`} aria-expanded={open} aria-controls="account-menu"
        onClick={() => setOpen(!open)}
        className="w-11 h-11 rounded-full border border-line2 bg-white font-semibold flex items-center justify-center hover:bg-ground">
        {name.slice(0, 1).toUpperCase()}
      </button>
      {open && (
        <div id="account-menu" className="absolute right-0 top-full mt-1.5 z-30 w-[240px] bg-white border border-line rounded-xl shadow-lg p-1.5 flex flex-col">
          <div className="px-3 py-2.5 border-b border-line mb-1">
            <p className="font-semibold truncate">{name}</p>
            <p className="text-xs text-muted">Signed in as {me.username} · {me.is_admin ? "Admin" : "User"}</p>
          </div>
          <Link to="/bookmarks" onClick={() => setOpen(false)} className={item}><Icon.star size={16} /> Bookmarks</Link>
          <Link to="/settings" onClick={() => setOpen(false)} className={item}><Icon.edit size={16} /> Profile and settings</Link>
          <button type="button" onClick={() => signOut.mutate()} className={item}><Icon.close size={16} /> Sign out</button>
        </div>
      )}
    </div>
  );
}

/** Career pages (admin): the Career menu on the left, the page on the right. */
function CareerLayout() {
  const me = useMe();
  if (!me.is_admin) return <AdminNote />;
  const side = (
    <div className="pb-8">
      <SideHeading>Career</SideHeading>
      {CAREER.map((c) => (
        <SideLink key={c.to} to={c.to} icon={c.icon}>
          <span className="block">{c.label}</span>
          <span className="block text-xs text-muted font-normal">{c.hint}</span>
        </SideLink>
      ))}
    </div>
  );
  return <TwoPane sideLabel="Career menu" side={side}><Outlet /></TwoPane>;
}

function AdminNote() {
  return (
    <main className="max-w-[640px] mx-auto w-full px-4 sm:px-8 py-16 flex flex-col gap-3 items-start">
      <h1 className="h-display text-2xl">Not available for this account</h1>
      <p className="text-body">This area is for the admin account.</p>
      <Link className="btn-outline" to="/">Go to Home</Link>
    </main>
  );
}

/** Old links (/upskill/3, /interview/3/edit) open the same page under /career/prep. */
function OldPrepLink() {
  const { pathname, search } = useLocation();
  return <Navigate to={pathname.replace(/^\/(upskill|interview)/, "/career/prep") + search} replace />;
}

function OldVoiceLink() {
  return <Navigate to="/d/voice-ai" replace />;
}

function FaangDefault() {
  const { company } = useParams();
  return <FaangPage key={company ?? "Google"} />;
}

export default function App() {
  return <AuthGate><SignedInApp /></AuthGate>;
}

function SignedInApp() {
  return (
    <AskProvider>
      <div className="min-h-screen flex flex-col">
        <Nav />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/domains" element={<DomainsIndex />} />
          <Route path="/d/:slug" element={<DomainPage />} />
          <Route path="/d/:slug/t/:topicId" element={<DomainPage />} />
          <Route path="/news" element={<News />} />
          <Route path="/news/live" element={<News />} />
          <Route path="/news/t/:topic" element={<News />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/bookmarks" element={<BookmarksPage />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/career" element={<CareerLayout />}>
            <Route index element={<Navigate to="/career/jobs" replace />} />
            <Route path="jobs" element={<Jobs />} />
            <Route path="search" element={<JobSearch />} />
            <Route path="prep" element={<InterviewList />} />
            <Route path="prep/new" element={<InterviewConfigure />} />
            <Route path="prep/:id" element={<InterviewPage />} />
            <Route path="prep/:id/edit" element={<InterviewConfigure />} />
            <Route path="faang" element={<FaangDefault />} />
            <Route path="faang/:company" element={<FaangDefault />} />
            <Route path="certs" element={<Career />} />
          </Route>
          {/* Links from the old design */}
          <Route path="/jobs" element={<Navigate to="/career/jobs" replace />} />
          <Route path="/upskill/*" element={<OldPrepLink />} />
          <Route path="/interview/*" element={<OldPrepLink />} />
          <Route path="/voice/*" element={<OldVoiceLink />} />
          <Route path="/hindi-voice" element={<OldVoiceLink />} />
          <Route path="/claude" element={<Navigate to="/d/agentic-ai" replace />} />
          <Route path="/paths/*" element={<Navigate to="/domains" replace />} />
          <Route path="/lessons/*" element={<Navigate to="/domains" replace />} />
          <Route path="/setup" element={<Navigate to="/domains" replace />} />
          <Route path="/discover" element={<Navigate to="/search" replace />} />
          <Route path="/links" element={<Navigate to="/bookmarks" replace />} />
          <Route path="*" element={<main className="p-8"><h1 className="h-display text-2xl">Page not found</h1><Link className="text-accent" to="/">Go home</Link></main>} />
        </Routes>
      </div>
      <AskFab />
      <AskDrawer />
    </AskProvider>
  );
}

