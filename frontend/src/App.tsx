import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api } from "./api";
import { AskDrawer, AskFab, AskProvider } from "./components/AskLLM";
import { Icon } from "./components/ui";
import Career from "./pages/Career";
import ClaudeAcademy from "./pages/ClaudeAcademy";
import Discover from "./pages/Discover";
import Voice from "./pages/Voice";
import Home from "./pages/Home";
import LessonPage from "./pages/Lesson";
import Links from "./pages/Links";
import InterviewPage from "./pages/Interview";
import { InterviewConfigure, InterviewList } from "./pages/InterviewSetup";
import PathPage, { PathsList } from "./pages/Paths";
import Settings from "./pages/Settings";
import Setup from "./pages/Setup";

type NavItem = { to: string; label: string; hint: string };
type NavGroupDef = { id: string; label: string; items: NavItem[] };

const GROUPS: NavGroupDef[] = [
  { id: "learning", label: "Learning", items: [
    { to: "/paths", label: "My paths", hint: "Your learning paths and progress" },
    { to: "/claude", label: "Claude learning", hint: "Claude Academy courses and updates" },
    { to: "/voice", label: "Voice ASR/NLU", hint: "Adding Hindi or English to a voice assistant" },
    { to: "/upskill", label: "Upskill Prep", hint: "Role research, question bank and mock practice" },
    { to: "/setup", label: "New goal", hint: "Build a new path from a learning goal" },
  ] },
  { id: "library", label: "Library", items: [
    { to: "/discover", label: "Discover", hint: "Search videos, papers and courses" },
    { to: "/links", label: "My links", hint: "Courses and links you saved" },
  ] },
];

/** A top-menu group: a button that opens a list of links. On small screens the list opens inline in the menu. */
function NavGroup({ g, open, setOpen, closeAll }: {
  g: NavGroupDef; open: boolean; setOpen: (v: boolean) => void; closeAll: () => void;
}) {
  const { pathname } = useLocation();
  const active = g.items.some((i) => pathname === i.to || pathname.startsWith(`${i.to}/`));
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { setOpen(false); ref.current?.querySelector("button")?.focus(); }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open, setOpen]);
  const item = ({ isActive }: { isActive: boolean }) =>
    `flex flex-col px-3 py-2.5 rounded-lg ${isActive ? "bg-accent-soft text-accent-dark" : "text-body hover:bg-ground"}`;
  return (
    <div ref={ref} className="relative"
      onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null) && e.relatedTarget) setOpen(false); }}>
      <button type="button" aria-expanded={open} aria-controls={`nav-${g.id}`}
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        className={`w-full md:w-auto px-3.5 py-2.5 rounded-lg inline-flex items-center justify-between gap-1.5 ${active ? "bg-accent-soft text-accent-dark font-semibold" : "text-body hover:bg-ground"}`}>
        {g.label}
        <Icon.chevron size={15} className={`transition-transform ${open ? "-rotate-90" : "rotate-90"}`}/>
      </button>
      {open && (
        <ul id={`nav-${g.id}`} onClick={closeAll}
          className="md:absolute md:left-0 md:top-full md:mt-1.5 z-30 md:w-[300px] flex flex-col gap-0.5 p-1.5 md:bg-white md:border md:border-line md:rounded-xl md:shadow-lg ml-3 md:ml-0 border-l-2 border-line md:border-l">
          {g.items.map((i) => (
            <li key={i.to}>
              <NavLink to={i.to} className={item}>
                <span className="font-semibold">{i.label}</span>
                <span className="text-xs text-muted">{i.hint}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Nav() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [q, setQ] = useState("");
  const [menu, setMenu] = useState(false);
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  useEffect(() => { setOpenGroup(null); setMenu(false); }, [pathname]);
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile });
  const onSearch = (e: FormEvent) => {
    e.preventDefault();
    if (q.trim()) navigate(`/discover?q=${encodeURIComponent(q.trim())}`);
  };
  const closeAll = () => { setOpenGroup(null); setMenu(false); };
  const link = ({ isActive }: { isActive: boolean }) =>
    `px-3.5 py-2.5 rounded-lg ${isActive ? "bg-accent-soft text-accent-dark font-semibold" : "text-body hover:bg-ground"}`;
  return (
    <header className="bg-white border-b border-line relative z-20">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-4 sm:px-8 py-3.5">
        <Link to="/" className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-lg bg-accent text-white font-display font-bold flex items-center justify-center">S</span>
          <span className="font-display font-semibold text-lg">Study Companion</span>
        </Link>
        <button type="button" className="ml-auto md:hidden w-11 h-11 rounded-lg border border-line2 flex items-center justify-center"
          aria-expanded={menu} aria-controls="main-nav" aria-label="Menu" onClick={() => setMenu(!menu)}><Icon.menu /></button>
        <nav id="main-nav" aria-label="Main" className={`${menu ? "flex" : "hidden"} md:flex w-full md:w-auto flex-col md:flex-row md:items-center gap-1`}>
          <NavLink to="/" end className={link} onClick={closeAll}>Home</NavLink>
          <NavGroup g={GROUPS[0]} open={openGroup === GROUPS[0].id} closeAll={closeAll}
            setOpen={(v) => setOpenGroup(v ? GROUPS[0].id : null)} />
          <NavLink to="/career" className={link} onClick={closeAll}>Career</NavLink>
          <NavGroup g={GROUPS[1]} open={openGroup === GROUPS[1].id} closeAll={closeAll}
            setOpen={(v) => setOpenGroup(v ? GROUPS[1].id : null)} />
        </nav>
        <form role="search" onSubmit={onSearch}
          className="hidden md:flex flex-1 min-w-[220px] max-w-[440px] ml-auto items-center gap-2 px-3 h-11 rounded-[10px] border border-line2 bg-ground focus-within:border-accent">
          <Icon.search className="text-muted" />
          <label htmlFor="nav-q" className="sr-only">Search videos and papers</label>
          <input id="nav-q" type="search" value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search videos, papers, courses…" className="flex-1 min-w-0 bg-transparent outline-none" />
        </form>
        <Link to="/settings" aria-label="Profile and settings" title="Profile and settings"
          className="hidden md:flex w-11 h-11 rounded-full border border-line2 bg-white font-semibold items-center justify-center hover:bg-ground">
          {(profile.data?.name ?? "L").slice(0, 1).toUpperCase()}
        </Link>
      </div>
    </header>
  );
}

/** Old /interview/... bookmarks open the same page under /upskill/... */
function OldInterviewLink() {
  const { pathname, search } = useLocation();
  return <Navigate to={pathname.replace(/^\/interview/, "/upskill") + search} replace />;
}

export default function App() {
  const location = useLocation();
  const onLesson = location.pathname.startsWith("/lessons/");
  return (
    <AskProvider>
      <div className="min-h-screen flex flex-col">
        <Nav />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/setup" element={<Setup />} />
          <Route path="/paths" element={<PathsList />} />
          <Route path="/paths/:id" element={<PathPage />} />
          <Route path="/lessons/:id" element={<LessonPage />} />
          <Route path="/claude" element={<ClaudeAcademy />} />
          <Route path="/career" element={<Career />} />
          <Route path="/voice" element={<Navigate to="/voice/hi" replace />} />
          <Route path="/voice/:lang" element={<Voice />} />
          <Route path="/hindi-voice" element={<Navigate to="/voice/hi" replace />} />
          <Route path="/links" element={<Links />} />
          <Route path="/upskill" element={<InterviewList />} />
          <Route path="/upskill/new" element={<InterviewConfigure />} />
          <Route path="/upskill/:id" element={<InterviewPage />} />
          <Route path="/upskill/:id/edit" element={<InterviewConfigure />} />
          <Route path="/interview/*" element={<OldInterviewLink />} />
          <Route path="/discover" element={<Discover />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<main className="p-8"><h1 className="h-display text-2xl">Page not found</h1><Link className="text-accent" to="/">Go home</Link></main>} />
        </Routes>
      </div>
      {/* On lesson pages the panel is docked on wide screens, so the floating button only shows below xl. */}
      <AskFab className={onLesson ? "xl:hidden" : ""} />
      <AskDrawer />
    </AskProvider>
  );
}
