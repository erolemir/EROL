"""Bounded public HTTPS access receipts; access does not certify claim truth."""

from __future__ import annotations

import hashlib
import http.client
import ipaddress
import socket
import ssl
import subprocess
import sys
import time
from urllib.parse import urljoin, urlsplit

from .common import ErolError, now
from .security import assert_secret_safe


def public_target(url: str, *, deadline: float | None = None) -> tuple[str, str, str]:
    assert_secret_safe(url)
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
        or parsed.fragment
    ):
        raise ErolError("Source access requires credential-free public HTTPS on port 443")
    host = parsed.hostname.encode("idna").decode("ascii")
    if deadline is None:
        addresses = sorted(
            {str(item[4][0]) for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        )
    else:
        # OS DNS APIs have no portable timeout. Bound an isolated resolver process instead.
        import json
        import os

        outcome = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                "import json,socket,sys; print(json.dumps(sorted("
                "{str(x[4][0]) for x in "
                "socket.getaddrinfo(sys.argv[1],443,type=socket.SOCK_STREAM)})))",
                host,
            ],
            timeout=max(0.01, min(10, deadline - time.monotonic())),
            capture_output=True,
            check=False,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        if outcome.returncode or len(outcome.stdout) > 16000:
            raise ErolError("Public source DNS lookup failed")
        addresses = json.loads(outcome.stdout)
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ErolError("Private, reserved or mixed DNS source targets are blocked")
    return (
        host,
        str(addresses[0]),
        (parsed.path or "/") + ("?" + parsed.query if parsed.query else ""),
    )


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, timeout: float):
        self.tls_context = ssl.create_default_context()
        super().__init__(host, timeout=timeout, context=self.tls_context)
        self.address = address

    def connect(self) -> None:
        raw = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self.tls_context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def fetch_source(url: str, *, deadline: float, cancelled=lambda: False) -> dict:
    original = url
    for _ in range(4):
        if cancelled() or time.monotonic() >= deadline:
            raise ErolError("Source access cancelled or budget exhausted")
        host, address, path = public_target(url, deadline=deadline)
        connection = PinnedHTTPS(host, address, min(10, deadline - time.monotonic()))
        try:
            connection.request(
                "GET",
                path,
                headers={"User-Agent": "EROL-source-receipt/1", "Accept-Encoding": "identity"},
            )
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location:
                    raise ErolError("Source redirect has no target")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ErolError("Source server did not return HTTP 200")
            content_type = response.getheader("Content-Type", "").split(";")[0].strip()
            if content_type not in {
                "text/html",
                "text/plain",
                "application/json",
                "application/pdf",
                "application/xhtml+xml",
            }:
                raise ErolError("Unsupported source content type")
            hasher = hashlib.sha256()
            size = 0
            while True:
                if cancelled() or time.monotonic() >= deadline:
                    raise ErolError("Source access cancelled or budget exhausted")
                if connection.sock is not None:
                    connection.sock.settimeout(min(10, max(0.01, deadline - time.monotonic())))
                chunk = response.read1(65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > 1048576:
                    raise ErolError("Source body exceeds one MiB receipt budget")
                hasher.update(chunk)
            return {
                "url": original,
                "final_url": url,
                "status": "accessed",
                "http_status": 200,
                "content_type": content_type,
                "content_sha256": hasher.hexdigest(),
                "bytes": size,
                "fetched_at": now(),
                "evidence_type": "runner_observed_source_access",
            }
        finally:
            connection.close()
    raise ErolError("Source redirect limit exceeded")


def fetch_sources(ledger: dict, *, seconds: float = 60, cancelled=lambda: False) -> list[dict]:
    deadline = time.monotonic() + max(0, min(seconds, 60))
    receipts = []
    for source in ledger["sources"]:
        try:
            receipt = fetch_source(source["url"], deadline=deadline, cancelled=cancelled)
        except (
            ErolError,
            OSError,
            ValueError,
            http.client.HTTPException,
            subprocess.SubprocessError,
        ) as exc:
            receipt = {
                "url": source["url"],
                "status": "unavailable",
                "fetched_at": now(),
                "evidence_type": "runner_observed_source_access",
                "reason": str(exc)[:300] if isinstance(exc, ErolError) else type(exc).__name__,
            }
        receipts.append({"source_id": source["id"], **receipt})
    return receipts
