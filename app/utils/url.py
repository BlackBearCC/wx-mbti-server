"""URL utilities for building absolute links.

For client compatibility (WeChat Mini Program and others), we normalize asset
links to HTTPS. The backend must be started with TLS in local and container
environments.
"""
from fastapi import Request


def build_base_url(request: Request, force_https: bool = True) -> str:
    """Return base URL like "https://host:port" (HTTPS enforced by default)."""
    host = request.headers.get("host") or request.url.netloc
    scheme = "https" if force_https else request.url.scheme
    return f"{scheme}://{host}"
