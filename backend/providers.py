"""Keyless content sources: arXiv, Semantic Scholar, YouTube oEmbed checks, and search links."""

from __future__ import annotations

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, quote_plus, urlparse

import httpx

from . import config

log = logging.getLogger("study.providers")
TIMEOUT = httpx.Timeout(20.0)
HEADERS = {"User-Agent": config.HTTP_USER_AGENT}
_arxiv_lock = asyncio.Lock()  # arXiv asks for ~1 request every 3 s


@dataclass
class Candidate:
    kind: str
    source: str
    external_id: str
    title: str
    url: str
    author: str = ""
    year: int | None = None
    summary: str = ""
    thumbnail: str | None = None
    duration_min: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- search links

def search_links(query: str) -> list[dict[str, str]]:
    q = quote_plus(query)
    return [
        {"source": "youtube", "label": "YouTube", "url": f"https://www.youtube.com/results?search_query={q}"},
        {"source": "coursera", "label": "Coursera", "url": f"https://www.coursera.org/search?query={q}"},
        {"source": "udemy", "label": "Udemy", "url": f"https://www.udemy.com/courses/search/?q={q}"},
    ]


# --------------------------------------------------------------------------- arXiv

_STOP = {"a", "an", "the", "of", "for", "and", "or", "in", "on", "to", "with", "how", "what", "is", "are"}
_ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_arxiv(xml_text: str) -> list[Candidate]:
    root = ET.fromstring(xml_text)
    out = []
    for entry in root.findall("a:entry", _ATOM):
        id_url = _clean(entry.findtext("a:id", namespaces=_ATOM))
        if "/abs/" not in id_url:
            continue  # error entries
        arxiv_id = re.sub(r"v\d+$", "", id_url.split("/abs/")[-1])
        authors = [_clean(a.findtext("a:name", namespaces=_ATOM)) for a in entry.findall("a:author", _ATOM)]
        published = entry.findtext("a:published", namespaces=_ATOM) or ""
        author = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        out.append(Candidate(
            kind="paper", source="arxiv", external_id=arxiv_id,
            title=_clean(entry.findtext("a:title", namespaces=_ATOM)),
            url=f"https://arxiv.org/abs/{arxiv_id}", author=author,
            year=int(published[:4]) if published[:4].isdigit() else None,
            summary=_clean(entry.findtext("a:summary", namespaces=_ATOM))[:1200],
            meta={"pdf": f"https://arxiv.org/pdf/{arxiv_id}"},
        ))
    return out


async def _arxiv_get(params: dict) -> list[Candidate]:
    async with _arxiv_lock:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
            r = await client.get("https://export.arxiv.org/api/query", params=params)
            r.raise_for_status()
        await asyncio.sleep(3)
    return parse_arxiv(r.text)


async def arxiv_search(query: str, max_results: int = 8) -> list[Candidate]:
    words = [w for w in re.findall(r"[A-Za-z0-9-]+", query) if w.lower() not in _STOP]
    if not words:
        return []
    raw = re.findall(r"[A-Za-z0-9-]+", query)
    attempts = []
    if 2 <= len(raw) <= 5:
        attempts.append(f'abs:"{" ".join(raw)}"')  # exact phrase first: far more relevant
    attempts.append(" AND ".join(f"abs:{w}" for w in words[:6]))
    try:
        for terms in attempts:
            found = await _arxiv_get({"search_query": terms, "max_results": max_results, "sortBy": "relevance"})
            if len(found) >= 3 or terms == attempts[-1]:
                return found
    except Exception as exc:
        log.warning("arXiv search failed for %r: %s", query, exc)
    return []


async def arxiv_by_ids(ids: list[str]) -> list[Candidate]:
    if not ids:
        return []
    try:
        return await _arxiv_get({"id_list": ",".join(ids), "max_results": len(ids)})
    except Exception as exc:
        log.warning("arXiv id lookup failed: %s", exc)
        return []


# --------------------------------------------------------------------------- Semantic Scholar

async def semantic_scholar_search(query: str, limit: int = 6) -> list[Candidate]:
    fields = "title,authors,year,abstract,citationCount,url,externalIds,openAccessPdf"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
            r = await client.get("https://api.semanticscholar.org/graph/v1/paper/search",
                                 params={"query": query, "limit": limit, "fields": fields})
            if r.status_code == 429:
                log.info("Semantic Scholar rate-limited; skipping")
                return []
            r.raise_for_status()
            data = r.json().get("data", [])
    except Exception as exc:
        log.warning("Semantic Scholar search failed for %r: %s", query, exc)
        return []

    out = []
    for p in data:
        ext = p.get("externalIds") or {}
        arxiv_id = ext.get("ArXiv")
        authors = [a.get("name", "") for a in (p.get("authors") or [])]
        author = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        pdf = (p.get("openAccessPdf") or {}).get("url")
        out.append(Candidate(
            kind="paper",
            source="arxiv" if arxiv_id else "semantic_scholar",
            external_id=arxiv_id or p.get("paperId", ""),
            title=_clean(p.get("title")),
            url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else (p.get("url") or ""),
            author=author, year=p.get("year"),
            summary=_clean(p.get("abstract"))[:1200],
            meta={"citations": p.get("citationCount"), **({"pdf": pdf} if pdf else {})},
        ))
    return [c for c in out if c.external_id and c.title]


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", t.lower())


async def paper_search(query: str, limit: int = 8) -> list[Candidate]:
    """arXiv + Semantic Scholar, merged; Semantic Scholar adds citation counts."""
    arxiv, s2 = await asyncio.gather(arxiv_search(query, limit), semantic_scholar_search(query, 6))
    merged: dict[str, Candidate] = {}
    for c in s2 + arxiv:
        key = norm_title(c.title)
        if key in merged:
            merged[key].meta.setdefault("citations", c.meta.get("citations"))
            continue
        merged[key] = c
    papers = list(merged.values())
    papers.sort(key=lambda c: (c.meta.get("citations") or 0), reverse=True)
    return papers[:limit]


# --------------------------------------------------------------------------- YouTube

_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def youtube_id(url: str) -> str | None:
    try:
        u = urlparse(url.strip())
    except ValueError:
        return None
    host = (u.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    vid = None
    if host == "youtu.be":
        vid = u.path.lstrip("/").split("/")[0]
    elif host in ("youtube.com", "music.youtube.com"):
        if u.path == "/watch":
            vid = (parse_qs(u.query).get("v") or [None])[0]
        else:
            m = re.match(r"^/(embed|shorts|live|v)/([^/?#]+)", u.path)
            vid = m.group(2) if m else None
    return vid if vid and _YT_ID.match(vid) else None


async def youtube_verify(url: str) -> Candidate | None:
    """Confirm a YouTube video exists via the keyless oEmbed endpoint; returns real title/channel."""
    vid = youtube_id(url)
    if not vid:
        return None
    watch = f"https://www.youtube.com/watch?v={vid}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
            r = await client.get("https://www.youtube.com/oembed", params={"url": watch, "format": "json"})
        if r.status_code != 200:
            return None
        data = r.json()
    except Exception as exc:
        log.info("oEmbed check failed for %s: %s", vid, exc)
        return None
    return Candidate(
        kind="video", source="youtube", external_id=vid, title=_clean(data.get("title")), url=watch,
        author=_clean(data.get("author_name")),
        thumbnail=data.get("thumbnail_url") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
    )


# --------------------------------------------------------------------------- link checks

_link_sem = asyncio.Semaphore(6)
_BROWSER_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}


async def check_url(url: str) -> str:
    """'ok' (page loads), 'blocked' (site exists but refuses bots: 401/403/429/5xx) or 'dead' (404/410/no host)."""
    if not re.match(r"^https?://[^/\s]+\.[^/\s]+", url or ""):
        return "dead"
    async with _link_sem:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(12.0), follow_redirects=True,
                                         headers=_BROWSER_HEADERS) as client:
                r = await client.get(url)
        except httpx.TimeoutException:
            return "blocked"  # slow, but the host exists
        except Exception as exc:  # DNS failure, TLS error, refused
            log.info("Link check failed for %s: %s", url, exc)
            return "dead"
    if r.status_code < 400:
        return "ok"
    if r.status_code in (404, 410):
        return "dead"
    return "blocked"
