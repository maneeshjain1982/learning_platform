from fastapi import APIRouter

from . import auth, career, chat, claude, content, home, interview, lessons, manage, news, papers, paths, search, settings, voice

router = APIRouter()
for module in (auth, career, chat, claude, content, home, interview, lessons, manage, news, papers, paths, search,
               settings, voice):
    router.include_router(module.router)
