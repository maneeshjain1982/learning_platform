"""Tests run against a temporary SQLite file, a fake LLM and mocked network calls."""

import os
import re
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="study_test_")
os.environ["STUDY_DATA_DIR"] = _tmp
os.environ["STUDY_DB_URL"] = f"sqlite:///{Path(_tmp, 'test.db').as_posix()}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend import llm as llm_mod  # noqa: E402
from backend import providers, seed  # noqa: E402
from backend.agents import schemas  # noqa: E402
from backend.llm import Answer  # noqa: E402
from backend.providers import Candidate  # noqa: E402


class FakeLLM:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []
        self.web_flags: list[bool] = []

    async def ask(self, prompt, *, system=None, model=None, web=False, timeout=None):
        self.calls.append(("ask", prompt[:60]))
        if "Lesson:" in prompt:
            return Answer("## Overview\nFake notes.", model, 5, "fake")
        if "Write two short" in prompt:
            return Answer("Focus on this lesson today.", model, 5, "fake")
        return Answer("Tutor answer about: " + prompt.splitlines()[-3][:60], model, 5, "fake")

    async def ask_json(self, prompt, schema, *, system=None, model=None, web=False, timeout=None):
        self.calls.append(("json:" + schema.__name__, prompt[:60]))
        if schema is schemas.TopicGraphOut:
            return schema(title="Test Topic", summary="Learn testing.", search_keywords=["testing"],
                          core_topics=[{"name": "Basics", "description": "the basics"},
                                       {"name": "Advanced", "description": "harder"}])
        if schema is schemas.CurriculumOut:
            lesson = lambda t: {"title": t, "objectives": ["do x"], "keywords": [t], "est_minutes": 20}  # noqa
            return schema(modules=[
                {"title": "Module A", "summary": "a", "objectives": ["a"], "keywords": ["module a"],
                 "paper_keywords": ["module a"], "lessons": [lesson("A1"), lesson("A2")]},
                {"title": "Module B", "summary": "b", "objectives": ["b"], "keywords": ["module b"],
                 "paper_keywords": ["module b"], "lessons": [lesson("B1")]},
            ])
        if schema is schemas.VideoPicksOut:
            return schema(videos=[{"lesson_index": 0, "url": "https://www.youtube.com/watch?v=aaaaaaaaaaa",
                                   "title": "t", "why": "good"},
                                  {"lesson_index": 0, "url": "https://example.com/not-youtube", "title": "x",
                                   "why": "bad"}])
        if schema is schemas.CuratorOut:
            return schema(assignments=[{"paper_index": 0, "lesson_index": 0, "why": "relevant"}])
        if schema is schemas.KnownPapersOut:
            return schema(papers=[{"arxiv_id": "2210.03629", "title": "ReAct"},
                                  {"arxiv_id": "9999.99999", "title": "Made up"}])
        if schema is schemas.VideoSearchOut:
            return schema(videos=[{"url": "https://youtu.be/bbbbbbbbbbb", "title": "v", "why": "nice"}])
        if schema is schemas.JDAnalysisOut:
            return schema(role_summary="Own agent platform.", responsibilities=["Design agents"],
                          required_skills=["MCP", "LangGraph"])
        if schema is schemas.RoleResearchOut:
            self.web_flags.append(web)
            return schema(role_summary="Architects agent systems.", responsibilities=["Design"],
                          common_skills=[{"name": "MCP", "note": "most postings"}], interview_format=["System design"],
                          trends=["A2A"], sources=[{"title": "Good", "url": "https://ok.example.com/a"},
                                                   {"title": "Dead", "url": "https://dead.example.com/x"}])
        if schema is schemas.SkillMapOut:
            sk = lambda a, n, imp, jd: {"area": a, "name": n, "importance": imp, "evidence": "e", "in_jd": jd,  # noqa
                                        "how_tested": "design round"}
            return schema(skills=[sk("Tools & protocols", "MCP", "must", True), sk("Tools & protocols", "A2A", "important", False),
                                  sk("Frameworks", "LangGraph", "must", True)])
        if schema is schemas.PrepPlanOut:
            lesson = lambda t: {"title": t, "objectives": ["do x"], "keywords": [t], "est_minutes": 30}  # noqa
            return schema(title="Prep", summary="Prep plan", modules=[
                {"title": "Protocols", "summary": "p", "objectives": ["p"], "keywords": ["mcp"],
                 "paper_keywords": ["tool use"], "lessons": [lesson("MCP deep dive")]}])
        if schema is schemas.QuestionBatchOut:
            n = int(re.search(r"Write (\d+) interview", prompt).group(1))
            area = re.search(r"competency area '([^']+)'", prompt).group(1)
            refs = [{"title": "ReAct", "url": "https://arxiv.org/abs/2210.03629", "arxiv_id": "2210.03629"},
                    {"title": "Fake paper", "url": "https://arxiv.org/abs/9999.99999", "arxiv_id": "9999.99999"},
                    {"title": "MCP spec", "url": "https://ok.example.com/spec", "arxiv_id": ""},
                    {"title": "Gone", "url": "https://dead.example.com/gone", "arxiv_id": ""}]
            skill = "MCP" if area.startswith("Tools") else "LangGraph"
            return schema(questions=[{"skill_name": skill, "qtype": "design" if i % 2 else "concept",
                                      "difficulty": "hard", "question": f"{area} question {i}?",
                                      "answer_md": "Answer [1]", "key_points": ["k1", "k2"], "follow_ups": ["f"],
                                      "red_flags": ["r"], "references": refs} for i in range(n)])
        if schema is schemas.MockGradeOut:
            return schema(score=9, verdict="Strong.", strengths=["clear"], missing=[], better_answer_md="Better.",
                          follow_up="And then?")
        raise AssertionError(schema)


async def fake_check_url(url):
    return "dead" if "dead.example" in url else "ok"


async def fake_verify(url):
    vid = providers.youtube_id(url)
    if not vid:
        return None
    return Candidate(kind="video", source="youtube", external_id=vid, title=f"Video {vid}",
                     url=f"https://www.youtube.com/watch?v={vid}", author="Chan")


async def fake_papers(query, limit=8):
    return [Candidate(kind="paper", source="arxiv", external_id=f"2401.{abs(hash(query)) % 10000:05d}",
                      title=f"Paper about {query}", url="https://arxiv.org/abs/x", year=2024)]


async def fake_arxiv_ids(ids):
    known = {"2210.03629": "ReAct: Synergizing Reasoning and Acting in Language Models"}
    return [Candidate(kind="paper", source="arxiv", external_id=i, title=known[i], url=f"https://arxiv.org/abs/{i}")
            for i in ids if i in known]


@pytest.fixture()
def fake_llm(monkeypatch):
    fake = FakeLLM()
    llm_mod.set_llm(fake)
    monkeypatch.setattr("backend.agents.search.youtube_verify", fake_verify)
    monkeypatch.setattr("backend.agents.search.paper_search", fake_papers)
    monkeypatch.setattr("backend.api.search.paper_search", fake_papers)
    monkeypatch.setattr(seed, "arxiv_by_ids", fake_arxiv_ids)
    monkeypatch.setattr("backend.agents.search.arxiv_by_ids", fake_arxiv_ids)
    monkeypatch.setattr("backend.agents.interview.arxiv_by_ids", fake_arxiv_ids)
    monkeypatch.setattr("backend.agents.interview.check_url", fake_check_url)
    yield fake
    llm_mod.set_llm(None)


@pytest.fixture()
def client(fake_llm):
    from backend.main import app

    with TestClient(app) as c:
        yield c
