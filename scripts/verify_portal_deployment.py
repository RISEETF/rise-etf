#!/usr/bin/env python3
"""Verify deployed GitHub Pages files against the checked-out repository.

No writes to market data. Exit nonzero on incomplete build or content mismatch.
"""
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = os.environ.get("GITHUB_REPOSITORY", "RISEETF/rise-etf")
TOKEN = os.environ.get("GH_TOKEN", "")
FILES = ("etf.html", "etf.js", "etf.css", "index.html", "dashboard.js", "intelligence/data/latest.json",
         "data/operations/intelligence.json", "data/quality/krx_rise_inventory.json")
TIMEOUT = 20
ATTEMPTS = int(os.environ.get("PORTAL_VERIFY_ATTEMPTS", "12"))
WAIT = int(os.environ.get("PORTAL_VERIFY_WAIT_SECONDS", "20"))


def fetch(url, api=False):
    headers = {"User-Agent": "RISE-portal-deployment-verifier/1.0",
               "Cache-Control": "no-cache", "Pragma": "no-cache"}
    if api:
        headers["Accept"] = "application/vnd.github+json"
        if TOKEN:
            headers["Authorization"] = "Bearer " + TOKEN
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read(), response.status


def verify():
    if not TOKEN:
        raise RuntimeError("GH_TOKEN_MISSING")
    base = "https://api.github.com/repos/" + REPO
    pages = json.loads(fetch(base + "/pages", True)[0])
    published = pages.get("html_url")
    if not published or not published.startswith("https://"):
        raise RuntimeError("PAGES_URL_MISSING")
    # Verify that Pages is sourced from the repository's main branch root.
    source = pages.get("source") or {}
    if source.get("branch") != "main" or source.get("path") != "/":
        raise RuntimeError("PAGES_SOURCE_UNEXPECTED")
    result = {"schema_version": "1.0", "repo": REPO, "pages_url": published,
              "files": [], "status": "PENDING"}
    for attempt in range(1, ATTEMPTS + 1):
        result["attempt"] = attempt
        try:
            build = json.loads(fetch(base + "/pages/builds/latest", True)[0])
            result["pages_build_status"] = build.get("status", "UNKNOWN")
            # Pages legacy build reports 'built' on success.
            if build.get("status") not in ("built",):
                raise RuntimeError("PAGES_BUILD_NOT_READY")
            checks = []
            for path in FILES:
                local = ROOT / path
                if not local.is_file():
                    raise RuntimeError("LOCAL_FILE_MISSING:" + path)
                url = urllib.parse.urljoin(published.rstrip("/") + "/", path)
                url += ("&" if "?" in url else "?") + "verify=" + str(int(time.time()))
                remote, status = fetch(url)
                expected = hashlib.sha256(local.read_bytes()).hexdigest()
                actual = hashlib.sha256(remote).hexdigest()
                checks.append({"path": path, "http_status": status,
                               "sha256_match": expected == actual})
                if status != 200 or expected != actual:
                    raise RuntimeError("DEPLOYED_CONTENT_MISMATCH:" + path)
            result["files"] = checks
            result["status"] = "PASS"
            return result
        except (RuntimeError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            result["status"] = "RETRYING"
            result["reason"] = str(exc).split(":")[0][:80]
            if attempt < ATTEMPTS:
                time.sleep(WAIT)
    result["status"] = "FAIL"
    return result


if __name__ == "__main__":
    try:
        output = verify()
    except Exception as exc:
        output = {"status": "FAIL", "reason": type(exc).__name__}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if output.get("status") == "PASS" else 1)
