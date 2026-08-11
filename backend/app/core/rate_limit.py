from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

# Simple in-memory rate limiter using client IP
# For production behind a proxy (like Nginx), ensure Forwarded-For headers are used.
limiter = Limiter(key_func=get_remote_address)
