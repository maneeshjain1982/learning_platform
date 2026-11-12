from fastapi import APIRouter

from . import career, chat, claude, home, interview, lessons, manage, paths, search, settings, voice

router = APIRouter()
for module in (career, chat, claude, home, interview, lessons, manage, paths, search, settings, voice):
    router.include_router(module.router)
