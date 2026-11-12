import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
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

function Nav() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [menu, setMenu] = useState(false);
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile });
  const onSearch = (e: FormEvent) => {
    e.preventDefault();
    if (q.trim()) navigate(`/discover?q=${encodeURIComponent(q.trim())}`);
  };
  const link = ({ isActive }: { isActive: boolean }) =>
    `px-3.5 py-2.5 rounded-lg ${isActive ? "bg-accent-soft text-accent-dark font-semibold" : "text-body hover:bg-ground"}`;
  return (
    <header className="bg-white border-b border-line">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-4 sm:px-8 py-3.5">
        <Link to="/" className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-lg bg-accent text-white font-display font-bold flex items-center justify-center">S</span>
          <span className="font-display font-semibold text-lg">Study Companion</span>
        </Link>
        <button type="button" className="ml-auto md:hidden w-11 h-11 rounded-lg border border-line2 flex items-center justify-center"
          aria-expanded={menu} aria-controls="main-nav" aria-label="Menu" onClick={() => setMenu(!menu)}><Icon.menu /></button>
        <nav id="main-nav" aria-label="Main" className={`${menu ? "flex" : "hidden"} md:flex w-full md:w-auto flex-col md:flex-row gap-1`}
          onClick={() => setMenu(false)}>
          <NavLink to="/" end className={link}>Home</NavLink>
          <NavLink to="/paths" className={link}>My paths</NavLink>
          <NavLink to="/claude" className={link}>Claude learning</NavLink>
          <NavLink to="/voice" className={link}>Voice ASR/NLU</NavLink>
          <NavLink to="/career" className={link}>Career</NavLink>
          <NavLink to="/interview" className={link}>Interview prep</NavLink>
          <NavLink to="/links" className={link}>My links</NavLink>
          <NavLink to="/discover" className={link}>Discover</NavLink>
          <NavLink to="/setup" className={link}>New goal</NavLink>
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
          <Route path="/interview" element={<InterviewList />} />
          <Route path="/interview/new" element={<InterviewConfigure />} />
          <Route path="/interview/:id" element={<InterviewPage />} />
          <Route path="/interview/:id/edit" element={<InterviewConfigure />} />
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
