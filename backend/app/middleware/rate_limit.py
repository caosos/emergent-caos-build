"""Rate limiting middleware for API protection.

Prevents abuse by limiting requests per user/IP across different endpoint types.
"""
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # Store: {user_key: {endpoint_type: [(timestamp, count)]}}
        self.request_history = defaultdict(lambda: defaultdict(list))
        
        # Rate limits per minute
        self.limits = {
            "chat": 10,  # 10 chat requests per minute
            "upload": 5,  # 5 file uploads per minute
            "default": 30,  # 30 general API calls per minute
        }
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """Get unique key for rate limiting (user email or IP)."""
        # Try to get user from state (set by auth middleware)
        user = getattr(request.state, "user", None)
        if user and isinstance(user, dict):
            return f"user:{user.get('email', 'unknown')}"
        
        # Fallback to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _get_endpoint_type(self, path: str) -> str:
        """Classify endpoint for rate limiting."""
        if "/chat" in path:
            return "chat"
        if "/upload" in path:
            return "upload"
        return "default"
    
    def _cleanup_old_requests(self, history: list, window_seconds: int = 60):
        """Remove requests older than the time window."""
        cutoff = time.time() - window_seconds
        return [ts for ts in history if ts > cutoff]
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/api/health", "/api/"]:
            return await call_next(request)
        
        key = self._get_rate_limit_key(request)
        endpoint_type = self._get_endpoint_type(request.url.path)
        limit = self.limits.get(endpoint_type, self.limits["default"])
        
        # Get and clean history
        history = self.request_history[key][endpoint_type]
        history = self._cleanup_old_requests(history)
        self.request_history[key][endpoint_type] = history
        
        # Check if limit exceeded
        if len(history) >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {limit} requests per minute for {endpoint_type} endpoints. Try again in {60 - int(time.time() - history[0])} seconds."
            )
        
        # Record this request
        history.append(time.time())
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(limit - len(history))
        response.headers["X-RateLimit-Reset"] = str(int(history[0] + 60) if history else int(time.time() + 60))
        
        return response
