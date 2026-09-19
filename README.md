<!-- The banner belongs here, at .github/banner.png, once it is added to the
repository. Linking it before the file exists would render a broken image on
the repository's front page. The alt text and link to restore:
[![Scrape LinkedIn data with the LinkedIn Scraper API: profiles, companies, jobs, posts. Collect or discover by URL, name and keyword. Start free.](.github/banner.png)](https://brightdata.com/products/web-scraper/linkedin?utm_source=github)
-->

# linkedin-scraper-python

[![Live check](https://github.com/brightdata/linkedin-scraper-python/actions/workflows/live.yml/badge.svg)](https://github.com/brightdata/linkedin-scraper-python/actions/workflows/live.yml)
[![last verified](https://img.shields.io/badge/last%20verified-19%20Sep%202026-brightgreen)](https://github.com/brightdata/linkedin-scraper-python/actions/workflows/live.yml) <!-- verified: rewritten by the daily run -->

[Quickstart](#quickstart) · [Command](#or-run-it-as-a-command) · [Endpoints](#the-rest-of-the-api) · [Data](#the-data) · [Errors](#when-it-fails) · [Coding agents](#coding-agents) · [Docs](https://docs.brightdata.com/products/scrapers/linkedin/introduction) · [Support](#support)

LinkedIn profiles, companies, jobs and posts as JSON, in Python. No LinkedIn
login, no browser. Built on the
[Bright Data LinkedIn Scraper API](https://brightdata.com/products/web-scraper/linkedin?utm_source=github).

Uses the [Bright Data Python SDK](https://github.com/brightdata/sdk-python).
Full API docs:
[LinkedIn Scraper API](https://docs.brightdata.com/products/scrapers/linkedin/introduction).

Also here: a one-command CLI for profiles, and the
[Bright Data CLI](#coding-agents), which needs no Python at all.

LinkedIn profile data is personal data. Use it within the law that applies to
you: [Bright Data compliance](https://brightdata.com/legal-governance).

## Quickstart

Python 3.10 or newer.

```bash
pip install brightdata-sdk
export BRIGHTDATA_API_TOKEN=YOUR_API_KEY
```

Get a token from the
[Bright Data control panel](https://brightdata.com/cp/setting/users). A `.env`
file in the project root works too, as long as the virtualenv is inside the
project.

Or skip the token. Run `npx -p @brightdata/cli bdata login` once: it opens a
browser, and from then on the SDK finds the stored credentials on its own, for
you and for any coding agent working in that terminal. Agents cannot click
through the login, so do it yourself first.

No account yet? [Create one](https://brightdata.com/cp/start); new accounts get
[5,000 free credits a month](https://docs.brightdata.com/general/account/billing-and-pricing/free-tier).

```python
from brightdata import SyncBrightDataClient

with SyncBrightDataClient(auto_create_zones=False) as client:
    profile = client.scrape.linkedin.profiles("https://www.linkedin.com/in/satyanadella/").data
    print(profile["name"], "|", profile["position"])
    print(profile["followers"], "followers,", profile["connections"], "connections")
```

```
Satya Nadella | Chairman and CEO at Microsoft
12173313 followers, 500 connections
```

Expect under a minute: the API runs a job and the SDK waits for it. One
[credit](https://brightdata.com/pricing/web-scraper) per profile.

Pass `auto_create_zones=False` every time. Left on, the SDK creates zones on
startup for Web Unlocker and SERP, two other Bright Data products this scraper
never touches, and zone creation fails on accounts without a payment method
([sdk-python#57](https://github.com/brightdata/sdk-python/issues/57)).

## Or run it as a command

The command in this repo does the same for several profiles and writes one
JSON file.

```bash
pip install git+https://github.com/brightdata/linkedin-scraper-python
linkedin-scraper satyanadella reidhoffman
```

While this repository is private, that install line works only for people with
access to it.

```
Fetching 2 LinkedIn profiles: satyanadella, reidhoffman
One job for all of them, usually one to three minutes. One credit per profile.
asking  2 profiles...

got     satyanadella: 34 fields (Satya Nadella)
got     reidhoffman: 38 fields (Reid Hoffman)

Saved 2 of 2 profiles as JSON to linkedin.json
```

It takes a profile URL just as happily as the slug inside it.

In a terminal the `asking` line is replaced by this, updating in place, so you
can see it is working and how long it has been going:

```
⠹ 2 profiles 0:00:41
```

```
--out PATH   output file, default linkedin.json
```

`python -m linkedin_scraper` works too.

Every profile you ask for goes into one job. The API bills per record, not per
job, and a job takes about the same time for one URL as for ten.

Import it instead of running it, for `ok` and `error` per profile instead of raw
rows. `scrape` never raises for one bad profile; check `ok` before reading
`profile`:

```python
from linkedin_scraper import scrape

for outcome in scrape(["satyanadella", "zz-not-a-real-profile-zz"]):
    if outcome.ok:
        print(f"{outcome.slug}: {outcome.profile['name']}")
    else:
        print(f"{outcome.slug} failed: {outcome.error}")
```

```
satyanadella: Satya Nadella
zz-not-a-real-profile-zz failed: The profile is hidden or private.
```

## The rest of the API

The command covers the first row of the table below. The rest of the SDK's
LinkedIn surface is the other rows, documented in the
[LinkedIn Scraper API docs](https://docs.brightdata.com/products/scrapers/linkedin/introduction).
Every snippet below is complete and needs only `brightdata-sdk`: paste it as
is. Every one of them runs in Actions each Monday, a smaller check runs every
other day, and the badge at the top is the latest result.

| you have | want | call |
| --- | --- | --- |
| a profile URL | that profile | `client.scrape.linkedin.profiles(url)` |
| a first and last name | matching profiles | `client.search.linkedin.profiles(first_name, last_name)`, see the note below |
| a company URL | that company | `client.scrape.linkedin.companies(url)` |
| a job URL | that job posting | `client.scrape.linkedin.jobs(url)` |
| a keyword or a location | matching job postings | `client.search.linkedin.jobs(keyword=..., location=...)`, see the note below |
| a post URL | that post | `client.scrape.linkedin.posts(url)` |
| a profile or company URL | its posts | `client.search.linkedin.posts(url, start_date=..., end_date=...)` |

`search.linkedin.profiles` takes a first and last name, not a URL. It is people
search by name. This README documents that it exists and does not demonstrate
it against a real person.

`search.linkedin.jobs` has no parameter that caps how many postings it returns,
and it bills one credit per posting. A broad keyword matches thousands. It is
not run here, because every snippet in this README reruns weekly. Narrow it with
`company`, `location` and `timeRange` before running it wide.

There is no example here built on a pinned job URL. A posting closes, and a
snippet pinned to it would turn red the week that happened.

Every one of these is an asynchronous job. The SDK triggers it, polls, and
returns when it is ready. The API's
[synchronous endpoint](https://docs.brightdata.com/api-reference/scrapers/synchronous-requests),
20 URLs and a one-minute limit, is raw HTTP only.

Error rows, like the dead profile above, appear because the SDK asks for them
with `include_errors=true`. The API default is off.

`scrape` calls with one URL return one record as a dict, and several as a list.
The `timeout` argument is seconds, 180 by default.

### Several profiles, one job

A list of URLs is one job, not one per profile.

```python
from brightdata import SyncBrightDataClient

with SyncBrightDataClient(auto_create_zones=False) as client:
    results = client.scrape.linkedin.profiles([
        "https://www.linkedin.com/in/satyanadella/",
        "https://www.linkedin.com/in/reidhoffman/",
    ])
    for result in results:
        row = result.data
        source = row.get("input_url") or row["input"]["url"]  # an error row has only input
        print(source, "|", row.get("name") or row["error"])
```

```
https://www.linkedin.com/in/reidhoffman/ | Reid Hoffman
https://www.linkedin.com/in/satyanadella/ | Satya Nadella
```

The URLs went in as satyanadella then reidhoffman, and the rows came back the
other way round. Each line is still right, because it reads the row's own
`input_url`.

Read which profile a row is from its own `input_url`, as above, never from
`result.url`. The SDK pairs results with the URLs you passed by position, and
the API returns rows in a different order each run, so `result.url` can name
one person while `result.data` holds another's profile. Every result is also
marked `success=True`, including a dead profile's error row
([sdk-python#60](https://github.com/brightdata/sdk-python/issues/60)). An error
row has no `input_url`; it names its profile in `input["url"]`.

### Trigger now, fetch later

For anything bigger than a few profiles, do not block a process for an hour.
Trigger, keep the snapshot id, fetch when ready. Snapshots stay downloadable
for 30 days.

```python
import time

from brightdata import SyncBrightDataClient

with SyncBrightDataClient(auto_create_zones=False) as client:
    job = client.scrape.linkedin.profiles_trigger("https://www.linkedin.com/in/satyanadella/")
    print("snapshot:", job.snapshot_id)
    while (status := client.scrape.linkedin.profiles_status(job.snapshot_id)) not in ("ready", "failed"):
        time.sleep(5)
    print("status:", status)
    record = client.scrape.linkedin.profiles_fetch(job.snapshot_id)[0]
    print("fetched:", record["name"], "|", record["current_company_name"])
```

```
snapshot: sd_mu717o9x2md4afafsv
status: ready
fetched: Satya Nadella | Microsoft
```

### A company

```python
from brightdata import SyncBrightDataClient

with SyncBrightDataClient(auto_create_zones=False) as client:
    company = client.scrape.linkedin.companies("https://www.linkedin.com/company/bright-data/").data
    print(company["name"], "|", company["employees_in_linkedin"], "employees on LinkedIn")
```

```
Bright Data | 407 employees on LinkedIn
```

## The data

The fields most people want from a profile:

```
name  position  city  current_company_name  followers  connections  experience
```

The code hardcodes no field list. Whatever the API returns lands in
`result.data`, and in the command's file.

The API marks 8 of these fields as personal data, with `pii: true` in the
schema: `id`, `name`, `about`, `url`, `input_url`, `linkedin_id`, `first_name`
and `last_name`.

`get_metadata()` drops that flag. It keeps `type`, `active`, `required` and
`description` for each field and discards the rest
([sdk-python#61](https://github.com/brightdata/sdk-python/issues/61)). To read
it, request `https://api.brightdata.com/datasets/gd_l1viktl72bvl7bjuj0/metadata`
yourself with the same token. The table below does that.

<!-- fields:start -->
<details>
<summary>All 46 fields, with type and description</summary>

Regenerated every day from the dataset schema, via the raw metadata
endpoint, so it cannot go stale. A
profile carries the fields that apply to it: the sample file has 32
of these 46, plus `timestamp` and `input`,
which the schema does not list.

| field | type | description |
| --- | --- | --- |
| `id` | text | Personal data. A unique identifier for the person's LinkedIn profile |
| `name` | text | Personal data. Profile name |
| `city` | text | Geographical location of the user |
| `country_code` | text | Geographical location of the user |
| `position` | text | The current job title or position of the profile |
| `about` | text | Personal data. A concise profile summary. In some cases, only a truncated version with "…" is displayed on the website, and this is the version we capture |
| `posts` | array | Contains information related to the user's last LinkedIn posts. It typically includes the post title, created date, URL link to the post, etc. |
| `groups` | array | The LinkedIn groups that the profile is a part of |
| `current_company` | object | Provides information about the user's current professional position. It typically includes the company name, the user's job title, the company ID, and the industry or sector to which the company belongs |
| `experience` | array | Contains information about user's professional history. It typically includes the user's job title, length of time the user held the position, the geographic location of the company, the start and end date, the company name, URL link to the company profile, etc. |
| `url` | url | Personal data. URL that link directly to the LinkedIn profile |
| `people_also_viewed` | array | Provides a list of LinkedIn profiles that users who have viewed the user's profile, have viewed these as well |
| `educations_details` | text | Provides information about the user's educational background |
| `education` | array | Provides information about the user's educational background. It typically includes the degree, the start and end year, the filed, etc. |
| `recommendations_count` | number | A numeric count of the total number of recommendations that the user has received |
| `avatar` | url | URL that link to the profile picture of the LinkedIn user |
| `courses` | array | Contains information about courses or educational programs that the user has undertaken |
| `languages` | array | Contains information about the user's proficiency in different languages |
| `certifications` | array | Licenses & Certifications |
| `recommendations` | array | Recommendations that the user has received from their connections or colleagues on LinkedIn |
| `volunteer_experience` | array | Contains information related to the user's volunteer work |
| `followers` | number | How many users/ companies following the profile |
| `connections` | number | How many connections the profile has |
| `current_company_company_id` | text | The id of the latest/current company of the profile |
| `current_company_name` | text | The name of the latest/current company of the profile |
| `publications` | array | Published works or presentations |
| `patents` | array | Patents filed or granted |
| `projects` | array | Professional or academic projects |
| `organizations` | array | Memberships in professional organizations |
| `location` | text | Geographical location of the user |
| `input_url` | url | Personal data. The URL that was entered when starting the scraping process |
| `linkedin_id` | text | Personal data. LinkedIn profile identifier |
| `activity` | array | Any activity the user has regarding posts |
| `linkedin_num_id` | text | Numeric LinkedIn profile ID |
| `banner_image` | url | Banner image |
| `honors_and_awards` | array | Awards and recognitions received |
| `similar_profiles` | array | Profiles similar to the current one |
| `default_avatar` | boolean | Is the avatar picture the default avatar empty picture |
| `memorialized_account` | boolean | Boolean indicating if the account is memorialized |
| `bio_links` | array | External links added to the bio |
| `first_name` | text | Personal data. First name of the user |
| `last_name` | text | Personal data. Last name of the user |
| `urn_id` | text | The Uniform Resource Name (URN) used by LinkedIn |
| `urn` | text | Uniform Resource Name |
| `influencer` | boolean | Indicator if the profile marked as influencer |
| `fsd_profile_id` | text | FSD profile ID |

</details>
<!-- fields:end -->

<details>
<summary>The start of a real output file, from <code>linkedin-scraper satyanadella</code></summary>

```json
{
  "generated_at": "2026-09-18T14:15:08.047993+00:00",
  "profiles": [
    {
      "slug": "satyanadella",
      "profile": {
        "id": "satyanadella",
        "name": "Satya Nadella",
        "city": "Redmond, Washington, United States",
        "country_code": "US",
        "position": "Chairman and CEO at Microsoft",
        "about": "As chairman and CEO of Microsoft, I define my mission and that of my company as empowering every person and every organization on the planet to achieve more.",
        "posts": [
          {
            "title": "How do we build a frontier intelligence ecosystem?",
            "attribution": "Great to be back at Microsoft Build today. For us, it is not about any one piece of technology or even the platform.",
            "img": "https://media.licdn.com/dms/image/v2/D560DAQHI1Iu8CrO8CQ/learning-public-crop_288_512/B56ZvrnmmhJ8AQ-/0/1769184586791?e=2147483647&v=beta&t=IZT3h7JK8tLoX5KYgwA0xLjxIKtc14hmHqKCk1cOLP8",
            "link": "https://www.linkedin.com/pulse/how-do-we-build-frontier-intelligence-ecosystem-satya-nadella-73jhc",
            "created_at": "2026-06-02T00:00:00.000Z",
  ...
```

The whole file, one profile with every field, is
[examples/sample_output.json](examples/sample_output.json).

</details>

## When it fails

| you see | what it means |
| --- | --- |
| `API token required but not found.` | Exit 2, before any request. Set the token. |
| `failed  slug: The profile is hidden or private.` | Exit 1. No such profile, or not public. Usually a typo in the slug. |
| `failed  slug: the API returned no row for this profile` | Exit 1. The job came back without a row for that input. Run it again. |
| `failed  slug: timeout` | Exit 1. A request gives up after 180 seconds. Run it again. |
| `failed  slug: Failed to fetch results: Request timeout after 30 seconds` | Exit 1. The job finished, but downloading it took longer than 30 seconds. Run it again. |
| `failed  slug: Crawler error: Your system is sending too many of this type of request. ...` | Exit 1. The account is being throttled, and a valid profile fails with it. Wait, then run it again. It clears on its own. |

Any failure exits 1, so a run is safe to gate a script on.

From the SDK, the same conditions look like this:

| you see | what it means |
| --- | --- |
| `AuthenticationError: Unauthorized (401)` | The token is set but wrong. |
| `result.success` is `False`, `result.status` is `"timeout"` | The SDK gave up waiting for the job, 180 seconds by default. Pass `timeout=420` to the call, or run it again. |
| `Failed to fetch results: Request timeout after 30 seconds` | The job finished; downloading it did not. That is the client's own limit on each HTTP request, `SyncBrightDataClient(timeout=30)`, not the `timeout` you pass to the call. Raising the call's `timeout` does not help. Run it again, or pass a larger `timeout` to the client. |
| a dict in `result.data` with an `error` key | The API's answer for one input. `result.success` still says `True`; read the row. |

## Coding agents

No Python, nothing installed. Paste both lines; the first opens a browser
once, or use `bdata login --device` over SSH and in CI:

```bash
npx -p @brightdata/cli bdata login
npx -p @brightdata/cli bdata pipelines linkedin_person_profile "https://www.linkedin.com/in/satyanadella/"
```

`bdata pipelines list` prints every type. The LinkedIn ones are
`linkedin_person_profile`, `linkedin_company_profile`, `linkedin_job_listings`,
`linkedin_posts` and `linkedin_people_search`. Each takes URLs, prints JSON,
and costs one credit per record.

`npx skills add brightdata/skills` teaches Claude Code, Cursor and Codex these
commands and the docs, so plain language works afterwards. Full guide:
[Bright Data for your coding agent](https://docs.brightdata.com/quickstart-coding-agent).

No terminal, for a hosted assistant? The
[Bright Data MCP server](https://github.com/brightdata/brightdata-mcp#which-tool-to-use)
has LinkedIn tools in its `social` group, which is off unless you ask for it:

    https://mcp.brightdata.com/mcp?token=YOUR_API_TOKEN&groups=social

An agent can also open the account itself, no signup form:
[agent registration](https://brightdata.com/auth.md). Everything else Bright
Data connects to, from LangChain to Zapier and n8n:
[integrations](https://docs.brightdata.com/integrations/introduction).

## Support

Bugs in this repo:
[open an issue](https://github.com/brightdata/linkedin-scraper-python/issues).
Anything about the API, your account or your credits:
[Bright Data support](https://brightdata.zendesk.com/hc/en-us/requests/new).

## License

MIT.
