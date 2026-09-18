"""Get LinkedIn profiles by URL or by the slug in that URL.

    slugs -> scrape.linkedin.profiles(urls) -> rows -> matched back by input

Every profile asked for goes into one job. The API bills per record, not per
job, and a job takes about the same time for one URL as for ten.

Rows are matched to inputs on the row's own `input_url` or `input.url`, never on
position. With a list of URLs the SDK pairs rows to inputs by index, and the API
returns them in a different order each run, so the SDK's `ScrapeResult.url` can
name one person while `data` holds another's profile (sdk-python#60).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brightdata import SyncBrightDataClient

#: Seconds, the SDK's own unit and default. The JavaScript twin counts in ms.
TIMEOUT = 180

_SLUG = re.compile(r"^[A-Za-z0-9\-_%.]{2,100}$")


def clean_slug(value: str) -> str:
    """Accept satyanadella, a full profile URL, or one with a query string."""
    cleaned = (value or "").strip().split("?", 1)[0].split("#", 1)[0].rstrip("/")
    if "linkedin.com/" in cleaned:
        cleaned = cleaned.rsplit("/", 1)[-1]
    if not _SLUG.match(cleaned):
        raise ValueError(f"{value!r} is not a LinkedIn profile")
    return cleaned


def profile_url(value: str) -> str:
    return f"https://www.linkedin.com/in/{clean_slug(value)}/"


def rows(result: Any) -> list[dict[str, Any]]:
    """Flatten a ScrapeResult, or a list of them, into plain dicts."""
    if isinstance(result, list):
        return [row for item in result for row in rows(item)]
    data = getattr(result, "data", result)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def envelope_error(result: Any) -> str | None:
    """A failed or timed out request carries no rows to explain itself.

    On failure the SDK returns one ScrapeResult even for list input, so this is
    the only shape that can say the whole job died.
    """
    if isinstance(result, list) or getattr(result, "success", True):
        return None
    return str(getattr(result, "error", None) or getattr(result, "status", "request failed"))


def row_input(row: dict[str, Any]) -> str:
    """The URL a row answers for. Success rows say input_url, error rows input.url."""
    found = row.get("input_url") or (row.get("input") or {}).get("url") or row.get("url")
    return str(found or "")


@dataclass
class Outcome:
    """What happened to one profile."""

    slug: str
    profile: dict[str, Any] | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def line(self) -> str:
        """One line a reader can understand without having read the source."""
        if not self.ok:
            return f"failed  {self.slug}: {self.error}"
        name = f" ({self.profile['name']})" if self.profile and self.profile.get("name") else ""
        return f"got     {self.slug}: {len(self.profile or {})} fields{name}"


def attribute(slugs: list[str], found: list[dict[str, Any]]) -> list[Outcome]:
    """Match each row to the slug that asked for it, by the row's own input."""
    by_slug: dict[str, dict[str, Any]] = {}
    for row in found:
        source = row_input(row)
        slug = next(
            (s for s in slugs if f"/in/{s}/" in source or source.endswith(f"/in/{s}")), None
        )
        if slug and slug not in by_slug:
            by_slug[slug] = row

    outcomes = []
    for slug in slugs:
        row = by_slug.get(slug)
        if row is None:
            outcomes.append(Outcome(slug, error="the API returned no row for this profile"))
        elif row.get("error"):
            outcomes.append(Outcome(slug, error=str(row["error"])))
        else:
            outcomes.append(Outcome(slug, profile=row))
    return outcomes


def client_context(client: Any = None) -> Any:
    """The client passed in, or one we open and own.

    SyncBrightDataClient builds its event loop in __enter__, so it must be
    entered. An unentered client fails with an AttributeError about
    run_until_complete.
    """
    # auto_create_zones defaults to True: the SDK tries to create Web Unlocker
    # and SERP zones on startup, which this scraper never uses. Creating a zone
    # needs a payment method, so leaving it on breaks the first run for free
    # accounts.
    return nullcontext(client) if client is not None else SyncBrightDataClient(
        auto_create_zones=False
    )


def fetch(client: Any, slugs: list[str], timeout: int = TIMEOUT) -> list[Outcome]:
    """One job for every slug. Never raises: a failure becomes Outcomes."""
    if not slugs:
        return []
    try:
        urls = [profile_url(slug) for slug in slugs]
        # A list, even of one, so the SDK never collapses the answer to a dict.
        result = client.scrape.linkedin.profiles(urls, timeout=timeout)
        failed = envelope_error(result)
        if failed:
            return [Outcome(slug, error=failed) for slug in slugs]
        return attribute(slugs, rows(result))
    except Exception as exc:  # one bad batch must not end the run with a traceback
        return [Outcome(slug, error=f"{type(exc).__name__}: {exc}") for slug in slugs]


def scrape(values: Iterable[str], client: Any = None) -> list[Outcome]:
    """One Outcome per input, in the order asked, whatever the API returned."""
    values = list(values)
    slugs: list[str] = []
    rejected: dict[str, Outcome] = {}
    for value in values:
        try:
            slugs.append(clean_slug(value))
        except ValueError as exc:
            rejected[str(value)] = Outcome(str(value), error=str(exc))

    found: dict[str, Outcome] = {}
    if slugs:
        with client_context(client) as opened:
            found = {o.slug: o for o in fetch(opened, list(dict.fromkeys(slugs)))}

    out = []
    for value in values:
        if str(value) in rejected:
            out.append(rejected[str(value)])
        else:
            out.append(found[clean_slug(value)])
    return out


def write(outcomes: list[Outcome], path: str | Path) -> Path:
    """Write one JSON file: when it ran, and the profile found per slug."""
    document = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profiles": [{"slug": o.slug, "profile": o.profile} for o in outcomes],
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return target
