---
name: publish-fun
description: Submit, revise and track a research paper at Publish.fun, the AI-reviewed research journal, through its REST API or MCP server, and cite published Publish.fun papers. Use when the user wants to publish a paper there, check its review status, answer reviewer concerns with a revision, upload figures for it, or get a citation for a Publish.fun paper.
---

# Publish.fun

Publish.fun (https://publish.fun) is an AI-native research journal. An AI editor and a panel of frontier models review each submission, checking claims and prior art with web search, and accepted papers are published openly (CC BY 4.0 by default) with their full review history.

The complete guide is https://publish.fun/llms.txt; everything, every schema included, is in one file at https://publish.fun/llms-full.txt. This skill is the short path through it.

## Before submitting

1. The person you act for needs an account and an API key: they sign in at https://publish.fun/signin and copy the key from https://publish.fun/dashboard. Never invent a key or use someone else's. No ORCID iD is needed to submit, but an accepted paper is published only once that account has linked one (see "ORCID iD" below), so tell them early.
2. Submitting accepts the Terms (https://publish.fun/terms), the Privacy Notice (https://publish.fun/privacy) and the publication-ethics policy (https://publish.fun/ethics). The manuscript is sent to third-party AI model and web-search providers for review and, if accepted, published publicly and permanently with its reviews. Confirm with the person before you submit, and before you upload any figure, since an uploaded image is public at once (see Figures below).
3. Only genuine, novel research is accepted; work already published in a journal or proceedings is desk-rejected. Limits: 5 new papers a day and 5 in review at a time per account (1 paper a day and 1 in review at a time until the account links its ORCID iD); the day window counts every submission whatever its outcome, and a paper in review holds an in-flight slot until its decision.

## Prepare the manuscript

- The body is GitHub-Flavored Markdown: `$...$` and `$$...$$` math, GFM tables, `![caption](url)` figures, 200 to 150,000 characters. The API and MCP do not take LaTeX; convert it first, for example `pandoc -f latex -t gfm paper.tex -o paper.md`.
- Figures: upload each image (PNG, JPEG, GIF or WebP, at most 10 MB) with `POST https://publish.fun/api/uploads/images` (multipart/form-data, one `file` part) or the MCP `upload_image` tool, and use the URL it returns. An https image hosted elsewhere is copied into the article when review starts. An uploaded image is public as soon as it is uploaded: anyone with the link can open it, before any review and whether or not the paper is ever accepted, so upload only images that may be made public. Copies of images referenced at other hosts or embedded inline are public in the same way once the paper enters review.
- Metadata goes in the fields, not in HTML comments: `title` (3 to 300 characters), `authors` (1 to 20 `{ name, affiliation?, orcid? }`), `abstract` (50 to 3000 characters), and optionally `keywords` (up to 20) and `license`, which is `CC-BY-4.0` (default) or `CC0-1.0`. With more than one author, `coauthorsConfirmed: true` is required: it states that every co-author consented.

## Check, then submit

- Check first: `POST https://publish.fun/api/papers/validate` or the MCP `validate_submission` tool, with the same body as a submission. It creates nothing and uses no slot. Fix every `problems` entry (submit would refuse them); read the `warnings`. With the key, `readiness.ready_to_submit` says whether a submission would be accepted right now and `readiness.identity` whether an accepted paper would publish at once.
- In order: validate the draft, upload the figures and use their URLs, validate again with the key, submit, poll, and if the status becomes `accepted` hand the operator the ORCID link.
- REST: `POST https://publish.fun/api/papers/submit` with `Authorization: Bearer <API_KEY>` and the JSON body above. A 202 returns `{ id, status, status_url, submission_allowance, identity }`; `identity.orcid_verified` says whether an accepted paper will publish at once or wait.
- MCP: connect to `https://publish.fun/api/mcp` (Streamable HTTP, protocol revision 2025-06-18) with the same `Authorization` header and call `submit_paper` with the same fields.

## Follow the review

Poll `GET https://publish.fun/api/papers/<id>` with the key, or call the MCP `get_paper_status` tool. A review round can take from about a minute to more than an hour: the first round, with the full reviewer panel and its web searches, usually takes longest, and a busy queue adds waiting time. Poll every few minutes rather than in a tight loop. Statuses: submitted, desk_reviewing, under_review, editor_deciding, then revision_requested, accepted, published, rejected, desk_rejected or lapsed (failed means a pipeline error). A published paper gets a permanent id such as `PF-260626.000001`.

## ORCID iD

No ORCID iD is needed to submit. An ACCEPTED paper is published only once the submitting account has linked a verified ORCID iD; it waits up to 30 days (reminders go to the account's email), then lapses unpublished. Linking is a browser step only the person who owns the account can do: they sign in and open https://publish.fun/auth/orcid. An agent cannot do it: give your operator that link, and if they have no ORCID iD tell them to register one free at https://orcid.org/register first (about a minute). Until the iD is linked the account submits under the smaller allowance. GET https://publish.fun/api/me (or get_paper_status on a held paper) shows whether it is linked. When a paper's status is `accepted`, its record carries `next_step` and `identity`: relay `identity.link_url` (and `identity.register_url` if they have no iD) to the person you act for, then keep polling; the status turns `published` once they have linked it, or `lapsed` if the hold ran out.

## Revise

When the status is `revision_requested`, read the decision's `summary_to_authors` and `key_concerns`, revise the manuscript, and write a response letter. Structure the response letter by concern: for each concern in the decision's key_concerns, quote it, then say what changed and where (the section of the revised manuscript), or explain why it was not changed. Reviewers verify each concern against the revised manuscript, not the letter alone.

Before you send a revision, show the person the revised manuscript and the response letter, and send it only with their OK, as for the first submission: a revision also goes to third-party AI model providers for review (and to web-search providers when its reviewers search the web again), and if the paper is accepted, every round's manuscript and response letter are published with it.

Send the full revised body with the letter: `POST https://publish.fun/api/papers/<id>/revisions` with `{ "content": ..., "response_letter": ... }` (optionally a new `title`, `abstract` or `keywords`), or the MCP `submit_revision` tool. Each revision starts a new review round (one revision per round), and rounds are limited: a paper gets at most 6 review rounds in all, the first submission included. The full revision policy is in https://publish.fun/llms.txt.

## Read and cite published papers (no key needed)

- Search with `GET https://publish.fun/api/papers?q=<terms>`. A paper's record, reviews included, is `GET https://publish.fun/api/papers/<PF-id>`; its body as Markdown is `https://publish.fun/papers/<PF-id>/content.md`.
- Cite with `GET https://publish.fun/api/cite/<PF-id>?format=bibtex` (or `ris`, `csl`, `text`), or the MCP `cite_paper` tool. Retracted papers stay listed and are marked as retracted; cite them as such.
