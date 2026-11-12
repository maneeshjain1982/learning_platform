"""Cold boot: create the user and the seed learning paths, then attach verified arXiv papers.

    python -m backend.seed            # structure + papers (needs internet for arXiv)
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .agents.base import attach, upsert_resource
from .agents.search import titles_match
from .db import init_db, session_scope
from .models import LearningPath, Lesson, Module, User
from .providers import arxiv_by_ids
from .seed_data import SEED_PATHS

log = logging.getLogger("study.seed")


def ensure_user(db: Session) -> User:
    user = db.get(User, 1)
    if user is None:
        user = User(id=1, name="Learner", settings={})
        db.add(user)
        db.flush()
    return user


def seed_structure(db: Session) -> list[int]:
    """Create any missing seed paths. Returns ids of newly created paths. No network."""
    user = ensure_user(db)
    removed = set((user.settings or {}).get("removed_seeds", []))  # starter paths the user deleted
    created = []
    for spec in SEED_PATHS:
        if spec["slug"] in removed:
            continue
        if db.scalars(select(LearningPath).where(LearningPath.slug == spec["slug"])).first():
            continue
        path = LearningPath(slug=spec["slug"], title=spec["title"], summary=spec["summary"], level=spec["level"],
                            hours_per_week=spec["hours_per_week"], weeks=spec["weeks"],
                            sources=["youtube", "coursera", "udemy", "arxiv", "semantic_scholar"],
                            status="ready", is_seed=True)
        for mi, m in enumerate(spec["modules"]):
            mod = Module(idx=mi, title=m["title"], summary=m["summary"], keywords=m["keywords"],
                         paper_keywords=m["paper_keywords"],
                         objectives=[o for l in m["lessons"] for o in l[1]][:4])
            mod.lessons = [Lesson(idx=li, title=t, objectives=obj, keywords=kw, est_minutes=mins)
                           for li, (t, obj, kw, mins) in enumerate(m["lessons"])]
            path.modules.append(mod)
        db.add(path)
        db.flush()
        created.append(path.id)
    return created


async def attach_seed_papers() -> int:
    """Look up each seed paper on arXiv by id; attach it only if the title matches. Returns papers attached."""
    with session_scope() as db:
        work = []  # (lesson_ids, [(arxiv_id, title)])
        for spec in SEED_PATHS:
            path = db.scalars(select(LearningPath).where(LearningPath.slug == spec["slug"])).first()
            if not path:
                continue
            for mod, m in zip(path.modules, spec["modules"]):
                work.append(([l.id for l in mod.lessons], m["papers"]))

    ids = sorted({pid for _, papers in work for pid, _ in papers})
    found = {}
    for i in range(0, len(ids), 20):
        for c in await arxiv_by_ids(ids[i:i + 20]):
            found[c.external_id] = c

    attached = 0
    with session_scope() as db:
        for lesson_ids, papers in work:
            for k, (pid, title) in enumerate(papers):
                cand = found.get(pid)
                if not cand or not titles_match(title, cand.title):
                    log.warning("Seed paper %s skipped (not found or title mismatch: %r)", pid,
                                cand.title if cand else None)
                    continue
                res = upsert_resource(db, cand)
                attach(db, lesson_ids[min(k, len(lesson_ids) - 1)], res.id, rank=10 + k,
                       why="Key paper for this module.", added_by="seed")
                attached += 1
    return attached


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    init_db()
    with session_scope() as db:
        created = seed_structure(db)
    print(f"Seed paths created: {len(created)}")
    n = asyncio.run(attach_seed_papers())
    print(f"Seed papers attached: {n}")


if __name__ == "__main__":
    main()
