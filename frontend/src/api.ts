// Typed client for the FastAPI backend (/api, proxied by Vite in dev).

export type Kind = "video" | "paper" | "course" | "article";

export interface Resource {
  id: number;
  kind: Kind;
  source: string;
  title: string;
  url: string;
  author: string;
  year: number | null;
  duration_min: number | null;
  summary: string;
  thumbnail: string | null;
  external_id: string;
  citations: number | null;
  pdf: string | null;
  why: string;
  saved: boolean;
  added_by: string | null;
  has_summary?: boolean;
  lesson_title?: string;
  lesson_id?: number;
}

export interface SearchLink { source: string; label: string; url: string; query?: string }

export interface PathSummary {
  id: number; title: string; summary: string; level: string; status: string;
  hours_per_week: number; weeks: number; is_seed: boolean; modules: number; lessons: number;
  done: number; pct: number; current_lesson_id: number | null; last_activity: string | null;
  show_on_home: boolean; kind?: "learning" | "interview";
}

// ---------------------------------------------------------------- interview companion
export type QType = "concept" | "design" | "scenario" | "hands_on" | "behavioral";
export type Difficulty = "medium" | "hard" | "expert";
export type QStatus = "new" | "needs_work" | "confident";
export type Bar = "top_ai" | "big_tech" | "standard";
export type Seniority = "senior" | "staff" | "principal" | "lead";

export interface InterviewConfig {
  role_title: string; company: string; jd_text: string; seniority: Seniority; interview_date: string | null;
  hours_per_week: number; background: string; focus_notes: string; question_types: QType[];
  questions_per_area: number; question_bar: Bar; web_research: boolean;
}
export interface InterviewSummary extends InterviewConfig {
  id: number; status: string; path_id: number | null; readiness: number; days_left: number | null;
  questions: number; skills: number; last_run: { id: number; status: string; kind: string } | null;
}
export interface Skill {
  id: number; area: string; name: string; importance: "must" | "important" | "nice"; evidence: string;
  in_jd: boolean; how_tested: string; self_rating: number | null; questions: number;
}
export interface Reference { title: string; url: string; kind: "paper" | "web"; verified: boolean; year?: number | null; authors?: string }
export interface IQuestion {
  id: number; area: string; skill_id: number | null; skill_name: string | null; qtype: QType; difficulty: Difficulty;
  question: string; status: QStatus; source: "agent" | "user"; attempts: number; last_score: number | null;
  answer_md?: string; key_points?: string[]; follow_ups?: string[]; red_flags?: string[]; references?: Reference[];
}
export interface Attempt {
  id: number; question_id: number; answer: string; score: number; verdict: string; strengths: string[];
  missing: string[]; better_answer_md: string; follow_up: string; created_at: string;
  question_text?: string; area?: string;
}
export interface InterviewStats {
  readiness: number; parts: { skills: number; practice: number; plan: number }; days_left: number | null;
  questions: number; question_status: Record<QStatus, number>; attempts: number;
  area_scores: Record<string, number | null>; rated_skills: number; skills: number; weak_skills: string[];
  next_lesson: { id: number; title: string } | null;
}
export interface InterviewDetail extends Omit<InterviewSummary, "skills" | "last_run" | "readiness" | "days_left" | "questions"> {
  skills: Skill[];
  jd_analysis: { role_summary: string; responsibilities: string[]; required_skills: string[]; nice_to_have: string[];
    seniority_signals: string[]; likely_rounds: string[] } | null;
  research: { role_summary: string; responsibilities: string[]; common_skills: { name: string; note: string }[];
    interview_format: string[]; trends: string[]; sources: { title: string; url: string; verified: boolean }[] } | null;
  coach_note: string | null; areas: string[];
  stats: InterviewStats; path: PathSummary | null; last_run: Run | null;
}

export type LinkKind = "course" | "link" | "video" | "paper" | "doc";
export interface MyLink {
  id: number; kind: LinkKind; title: string; url: string; provider: string; note: string;
  path_id: number | null; path_title: string | null; show_on_home: boolean; status: "todo" | "doing" | "done";
}
export interface LinkInput {
  url: string; title: string; kind?: LinkKind; note: string; path_id: number | null; show_on_home: boolean;
  status?: MyLink["status"];
}
export interface PathInput {
  title: string; summary: string; level: string; hours_per_week: number; weeks: number;
  show_on_home?: boolean; modules?: string[];
}
export type CourseStatus = "todo" | "doing" | "done";
export interface AcademyCourse extends Overlaid {
  slug: string; title: string; group: string; order: number | null; hours: number | null; lessons: number;
  quizzes: number; badge: boolean; level: string; summary: string; why: string; prereqs: string; url: string;
  outline: { title: string; lessons: string[] }[]; status: CourseStatus;
  path_progress: { done: number; total: number; module_id: number } | null;
  qa: { total: number; known: number; review: number };
}
export type QAStatus = "new" | "review" | "known";
export interface JobState { status: "idle" | "running" | "ready" | "failed"; error: string | null; started_at: string | null; fetched_at: string | null }
export interface QAItem {
  id: number; lesson_idx: number; lesson_title: string; question: string; answer_md: string; key_points: string[];
  references: { title: string; url: string; verified: boolean }[]; status: QAStatus;
}
export interface CourseQA { slug: string; title: string; lessons: string[]; items: QAItem[]; job: JobState }

export interface Cert extends Overlaid {
  name: string; issuer: string; tier: string; url: string; code: string; kind: string; price: string; duration: string;
  format: string; validity: string; access: string; focus: string; fit: string; notes: string; top_pick: boolean;
}
export interface CertFind {
  name: string; issuer: string; code: string; tier: string; change: "new" | "updated"; what_changed: string;
  price: string; format: string; focus: string; fit: string; url: string; verified: boolean;
}
export interface Certifications {
  checked_on: string; tiers: { id: string; title: string; summary: string }[]; certs: Cert[]; removed: number;
  refresh: JobState & { summary: string; items: CertFind[]; dropped: number };
}
export interface JobPosting {
  title: string; company: string; location: string; work_mode: string; seniority: string; posted: string; salary: string;
  url: string; summary: string; responsibilities: string[]; must_have: string[]; nice_to_have: string[]; skill_tags?: string[]; why_hot: string;
  verified: boolean; match?: number; fits?: string[]; gaps?: string[];
}
export interface JobsParams { roles: string; country: string; location: string; count: number }
export interface Jobs extends JobState {
  market_summary: string; trends: string[]; jobs: JobPosting[]; top_skills: { skill: string; count: number }[];
  dropped: number; params: JobsParams;
}
export interface Academy {
  base_url: string; checked_on: string; groups: { id: string; title: string; summary: string }[];
  courses: AcademyCourse[]; track: { hours: number; courses: number; lessons: number }; path_id: number | null; removed: number;
}

export interface AIUpdate {
  title: string; date: string; category: string; summary: string; why_it_matters: string; url: string;
  new_course: boolean; verified: boolean; is_new: boolean;
}
export interface AIUpdates {
  status: "idle" | "running" | "ready" | "failed"; error: string | null; headline: string; items: AIUpdate[];
  dropped: number; days: number; started_at: string | null; fetched_at: string | null; categories: string[];
}

// Voice (ASR + NLU), per language
export interface HVSkill { name: string; need: number; why: string; level: number }
/** Fields added to built-in catalog items by the edit layer. */
export interface Overlaid { _key?: string; _edited?: boolean }
export interface HVCourse extends Overlaid { id: string; title: string; provider: string; url: string; phase: string; kind: string; level: string; cost: string; covers: string; top_pick: boolean; status: CourseStatus }
export interface HVModule {
  slug: string; side: string; title: string; summary: string; url: string; refs: string[]; lessons: number;
  outline: { title: string; lessons: string[] }[]; qa: { total: number; known: number; review: number };
  path_progress: { done: number; total: number } | null;
}
export interface HVModel extends Overlaid { name: string; org: string; kind: string; url: string; paper: string; licence: string; size: string; on_device: string; result: string; notes: string; top_pick: boolean }
export interface HVDataset extends Overlaid { name: string; kind: string; url: string; paper: string; licence: string; size: string; what: string; use: string }
export interface HVPaper extends Overlaid { id: string; title: string; year: number; topic: string; url: string; why: string; top_pick: boolean }
export interface HVPhase { id: string; title: string; goal: string; steps: string[]; outputs: string[]; owners: string; pitfalls: string[] }
export interface HVTesting { id: string; title: string; metrics: [string, string, string][]; slices: string[] }
export interface HVVariability { dimension: string; values: string[]; why: string; how: string }
export interface HVSourcing { method: string; how: string; pros: string; cons: string }
export interface HVGeneration { name: string; for: string; how: string; caution: string; tool: string }
type IdTitle = { id: string; title: string };
export interface VoiceLang { code: string; name: string; title: string }
export interface UtterStyleInfo { id: string; label: string; help: string }
export interface VoiceData {
  code: string; name: string; title: string; intro: string; qa_sources: string; removed: Record<"models" | "datasets" | "papers" | "courses", number>;
  utter_styles: UtterStyleInfo[]; utter_default: UtterParams;
  checked_on: string; competencies: { id: string; title: string; skills: HVSkill[] }[];
  phases: (IdTitle & { summary: string })[]; courses: HVCourse[]; sides: IdTitle[]; modules: HVModule[];
  model_kinds: IdTitle[]; models: HVModel[]; dataset_kinds: IdTitle[]; datasets: HVDataset[];
  paper_topics: IdTitle[]; papers: HVPaper[]; playbook: HVPhase[]; steps_done: string[];
  testing: HVTesting[]; test_sizing: string[]; variability: HVVariability[]; sourcing: HVSourcing[];
  generation: HVGeneration[]; platform_notes: string[]; path_id: number | null;
}
export interface HVFind { kind: string; title: string; org: string; date: string; summary: string; why_it_matters: string; result: string; licence: string; url: string; verified: boolean; is_new?: boolean }
export interface HVResearch extends JobState { summary: string; items: HVFind[]; dropped: number; months: number }
export type UtterStyle = string;
export interface UtterParams { intent: string; description: string; slots: { name: string; examples: string }[]; count: number; styles: UtterStyle[] }
export interface Utterance { text: string; style: UtterStyle; tone: string; slots: { name: string; value: string }[]; annotated: string }
export interface Utterances extends JobState { items: Utterance[]; dropped_slots: number; params: UtterParams | null }

export type Direction = "up" | "down";

export interface Step { agent: string; status: string; summary: string; chips: string[] }
export interface Run {
  id: number; kind: string; status: string; error: string | null; path_id: number | null;
  started_at: string; finished_at: string | null; steps: Step[];
}

export interface HomeModule {
  id: number; idx: number; title: string; state: "done" | "now" | "next"; lessons: number; done: number;
  minutes: number; resources_status: string;
}

export interface HomeCard { id: string; label: string; on: boolean }
export interface Home {
  user: { name: string };
  layout: HomeCard[];
  paths: PathSummary[];
  hidden_paths: number;
  my_links: MyLink[];
  active: (PathSummary & {
    modules_detail: HomeModule[];
    continue: {
      lesson_id: number; title: string; module_idx: number; module_title: string; lesson_idx: number;
      est_minutes: number; started: boolean; module_done: number; module_lessons: number;
    } | null;
    focus_note: string | null;
    videos: Resource[]; papers: Resource[]; course_links: SearchLink[];
    current_module: { id: number; title: string; idx: number; resources_status: string } | null;
    week: { minutes: number; goal_minutes: number; lessons_done: number; questions: number };
    last_run: Run | null;
  }) | null;
}

export interface PathDetail extends PathSummary {
  module_list: {
    id: number; idx: number; title: string; summary: string; objectives: string[]; keywords: string[];
    resources_status: string;
    lessons: { id: number; idx: number; title: string; est_minutes: number; objectives: string[]; status: string; videos: number; papers: number }[];
  }[];
}

export interface Lesson {
  id: number; idx: number; title: string; objectives: string[]; keywords: string[]; est_minutes: number;
  content_md: string | null; notes_status: string; user_notes: string; status: string;
  module: { id: number; idx: number; title: string; lessons: number; resources_status: string };
  path: { id: number; title: string; level: string };
  prev: { id: number; title: string } | null;
  next: { id: number; title: string } | null;
  resources: Resource[];
  links: SearchLink[];
}

export interface ChatMsg {
  id: number; role: "user" | "assistant" | "error"; content: string;
  meta: { model?: string; provider?: string; duration_ms?: number; context?: string[] };
  created_at: string;
}

export interface Providers {
  active: { provider: string; model: string; fast_model: string };
  providers: { name: string; label: string; available: boolean; error: string | null; models: string[] }[];
}

export interface Me { id: number; username: string; name: string; role: "admin" | "user"; is_admin: boolean; default_password: boolean }

// ---------------------------------------------------------------- paper summaries & tech news
export interface PaperRef { resource_id?: number; url?: string; title?: string }
export interface PaperSummaryT {
  tldr: string; problem: string; method: string; results: string[]; limitations: string[]; why_it_matters: string;
  read_full_text: boolean; written_at?: string; edited?: boolean;
}
export interface PaperSummaryOut { resource_id: number; title: string; url: string; summary: PaperSummaryT | null; job: JobState }
export interface NewsItem { topic: string; title: string; source: string; date: string; summary: string; why_it_matters: string; url: string; verified: boolean }
export interface NewsDigest extends JobState {
  headline: string; items: NewsItem[]; dropped: number; days: number; topics: string[]; all_topics: { id: string; label: string }[];
}
export interface LiveItem { id: string; title: string; url: string; discussion: string; site: string; points: number; comments: number; at: string }


// ---------------------------------------------------------------- domains (knowledge base)
export type SourceKind = "video" | "course" | "paper" | "article" | "docs" | "repo" | "model" | "dataset" | "book";
export type Access = "free" | "login" | "paid" | "limited";
export type TopicStatus = "draft" | "writing" | "ready" | "failed";
export interface DomainBrief { id: number; slug: string; name: string; description: string; status: "building" | "ready" | "failed"; error: string | null; sections: number; topics: number; trusted_blogs: TrustedBlog[] }
export interface TrustedBlog { name: string; url: string }
export interface TopicBrief { id: number; title: string; blurb: string; status: TopicStatus; sources: number }
export interface DomainDetail extends DomainBrief { section_list: { id: number; title: string; topics: TopicBrief[] }[] }
export interface SourceAISummary {
  type: "paper" | "source"; tldr: string; key_points?: string[]; best_for?: string; time_needed?: string; access_note?: string;
  read_source?: boolean; problem?: string; method?: string; results?: string[]; limitations?: string[]; why_it_matters?: string; read_full_text?: boolean;
}
export interface TopicSource {
  id: number; title: string; url: string; kind: SourceKind; site: string; access: Access; summary: string; author: string;
  year: number | null; duration: string; facts: Record<string, string>; ai_summary: SourceAISummary | null;
  summary_status: "none" | "writing" | "ready" | "failed";
  blog: boolean; read_minutes: number | null; published: string; post_level: "beginner" | "intermediate" | "advanced" | null;
}
export interface TopicDetail extends TopicBrief {
  overview: string; key_points: string[]; why: string; details_md: string; error: string | null; updated_at: string | null;
  section: { id: number; title: string }; domain: { id: number; slug: string; name: string };
  source_list: TopicSource[]; bookmarked: boolean;
  blog_status: "none" | "finding" | "done" | "failed"; blog_error: string | null;
}
export interface TopicHit extends TopicBrief { overview: string; section?: string; domain: { slug: string; name: string }; updated_at?: string }
export type WorkMode = "any" | "remote" | "hybrid" | "onsite";
export type CompanyType = "any" | "big_tech" | "startup" | "enterprise";
export interface SearchParams {
  use_profile: boolean; query: string; domain: string; country: string; location: string; count: number;
  years: number | null; level: string; work_mode: WorkMode; company_type: CompanyType; posted_days: 7 | 14 | 30;
  min_salary: string; visa: boolean; extra: string;
}
export interface JobSearch extends Omit<Jobs, "params"> { params: SearchParams; matched: boolean }
export interface CareerProfile {
  headline: string; years: number; level: string; domains: string[]; skills: string[]; roles: string[]; summary: string;
  highlights: string[]; cv_name?: string; cv_text?: string; updated_at?: string;
}
export interface ReportedQ { question: string; round: string; role: string; difficulty: string; answer_outline: string[]; source_name: string; url: string; year: number | null; verified: boolean }
export interface Faang extends JobState { company: string; process: string; questions: ReportedQ[]; dropped: number; params: { role?: string; domain?: string; count?: number } }

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function req<T>(method: string, url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch { /* not JSON */ }
    // Session expired or signed out in another tab: the app shows the sign-in page.
    if (res.status === 401 && !url.startsWith("/api/auth/")) window.dispatchEvent(new Event("auth:expired"));
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

const get = <T,>(u: string) => req<T>("GET", u);
const post = <T,>(u: string, b?: unknown) => req<T>("POST", u, b ?? {});
const patch = <T,>(u: string, b: unknown) => req<T>("PATCH", u, b);
const del = (u: string) => req<{ ok: boolean }>("DELETE", u);
type Ok = { ok: boolean };

export const api = {
  domains: () => get<DomainBrief[]>("/api/domains"),
  domain: (key: string) => get<DomainDetail>(`/api/domains/${key}`),
  createDomain: (b: { name: string; description: string; build: boolean; max_topics?: number }) => post<DomainBrief>("/api/domains", b),
  updateDomain: (id: number, b: { name?: string; description?: string; trusted_blogs?: TrustedBlog[] }) => patch<DomainBrief>(`/api/domains/${id}`, b),
  deleteDomain: (id: number) => del(`/api/domains/${id}`),
  reorderDomains: (ids: number[]) => req<DomainBrief[]>("PUT", "/api/domains-order", ids),
  buildDomain: (id: number) => post<DomainBrief>(`/api/domains/${id}/build`),
  fillDomain: (id: number) => post<{ started: number }>(`/api/domains/${id}/fill`),
  domainBlogs: (id: number) => post<{ started: number }>(`/api/domains/${id}/blogs`),
  topicBlogs: (id: number) => post<TopicDetail>(`/api/topics/${id}/blogs`),
  addSection: (domainId: number, title: string) => post<{ id: number }>(`/api/domains/${domainId}/sections`, { title }),
  renameSection: (id: number, title: string) => patch<{ id: number }>(`/api/sections/${id}`, { title }),
  deleteSection: (id: number) => del(`/api/sections/${id}`),
  addTopic: (sectionId: number, b: { title: string; blurb?: string; auto: boolean }) => post<TopicDetail>(`/api/sections/${sectionId}/topics`, b),
  topic: (id: number) => get<TopicDetail>(`/api/topics/${id}`),
  updateTopic: (id: number, b: Partial<Pick<TopicDetail, "title" | "blurb" | "overview" | "key_points" | "why" | "details_md">>) => patch<TopicDetail>(`/api/topics/${id}`, b),
  deleteTopic: (id: number) => del(`/api/topics/${id}`),
  rewriteTopic: (id: number, find_sources: boolean) => post<TopicDetail>(`/api/topics/${id}/rewrite`, { find_sources }),
  bookmarkTopic: (id: number, on: boolean) => req<{ bookmarked: boolean }>("PUT", `/api/topics/${id}/bookmark`, { on }),
  bookmarks: () => get<TopicHit[]>("/api/topics/bookmarks"),
  recentTopics: (limit = 8) => get<TopicHit[]>(`/api/topics/recent?limit=${limit}`),
  searchTopics: (q: string) => get<TopicHit[]>(`/api/topics/search?q=${encodeURIComponent(q)}`),
  matchTopics: (terms: string[]) => post<Record<string, TopicHit[]>>("/api/topics/match", { terms }),
  addSource: (topicId: number, b: { url: string; title?: string; summary?: string; access?: Access }) => post<TopicSource>(`/api/topics/${topicId}/sources`, b),
  updateSource: (id: number, b: Partial<Pick<TopicSource, "title" | "url" | "summary" | "access" | "kind">>) => patch<TopicSource>(`/api/sources/${id}`, b),
  deleteSource: (id: number) => del(`/api/sources/${id}`),
  summarizeSource: (id: number) => post<TopicSource>(`/api/sources/${id}/summary`),
  deleteSourceSummary: (id: number) => req<TopicSource>("DELETE", `/api/sources/${id}/summary`),
  jobSearch: () => get<JobSearch>("/api/career/search"),
  runJobSearch: (b: Partial<SearchParams>) => post<JobSearch>("/api/career/search", b),
  careerProfile: () => get<{ profile: CareerProfile | null }>("/api/career/profile"),
  uploadCV: (b: { filename?: string; content_b64?: string; text?: string }) =>
    post<{ profile: CareerProfile }>("/api/career/profile/cv", b),
  editProfile: (b: Partial<CareerProfile>) => req<{ profile: CareerProfile }>("PUT", "/api/career/profile", b),
  deleteProfile: () => req<{ profile: null }>("DELETE", "/api/career/profile"),
  faangList: () => get<{ companies: string[]; loaded: Record<string, string | null> }>("/api/career/faang"),
  faang: (company: string) => get<Faang>(`/api/career/faang?company=${encodeURIComponent(company)}`),
  refreshFaang: (b: { company: string; role: string; domain: string; count: number }) => post<Faang>("/api/career/faang/refresh", b),
  me: () => get<Me>("/api/auth/me"),
  editItem: (scope: string, key: string, fields: Record<string, string>) => post<Ok>("/api/content/edit", { scope, key, fields }),
  deleteItem: (scope: string, key: string) => post<Ok & { for_everyone: boolean }>("/api/content/delete", { scope, key }),
  resetItems: (scope: string) => post<Ok>("/api/content/reset", { scope }),
  removeJobItem: (job: string, url: string) => post<Ok>("/api/content/job-item/remove", { job, url }),
  editLessonNotes: (id: number, content_md: string) => req<Lesson>("PUT", `/api/lessons/${id}/content`, { content_md }),
  deleteLessonNotes: (id: number) => req<Lesson>("DELETE", `/api/lessons/${id}/content`),
  paperSummary: (ref: PaperRef) => post<PaperSummaryOut>("/api/papers/summary/lookup", ref),
  summarizePaper: (ref: PaperRef & { context?: string }) => post<PaperSummaryOut>("/api/papers/summary", ref),
  editPaperSummary: (resource_id: number, s: PaperSummaryT) => req<PaperSummaryOut>("PUT", "/api/papers/summary", { ...s, resource_id }),
  deletePaperSummary: (resource_id: number) => del(`/api/papers/summary/${resource_id}`),
  news: () => get<NewsDigest>("/api/news"),
  refreshNews: (b: { days?: number; topics?: string[] }) => post<NewsDigest>("/api/news/refresh", b),
  hideNews: (url: string, hidden = true) => post<Ok>("/api/news/hide", { url, hidden }),
  liveNews: (limit = 20) => get<{ items: LiveItem[]; error: string | null }>(`/api/news/live?limit=${limit}`),
  login: (username: string, password: string) => post<Me>("/api/auth/login", { username, password }),
  logout: () => post<Ok>("/api/auth/logout"),
  changePassword: (current: string, next: string) => post<Me>("/api/auth/password", { current, new: next }),
  homeLayout: (cards: { id: string; on: boolean }[]) => req<HomeCard[]>("PUT", "/api/home/layout", cards),
  home: (pathId?: number) => get<Home>(`/api/home${pathId ? `?path_id=${pathId}` : ""}`),
  focus: (lessonId: number) => post<{ text: string }>(`/api/home/focus/${lessonId}`),
  paths: () => get<PathSummary[]>("/api/paths"),
  path: (id: number) => get<PathDetail>(`/api/paths/${id}`),
  deletePath: (id: number) => del(`/api/paths/${id}`),
  findResources: (id: number, moduleIds?: number[]) =>
    post<{ run_id: number }>(`/api/paths/${id}/find-resources`, moduleIds ? { module_ids: moduleIds } : {}),
  createRequirement: (body: {
    raw_text: string; goal: string; level: string; hours_per_week: number; weeks: number;
    formats: string[]; sources: string[];
  }) => post<{ requirement_id: number; run_id: number }>("/api/requirements", body),
  run: (id: number) => get<Run>(`/api/agent-runs/${id}`),
  activeRuns: () => get<Run[]>("/api/agent-runs?active=true"),
  lesson: (id: number) => get<Lesson>(`/api/lessons/${id}`),
  writeNotes: (id: number, force = false) => post<{ notes_status: string }>(`/api/lessons/${id}/notes${force ? "?force=true" : ""}`),
  saveUserNotes: (id: number, text: string) => req<{ ok: boolean }>("PUT", `/api/lessons/${id}/user-notes`, { text }),
  progress: (id: number, status: "todo" | "doing" | "done", minutes = 0) =>
    post<{ status: string }>(`/api/lessons/${id}/progress`, { status, minutes }),
  attach: (lessonId: number, resourceId: number) =>
    post<{ ok: boolean }>(`/api/lessons/${lessonId}/resources`, { resource_id: resourceId }),
  detach: (lessonId: number, resourceId: number) =>
    req<{ ok: boolean }>("DELETE", `/api/lessons/${lessonId}/resources/${resourceId}`),
  searchPapers: (q: string) => get<Resource[]>(`/api/search/papers?q=${encodeURIComponent(q)}`),
  searchVideos: (q: string, level: string) => post<Resource[]>("/api/search/videos", { q, level }),
  searchLinks: (q: string) => get<SearchLink[]>(`/api/search/links?q=${encodeURIComponent(q)}`),
  saved: () => get<Resource[]>("/api/saved"),
  save: (id: number) => post<{ saved: boolean }>(`/api/resources/${id}/save`),
  unsave: (id: number) => req<{ saved: boolean }>("DELETE", `/api/resources/${id}/save`),
  chat: (body: { message: string; session_id?: number | null; lesson_id?: number | null;
    context?: { lesson: boolean; level: boolean; path: boolean } }) =>
    post<{ session_id: number; user: ChatMsg; reply: ChatMsg }>("/api/chat", body),
  chatSession: (id: number) => get<{ id: number; messages: ChatMsg[]; lesson_id: number | null }>(`/api/chat/${id}`),
  saveToNotes: (msgId: number) => post<{ ok: boolean; user_notes: string }>(`/api/chat/messages/${msgId}/save-to-notes`),
  profile: () => get<{ name: string; email: string | null }>("/api/profile"),
  saveProfile: (b: { name: string; email: string | null }) => req<{ name: string }>("PUT", "/api/profile", b),
  providers: () => get<Providers>("/api/providers"),

  // Editing: your own courses and links, and changes to any path, module or lesson.
  createPath: (b: PathInput) => post<PathSummary>("/api/paths", b),
  updatePath: (id: number, b: Partial<PathInput>) => patch<PathSummary>(`/api/paths/${id}`, b),
  movePath: (id: number, direction: Direction) => post<Ok>(`/api/paths/${id}/move`, { direction }),
  restoreStarters: () => post<{ restored: number }>("/api/paths/restore-starters"),
  addModule: (pathId: number, b: { title: string; summary: string }) => post<{ id: number }>(`/api/paths/${pathId}/modules`, b),
  updateModule: (id: number, b: { title?: string; summary?: string }) => patch<{ id: number }>(`/api/modules/${id}`, b),
  moveModule: (id: number, direction: Direction) => post<Ok>(`/api/modules/${id}/move`, { direction }),
  deleteModule: (id: number) => del(`/api/modules/${id}`),
  addLesson: (moduleId: number, b: { title: string; est_minutes: number; objectives: string[] }) =>
    post<{ id: number }>(`/api/modules/${moduleId}/lessons`, b),
  updateLesson: (id: number, b: { title?: string; est_minutes?: number; objectives?: string[] }) =>
    patch<{ id: number }>(`/api/lessons/${id}`, b),
  moveLesson: (id: number, direction: Direction) => post<Ok>(`/api/lessons/${id}/move`, { direction }),
  deleteLesson: (id: number) => del(`/api/lessons/${id}`),
  links: (pathId?: number) => get<MyLink[]>(`/api/links${pathId ? `?path_id=${pathId}` : ""}`),
  createLink: (b: LinkInput) => post<MyLink>("/api/links", b),
  updateLink: (id: number, b: Partial<LinkInput> & { clear_path?: boolean }) => patch<MyLink>(`/api/links/${id}`, b),
  moveLink: (id: number, direction: Direction) => post<Ok>(`/api/links/${id}/move`, { direction }),
  deleteLink: (id: number) => del(`/api/links/${id}`),

  // Claude Academy
  academy: () => get<Academy>("/api/claude-academy"),
  setCourseStatus: (slug: string, status: CourseStatus) =>
    req<{ status: CourseStatus }>("PUT", `/api/claude-academy/courses/${slug}/status`, { status }),
  aiUpdates: () => get<AIUpdates>("/api/claude-academy/updates"),
  refreshUpdates: (days: number) => post<AIUpdates>("/api/claude-academy/updates/refresh", { days }),
  courseQA: (slug: string) => get<CourseQA>(`/api/claude-academy/qa/${slug}`),
  generateQA: (slug: string, per_lesson: number) => post<CourseQA>(`/api/claude-academy/qa/${slug}/generate`, { per_lesson }),
  editQA: (id: number, b: { question: string; answer_md: string; key_points: string[] }) => patch<QAItem>(`/api/claude-academy/qa/items/${id}`, b),
  deleteQA: (id: number) => del(`/api/claude-academy/qa/items/${id}`),
  setQAStatus: (id: number, status: QAStatus) => patch<QAItem>(`/api/claude-academy/qa/items/${id}`, { status }),

  // Career
  certifications: () => get<Certifications>("/api/career/certifications"),
  refreshCertifications: () => post<Certifications>("/api/career/certifications/refresh"),
  jobs: () => get<Jobs>("/api/career/jobs"),
  refreshJobs: (b: JobsParams) => post<Jobs>("/api/career/jobs/refresh", b),
  academyPath: () => post<{ path_id: number; created: boolean }>("/api/claude-academy/path"),

  // Voice (ASR + NLU)
  voiceLangs: () => get<VoiceLang[]>("/api/voice"),
  voice: (lang: string) => get<VoiceData>(`/api/voice/${lang}`),
  setVoiceState: (lang: string, kind: "skill" | "course" | "step", key: string, value: number | string | boolean) =>
    req<Ok>("PUT", `/api/voice/${lang}/state`, { kind, key, value }),
  voicePath: (lang: string) => post<{ path_id: number; created: boolean }>(`/api/voice/${lang}/path`),
  voiceResearch: (lang: string) => get<HVResearch>(`/api/voice/${lang}/research`),
  refreshVoiceResearch: (lang: string, months: number) => post<HVResearch>(`/api/voice/${lang}/research/refresh`, { months }),
  utterances: (lang: string) => get<Utterances>(`/api/voice/${lang}/utterances`),
  editUtterance: (lang: string, old: string, text: string | null) =>
    post<Utterances>(`/api/voice/${lang}/utterances/edit`, text === null ? { old } : { old, text }),
  generateUtterances: (lang: string, b: UtterParams) => post<Utterances>(`/api/voice/${lang}/utterances/generate`, b),

  // Interview companion
  interviews: () => get<InterviewSummary[]>("/api/interviews"),
  interview: (id: number) => get<InterviewDetail>(`/api/interviews/${id}`),
  createInterview: (b: InterviewConfig) => post<{ id: number; run_id: number }>("/api/interviews", b),
  updateInterview: (id: number, b: Partial<InterviewConfig> & { clear_date?: boolean }) =>
    patch<InterviewConfig>(`/api/interviews/${id}`, b),
  rebuildInterview: (id: number, b: { replace_plan: boolean; replace_questions: boolean }) =>
    post<{ run_id: number }>(`/api/interviews/${id}/rebuild`, b),
  deleteInterview: (id: number, deletePlan = true) => del(`/api/interviews/${id}?delete_plan=${deletePlan}`),
  coach: (id: number) => post<{ text: string }>(`/api/interviews/${id}/coach`),
  rateSkill: (id: number, rating: number) => patch<{ self_rating: number | null }>(`/api/interview-skills/${id}`, { self_rating: rating }),
  questions: (id: number, f: Partial<Record<"area" | "qtype" | "difficulty" | "status" | "q", string>> = {}) => {
    const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v) as [string, string][]).toString();
    return get<IQuestion[]>(`/api/interviews/${id}/questions${qs ? `?${qs}` : ""}`);
  },
  generateQuestions: (id: number, b: { area?: string; qtype?: QType; difficulty?: Difficulty; count: number }) =>
    post<{ run_id: number }>(`/api/interviews/${id}/questions/generate`, b),
  addQuestion: (id: number, b: { question: string; area: string; qtype: QType; difficulty: Difficulty; answer_md: string }) =>
    post<IQuestion>(`/api/interviews/${id}/questions`, b),
  updateQuestion: (qid: number, b: Partial<Pick<IQuestion, "status" | "question" | "answer_md" | "key_points" | "difficulty" | "qtype">>) =>
    patch<IQuestion>(`/api/interview-questions/${qid}`, b),
  deleteQuestion: (qid: number) => del(`/api/interview-questions/${qid}`),
  mockNext: (id: number, b: { area?: string; qtype?: QType; exclude: number[] }) => post<IQuestion>(`/api/interviews/${id}/mock/next`, b),
  submitAttempt: (qid: number, answer: string) => post<Attempt & { question: IQuestion }>(`/api/interview-questions/${qid}/attempts`, { answer }),
  attempts: (id: number) => get<Attempt[]>(`/api/interviews/${id}/attempts`),
};
