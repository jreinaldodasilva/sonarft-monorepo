"""
SonarFT API Rate Limiter
Centralised slowapi Limiter instance shared across all routers.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# 200 requests/minute per IP as the global default.
# Individual endpoints override this with tighter limits via @limiter.limit().
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
