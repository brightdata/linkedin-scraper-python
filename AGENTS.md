# For coding agents working in this repository

Read this before changing anything. Every line below was verified against the
live API or the installed SDK, `brightdata-sdk` 2.5.2, on 2026-09-18. Several
lines contradict the SDK's own behaviour or docstrings.

## What this repository may demonstrate

LinkedIn profile data is personal data. The API says so itself: of the 46 fields
in the profiles dataset it marks 8 with `pii: true`, namely `id`, `name`,
`about`, `url`, `input_url`, `linkedin_id`, `first_name` and `last_name`.

- Examples use public figures whose professional presence is already public,
  and company pages. Do not add an example that scrapes a private individual.
- Do not add an example built on `search.linkedin.profiles`. It searches by
  first and last name, which is people search.
- Permitted use is the customer's responsibility, and the README links to Bright
  Data's compliance material rather than restating it here.

## Auth

- The SDK reads `BRIGHTDATA_API_TOKEN` from the environment, from a `.env` file
  found by searching upward from its own install folder (so the project root,
  when the virtualenv is inside the project), or from the Bright Data CLI login.
  The JavaScript twin does not read `.env` at all; do not copy its wording here.
- Always construct the client as `SyncBrightDataClient(auto_create_zones=False)`.
  Left on, the SDK creates Web Unlocker and SERP zones on startup, which this
  repository never uses, and zone creation fails without a payment method.

## How the API behaves

- Every call is an asynchronous job: trigger, poll, fetch. Profiles took 13 s to
  64 s on 2026-09-18.
- `timeout` is seconds, 180 by default. The JavaScript twin's `pollTimeout` is
  milliseconds. A number copied across is off by a thousand.
- LinkedIn lives on `client.scrape.linkedin` for URLs and on
  `client.search.linkedin` for name, keyword and date searches. The JavaScript
  SDK has no `search.linkedin`; there, both are `discover*` methods on
  `scrape.linkedin`.
- The profiles dataset is `gd_l1viktl72bvl7bjuj0`, the id the control panel shows.
- A list of URLs is one job. The API bills per record, not per job.

### The SDK mislabels list results

This is the one to remember. With a list of URLs, `_scrape_urls` pairs rows with
inputs by position:

    for url_item, data_item in zip(url_list, result.data):
        ScrapeResult(success=True, data=data_item, url=url_item, ...)

The API returns rows in a different order on each run. Measured on 2026-09-18
with three inputs, the result labelled `reidhoffman` held a dead profile's error
and the result labelled with the dead slug held Reid Hoffman's profile.

- Never read `ScrapeResult.url` on list input. Match a row to its input on the
  row's own `input_url`, or `input["url"]` for an error row, which has no
  `input_url`. `attribute()` in `src/linkedin_scraper/scrape.py` does this.
- `success` is always `True` on list results, error rows included. Read the row.
- If fewer rows come back than inputs, `zip` drops the rest in silence.
- On failure or timeout the method returns one `ScrapeResult`, not a list, even
  for list input.
- The same `zip` is in the amazon, facebook, instagram, pinterest and tiktok
  scrapers. Tracked in [sdk-python#60](https://github.com/brightdata/sdk-python/issues/60).

### Error rows

- They arrive because the executor sends `include_errors=True`. The API default
  is off.
- A dead profile: `The profile is hidden or private.`
- A throttled account: `Crawler error: Your system is sending too many of this
  type of request. If you need to send more, contact your Account Manager`.
  Valid profiles fail with this too. Seen on 2026-09-18 after many profile calls
  in a short window. Wait before running again.
- Match on the message, not `error_code`.

### Things that cost money

- `search.linkedin.jobs` has no parameter that caps rows, and never sends
  `limit_per_input`. It bills one credit per posting, and a broad keyword
  matches thousands. The README does not run it for that reason, because every
  README block reruns weekly. A test pins the missing parameter, so it fails the
  day a cap is added.
- It accepts a keyword with no location. The JavaScript twin requires `location`.
- Never pin a job URL in the README. A posting closes and the weekly check goes
  red through no fault of the code.

### The schema

- Never hardcode a field list. The API also returns `timestamp` and `input`,
  which the schema does not list.
- `client.datasets.linkedin_profiles.get_metadata()` returns `fields` as a dict,
  but drops `pii`: each `DatasetField` keeps only `type`, `active`, `required`
  and `description`. Read the flag from the raw endpoint,
  `https://api.brightdata.com/datasets/gd_l1viktl72bvl7bjuj0/metadata`, as the
  field-table step in `live.yml` does. Tracked in
  [sdk-python#61](https://github.com/brightdata/sdk-python/issues/61).
- The full documentation index, one `.md` page per entry:
  https://docs.brightdata.com/llms.txt

### The Bright Data CLI

The LinkedIn pipelines are `linkedin_person_profile`, `linkedin_company_profile`,
`linkedin_job_listings`, `linkedin_posts` and `linkedin_people_search`. There is
no `linkedin_profiles`. Run `bdata pipelines list` rather than guessing a name.

## The API stalls in waves

On 2026-09-16 the API went through stretches of roughly an hour where most jobs
sat until the poll deadline and returned `status: "timeout"` with no rows.
Between those stretches the same calls finished in about a minute. Load did not
explain it. A red live check whose only symptom is timeouts is probably a bad
wave: rerun it before looking for a code change.

## Working here

- `pytest` runs offline and needs no token. `ruff check .` must pass.
- CI installs from the README's own commands on an empty machine. A weekly
  workflow executes every fenced block in the README against the real API, and
  a daily one runs a smaller live check.
- The field table sits between `<!-- fields:start -->` and `<!-- fields:end -->`
  and is regenerated daily. Do not edit it by hand.
- The "last verified" badge line is rewritten by the daily run. Do not edit it.
- Keep it small: 14 files and about 300 lines of Python. Do not add retries,
  deduplication, scheduling, databases, async examples or concurrency.
