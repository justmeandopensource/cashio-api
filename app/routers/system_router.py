from fastapi import APIRouter
from app.version import __version__
import platform

system_Router = APIRouter(prefix="/api")

@system_Router.get("/sysinfo", tags=["system"])
async def get_sysinfo():
    return {
        "version": __version__,
        "environment": {
            "python_version": platform.python_version(),
            "platform":  platform.platform(),
            "platform_release": platform.release()
        }
    }
