from fastapi import APIRouter

from . import career, chat, claude, home, interview, lessons, manage, paths, search, settings

router = APIRouter()
for module in (career, chat, claude, home, interview, lessons, manage, paths, search, settings):
    router.include_router(module.router)
