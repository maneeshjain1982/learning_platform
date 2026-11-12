from fastapi import APIRouter

from . import chat, claude, home, interview, lessons, manage, paths, search, settings

router = APIRouter()
for module in (chat, claude, home, interview, lessons, manage, paths, search, settings):
    router.include_router(module.router)
