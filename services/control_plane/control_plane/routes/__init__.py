from control_plane.routes.audit import router as audit_router
from control_plane.routes.bundle import router as bundle_router
from control_plane.routes.closed_loop import router as closed_loop_router
from control_plane.routes.middlewares import router as middlewares_router
from control_plane.routes.parameters import router as parameters_router
from control_plane.routes.rebac import router as rebac_router
from control_plane.routes.routes import router as routes_router
from control_plane.routes.stats import router as stats_router
from control_plane.routes.upstreams import router as upstreams_router
from control_plane.routes.users import router as users_router

__all__ = [
    "audit_router",
    "bundle_router",
    "closed_loop_router",
    "middlewares_router",
    "parameters_router",
    "rebac_router",
    "routes_router",
    "stats_router",
    "upstreams_router",
    "users_router",
]
