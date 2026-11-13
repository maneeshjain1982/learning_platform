from fastapi import APIRouter

from . import auth, career, chat, claude, home, interview, lessons, manage, paths, search, settings, voice

router = APIRouter()
for module in (auth, career, chat, claude, home, interview, lessons, manage, paths, search, settings, voice):
    router.include_router(module.router)
