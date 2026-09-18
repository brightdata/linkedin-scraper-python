"""These run without a token. The client is a stub."""

from __future__ import annotations

import inspect
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from brightdata import BrightDataError

import linkedin_scraper.__main__  # noqa: F401  (registers the module for monkeypatching)
from linkedin_scraper.scrape import attribute, clean_slug, profile_url, scrape, write

ROOT = Path(__file__).resolve().parents[1]
SATYA = "https://www.linkedin.com/in/satyanadella/"
REID = "https://www.linkedin.com/in/reidhoffman/"
DEAD = "https://www.linkedin.com/in/zz-not-a-real-profile-zz/"


def stub(answer, calls=None):
    """A client whose one LinkedIn call returns canned results."""

    def profiles(url, **kwargs):
        if calls is not None:
            calls.append({"url": url, **kwargs})
        if isinstance(answer, Exception):
            raise answer
        return answer

    return SimpleNamespace(scrape=SimpleNamespace(linkedin=SimpleNamespace(profiles=profiles)))


def result(data, **fields):
    return SimpleNamespace(data=data, success=fields.pop("success", True), **fields)


def test_a_slug_a_url_or_a_url_with_a_query_string_name_the_same_profile():
    assert clean_slug("satyanadella") == "satyanadella"
    assert clean_slug(SATYA) == "satyanadella"
    assert clean_slug(SATYA.rstrip("/")) == "satyanadella"
    assert clean_slug(SATYA + "?originalSubdomain=us") == "satyanadella"
    assert profile_url("satyanadella") == SATYA


def test_anything_that_is_not_a_profile_is_refused_before_any_request():
    for bad in ("not a profile", "", "x"):
        with pytest.raises(ValueError, match="is not a LinkedIn profile"):
            clean_slug(bad)


def test_rows_are_matched_by_their_own_input_not_by_position():
    """The exact shape seen live on 2026-09-18 (sdk-python#60).

    The SDK pairs rows with inputs by index, and the API returns them in a
    different order each run. Here the result labelled reidhoffman holds the
    dead profile's error, and the one labelled with the dead slug holds Reid
    Hoffman's profile. Trusting .url would report Reid Hoffman as hidden.
    """
    mislabelled = [
        result({"error": "The profile is hidden or private.", "input": {"url": DEAD}}, url=REID),
        result({"input_url": REID, "name": "Reid Hoffman"}, url=DEAD),
        result({"input_url": SATYA, "name": "Satya Nadella"}, url=SATYA),
    ]
    reid, dead, satya = scrape(
        ["reidhoffman", "zz-not-a-real-profile-zz", "satyanadella"], client=stub(mislabelled)
    )

    assert reid.ok and reid.profile["name"] == "Reid Hoffman"
    assert not dead.ok and dead.error == "The profile is hidden or private."
    assert satya.ok and satya.profile["name"] == "Satya Nadella"


def test_an_error_row_fails_only_the_profile_it_belongs_to():
    rows = [
        {"input_url": SATYA, "name": "Satya Nadella"},
        {"error": "The profile is hidden or private.", "input": {"url": DEAD}},
    ]
    good, bad = attribute(["satyanadella", "zz-not-a-real-profile-zz"], rows)

    assert good.ok
    assert bad.line() == "failed  zz-not-a-real-profile-zz: The profile is hidden or private."


def test_a_profile_the_api_never_returned_is_a_failure_not_a_silent_gap():
    """zip() in the SDK stops at the shorter list, so a missing row just vanishes."""
    [only] = scrape(["satyanadella"], client=stub([]))

    assert not only.ok
    assert "no row" in only.error


def test_a_timed_out_request_fails_every_profile_in_the_batch():
    """On failure the SDK returns one result, not a list, even for list input."""
    timed_out = result(None, success=False, error=None, status="timeout")
    outcomes = scrape(["satyanadella", "reidhoffman"], client=stub(timed_out))

    assert [o.error for o in outcomes] == ["timeout", "timeout"]


def test_one_bad_input_does_not_stop_the_others_being_fetched():
    good, bad = scrape(
        ["satyanadella", "not a profile"], client=stub([result({"input_url": SATYA})])
    )

    assert good.ok
    assert not bad.ok and "is not a LinkedIn profile" in bad.error


def test_a_raised_request_does_not_end_the_run():
    [outcome] = scrape(["satyanadella"], client=stub(RuntimeError("boom")))

    assert outcome.error == "RuntimeError: boom"


def test_every_profile_goes_in_one_job():
    """The API bills per record, and a job takes as long for ten URLs as for one."""
    calls = []
    scrape(["satyanadella", "reidhoffman"], client=stub([], calls))

    assert len(calls) == 1, "a batch must be one job, not one job per profile"
    assert calls[0]["url"] == [SATYA, REID]


def test_a_run_writes_what_it_found(tmp_path):
    profile = {"input_url": SATYA, "name": "Satya Nadella"}
    outcomes = scrape(["satyanadella"], client=stub([result(profile)]))

    assert outcomes[0].line() == "got     satyanadella: 2 fields (Satya Nadella)"

    path = write(outcomes, tmp_path / "out.json")
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["profiles"] == [{"slug": "satyanadella", "profile": profile}]
    assert document["generated_at"]


def test_a_client_we_own_gets_entered(monkeypatch):
    """SyncBrightDataClient is unusable until __enter__ builds its event loop."""
    entered = []

    class Fake:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            entered.append(True)
            return stub([result({"input_url": SATYA})])

        def __exit__(self, *exc):
            entered.append(False)
            return False

    monkeypatch.setattr(sys.modules["linkedin_scraper.scrape"], "SyncBrightDataClient", Fake)
    assert scrape(["satyanadella"])[0].ok
    assert entered == [True, False]


def test_we_do_not_ask_the_sdk_to_create_zones(monkeypatch):
    """Zone creation needs a payment method and this scraper never uses a zone."""
    seen = {}

    class Fake:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def __enter__(self):
            return stub([])

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(sys.modules["linkedin_scraper.scrape"], "SyncBrightDataClient", Fake)
    scrape(["satyanadella"])
    assert seen.get("auto_create_zones") is False


def fake_cli(monkeypatch, answer):
    """Point the CLI at a client that never exists and an answer we control."""
    from contextlib import nullcontext

    cli = sys.modules["linkedin_scraper.__main__"]
    monkeypatch.setattr(cli, "client_context", lambda: nullcontext(stub(answer)))
    return cli


def test_the_cli_exit_code_says_whether_every_profile_worked(monkeypatch, tmp_path):
    cli = fake_cli(monkeypatch, [result({"input_url": SATYA, "name": "S"})])
    assert cli.main(["satyanadella", "--out", str(tmp_path / "ok.json")]) == 0

    cli = fake_cli(monkeypatch, [result({"input": {"url": SATYA}, "error": "boom"})])
    assert cli.main(["satyanadella", "--out", str(tmp_path / "bad.json")]) == 1


def test_no_profile_is_refused_before_any_request(capsys):
    cli = sys.modules["linkedin_scraper.__main__"]
    with pytest.raises(SystemExit) as exit_info:
        cli.main([])
    assert exit_info.value.code == 2
    assert "usage: linkedin-scraper" in capsys.readouterr().err


def test_a_missing_token_is_a_message_not_a_traceback(monkeypatch, capsys):
    cli = sys.modules["linkedin_scraper.__main__"]

    def no_token():
        raise BrightDataError("API token required but not found.")

    monkeypatch.setattr(cli, "client_context", no_token)
    assert cli.main(["satyanadella"]) == 2
    err = capsys.readouterr().err
    assert "export BRIGHTDATA_API_TOKEN" in err and "bdata login" in err
    assert "Pass as parameter" not in err, "the SDK's Python-only advice leaked into the CLI"


def test_piped_output_keeps_the_header_before_the_error(tmp_path):
    """A log or an agent reads a pipe. The header must not land after the error."""
    tokens = ("BRIGHTDATA_API_TOKEN", "BRIGHTDATA_API_KEY")
    env = {k: v for k, v in os.environ.items() if k not in tokens}
    env["HOME"] = str(tmp_path)  # no CLI login, no .env: the stranger's machine
    run = subprocess.run(
        [sys.executable, "-m", "linkedin_scraper", "satyanadella"],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=60,
    )
    assert run.returncode == 2, run.stdout
    assert run.stdout.index("Fetching 1 LinkedIn profile") < run.stdout.index("API token required")


def test_the_sdk_contract_the_readme_relies_on():
    """Offline, no token. Every claim the README makes about the SDK, pinned here."""
    from brightdata.scrapers import workflow
    from brightdata.scrapers.linkedin import LinkedInScraper, LinkedInSearchScraper

    for name in ("profiles", "companies", "jobs", "posts"):
        for suffix in ("", "_trigger", "_status", "_fetch"):
            assert callable(getattr(LinkedInScraper, name + suffix, None)), name + suffix
    for name in ("profiles", "jobs", "posts"):
        assert callable(getattr(LinkedInSearchScraper, name, None)), name

    # The profiles dataset is the one the control panel shows.
    assert LinkedInScraper.DATASET_ID == "gd_l1viktl72bvl7bjuj0"

    # Name search takes a first and last name, not a URL.
    params = inspect.signature(LinkedInSearchScraper.profiles).parameters
    assert "first_name" in params and "url" not in params

    # Job search has no way to cap how many rows it returns, and so what it
    # bills. This is why the README does not run it. If a cap is ever added,
    # this fails, and the README should start using it.
    params = inspect.signature(LinkedInSearchScraper.jobs).parameters
    assert not any("limit" in p or "num_of" in p for p in params), params

    # Timeouts are seconds here, where the JavaScript twin counts milliseconds.
    assert inspect.signature(LinkedInScraper.profiles).parameters["timeout"].default == 180

    # Error rows arrive only because the SDK asks for them. The API default is off.
    executor = next(c for c in vars(workflow).values() if hasattr(c, "execute"))
    assert inspect.signature(executor.execute).parameters["include_errors"].default is True


def test_the_readme_excerpt_is_the_start_of_the_example_file():
    """The README shows the start of the real file, verbatim, and links it."""
    sample = (ROOT / "examples" / "sample_output.json").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "\n".join(sample.splitlines()[:19]) in readme, "README excerpt drifted from the file"
    assert "](examples/sample_output.json)" in readme


def test_every_in_page_link_has_its_heading():
    """A renamed heading would break the header row silently; the link check sees only URLs."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    headings = re.findall(r"^#{1,6} (.+)$", readme, re.M)
    anchors = {re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-") for h in headings}
    for anchor in re.findall(r"\]\(#([^)]+)\)", readme):
        assert anchor in anchors, f"#{anchor} points at no heading"


def test_the_readme_names_no_pinned_job_url_which_would_expire():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert not re.search(r"linkedin\.com/jobs/view/\d+", readme), (
        "a pinned job URL turns red in CI the week the posting closes"
    )
