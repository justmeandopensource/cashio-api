from fastapi import APIRouter
import platform
from app.version import __version__

system_Router = APIRouter(prefix="/api")

@system_Router.get("/sysinfo", tags=["system"])
async def get_sysinfo():
    return {
        "api_version": __version__,
        "python_version": platform.python_version(),
    }

