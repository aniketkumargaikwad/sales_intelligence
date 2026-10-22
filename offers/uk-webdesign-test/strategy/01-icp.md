---
offer: uk-webdesign-test
doc: icp
generated_on: 2026-10-22
offer_yaml_hash: "60a51fc02f83"
sources: [offer.yaml, context/README.md]
---

# Ideal customer profile: Northlight Studio

## Who buys

**Physiotherapy clinics in England (segment `physio_england`).** Independent clinics with 1–15
staff, usually one owner-physio plus associates, a receptionist or practice manager, and one or two
treatment rooms per site. Bookings come from Google searches, GP and word-of-mouth referrals, and
insurers' directories. The website was usually built cheaply years ago, is slow on a phone, and
hides the booking link (often a third-party booking system such as Cliniko or Jane) below the
fold. Northlight replaces "my nephew built it" or a dated template.

**Independent dental practices in England (segment `dental_england`).** Private or mixed
practices with 1–20 staff, owned by a principal dentist. They compete on private treatments
(hygiene, whitening, implants, Invisalign) where the website does the selling. Same problems:
slow mobile pages, no clear "book" path, treatment pages that read like a price list.

Both segments buy a one-off site (£1,800 per site, £900 deposit) when the owner can see that the
current site is losing bookings.

## Must have

| Test | How we detect it | Source |
|---|---|---|
| Independent, not part of a national group | No group branding or "part of X" in the footer; not on our exclusion list of groups | Clinic website, Google listing |
| Has a website we can audit | Website field on the listing resolves and returns a page | Google Places, the site itself |
| Limited company or LLP (PECR corporate subscriber) | Company number on the site or a matching active company at the clinic's address | Companies House API |

If the company check can't find a match, treat the clinic as a sole trader: **blocked** for cold
email (see 06-channel-plan).

## Nice to have

| Signal | How we detect it | Source |
|---|---|---|
| No visible booking button on the homepage | No link to a booking system or "book" CTA in the first screen | Crawl of the homepage |
| Fails Google's mobile performance check | PageSpeed Insights mobile performance score below 50 (assumption: threshold to tune) | PageSpeed Insights API |
| Well reviewed | 4.5+ rating with 50+ reviews | Google Places |

## Disqualifiers

- Site rebuilt in the last 18 months: copyright year, a "new website" post, or a modern
  site builder theme with good performance scores.
- Marketing run centrally by a parent group (group domain, group booking engine).
- Sole trader or partnership: PECR requires prior consent for cold email to individual
  subscribers, so we never cold email them.
- Clinics inside hospitals or NHS trusts (excluded in offer.yaml).

## Signals to watch

| Signal | Why it predicts buying | Fresh for |
|---|---|---|
| Hiring a practice manager or receptionist | Growth or turnover; a new manager often reviews the "front door" | 30 days from the job post |
| Opened a new location | Needs location pages and a booking path per site | 90 days |
| Practice changed owner | New owners rebrand and refresh the website | 180 days |

## Where to find them

- **Google Places (New) Text Search** for "physiotherapy clinic" / "dentist" by town across
  England, within the free monthly caps (offer budget is $30/month; no paid data).
- **Companies House API** (free key) to confirm Ltd/LLP and find the directors' names.
- **Professional registers** for sanity checks: CSP's physio finder and the GDC register
  (lookup only; we don't scrape them in bulk).
- No Google Maps scraping (off by default, ToS risk).
