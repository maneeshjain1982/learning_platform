from fastapi import APIRouter

from . import chat, home, interview, lessons, manage, paths, search, settings

router = APIRouter()
for module in (chat, home, interview, lessons, manage, paths, search, settings):
    router.include_router(module.router)
