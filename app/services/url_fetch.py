"""SSRF-safe synchronous URL fetch for image downloads."""

import ipaddress
import socket
from urllib.parse import urlparse

import httpx


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
        raise ValueError("Only http and https URLs are allowed")
    if not parsed.hostname:
        raise ValueError("URL must include a hostname")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addrinfos = socket.getaddrinfo(parsed.hostname, port)
    except socket.gaierror as exc:
        raise ValueError("Could not resolve hostname") from exc

    for _, _, _, _, sockaddr in addrinfos:
        ip = ipaddress.ip_address(sockaddr[0])
        if _is_blocked_ip(ip):
            raise ValueError("URL resolves to a blocked address")


def fetch_url_bytes(url: str, timeout: float, max_bytes: int) -> bytes:
    validate_url(url)
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError("Response exceeds maximum allowed size")
                chunks.append(chunk)
    return b"".join(chunks)
