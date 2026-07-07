"""SSRF-safe synchronous URL fetch for image downloads."""

import ipaddress
import socket
from urllib.parse import urlparse

import httpx


class UrlFetchError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UrlFetchError("unsafe_url", "Only http and https URLs are allowed")
    if not parsed.hostname:
        raise UrlFetchError("invalid_url", "URL must include a hostname")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addrinfos = socket.getaddrinfo(parsed.hostname, port)
    except socket.gaierror as exc:
        raise UrlFetchError("url_fetch_failed", "Could not resolve hostname") from exc

    for _, _, _, _, sockaddr in addrinfos:
        ip = ipaddress.ip_address(sockaddr[0])
        if _is_blocked_ip(ip):
            raise UrlFetchError("unsafe_url", "URL resolves to a blocked address")


def fetch_url_bytes(url: str, timeout: float, max_bytes: int) -> bytes:
    validate_url(url)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise UrlFetchError(
                            "payload_too_large",
                            "Response exceeds maximum allowed size",
                        )
                    chunks.append(chunk)
    except httpx.TimeoutException as exc:
        raise UrlFetchError(
            "url_fetch_failed",
            "Timed out fetching image URL",
            status_code=504,
        ) from exc
    except httpx.HTTPError as exc:
        raise UrlFetchError(
            "url_fetch_failed",
            "Failed to fetch image URL",
        ) from exc
    except UrlFetchError:
        raise
    except ValueError as exc:
        raise UrlFetchError("invalid_url", str(exc)) from exc

    return b"".join(chunks)
