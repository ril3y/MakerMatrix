"""
Guest Rate Limiting Middleware

Applies strict rate limits to guest users to prevent abuse and DDoS attacks.
Regular authenticated users are not affected by these limits.
"""

from fastapi import Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from jose import jwt, JWTError
import os

# Get JWT secret from environment
SECRET_KEY = os.getenv("JWT_SECRET_KEY")


def get_guest_identifier(request: Request) -> str:
    """
    Extract identifier for rate limiting.
    For guests: use IP address
    For authenticated users: use username (exempt from guest limits)
    """
    # Check for API key authentication (X-API-Key header or Authorization: ApiKey)
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("ApiKey "):
            api_key = auth_header[7:]  # Remove "ApiKey " prefix

    # If API key is present, user is authenticated and exempt from guest limits
    if api_key:
        return f"apikey:{api_key[:12]}"  # Use key prefix as identifier

    # Try to get JWT token from Authorization header
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

        try:
            # Decode token without verification (we just need to check if guest)
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"], options={"verify_signature": True})

            # Check if user is a guest
            is_guest = payload.get("is_guest", False)

            if is_guest:
                # Guest users: rate limit by IP
                return f"guest:{get_remote_address(request)}"
            else:
                # Regular authenticated users: exempt from guest limits
                # Return a unique identifier that won't hit limits
                username = payload.get("sub", "unknown")
                return f"user:{username}"
        except JWTError:
            # Invalid token, treat as guest
            return f"guest:{get_remote_address(request)}"

    # No token provided, treat as unauthenticated guest
    return f"guest:{get_remote_address(request)}"


# Create limiter instance for guests
# Limits: 100 requests per minute, 1000 per hour
guest_limiter = Limiter(
    key_func=get_guest_identifier,
    default_limits=["100/minute", "1000/hour"],
    headers_enabled=True,  # Add rate limit info to response headers
)


from slowapi.util import get_ipaddr
from limits import RateLimitItem, parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

# Create in-memory storage for rate limits
storage = MemoryStorage()
rate_limiter_strategy = MovingWindowRateLimiter(storage)

# Define rate limits for guests
GUEST_LIMITS = [
    parse("100/minute"),  # 100 requests per minute
    parse("1000/hour"),  # 1000 requests per hour
]


async def check_guest_rate_limit(request: Request) -> bool:
    """
    Check if guest user has exceeded rate limit.
    Returns True if allowed, raises HTTPException if rate limited.
    """
    # Get the identifier
    identifier = get_guest_identifier(request)

    # Only apply limits to guests
    if not identifier.startswith("guest:"):
        return True

    # Check each rate limit
    for limit in GUEST_LIMITS:
        # Use the IP address as the key
        ip_address = get_ipaddr(request)
        key = f"guest_rate_limit:{ip_address}"

        # Check if limit exceeded
        if not rate_limiter_strategy.hit(limit, key):
            # Calculate retry time
            window_stats = storage.get(key)

            # Get the limit type (minute/hour)
            if "minute" in str(limit):
                retry_after = 60
                limit_description = f"{limit.amount} requests per minute"
            else:
                retry_after = 3600
                limit_description = f"{limit.amount} requests per hour"

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for guest users: {limit_description}. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

    return True


async def guest_rate_limit_middleware(request: Request, call_next):
    """
    Middleware to apply rate limits to guest users only.
    Regular authenticated users bypass this middleware.
    """
    # Skip rate limiting for public endpoints
    public_paths = ["/", "/docs", "/redoc", "/openapi.json", "/api/auth/login", "/api/auth/guest-login"]

    if request.url.path in public_paths or request.url.path.startswith("/ws"):
        response = await call_next(request)
        return response

    # Check rate limit for guests
    await check_guest_rate_limit(request)

    # If not rate limited, proceed
    response = await call_next(request)
    return response
