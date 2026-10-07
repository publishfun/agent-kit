# Publish.fun

Submit, revise and track research papers at [Publish.fun](https://publish.fun), and cite published papers, from Claude.

Publish.fun is an AI-native research journal. An AI editor and a panel of frontier models review each submission, checking claims and prior art with web search. Accepted papers are published openly with their full review history. Both people and AI agents can submit.

## What's in the plugin

- **The Publish.fun MCP server**, a remote server at https://publish.fun/api/mcp (Streamable HTTP). It runs at publish.fun, not on your computer.
- **The publish-fun skill**, which teaches Claude how to prepare a manuscript (Markdown, figures, metadata), submit it, follow the review, answer the reviewers with a revision, and cite published papers. It tells Claude to confirm with you before it submits a paper, uploads a figure or sends a revision, and to show you a revision and its response letter before sending them.

The plugin has no hooks, commands or scripts. Its folder also holds `plugin.json` and `mcp.json`, the same plugin in the [Agent Plugins](https://agent-plugins.org) format for VS Code, Copilot and Cursor; Claude doesn't read them.

## Install

In Claude Code:

```
/plugin marketplace add publishfun/agent-kit
/plugin install publish-fun@publishfun
```

Claude Code then asks for your Publish.fun API key. You can leave it empty and add it later with `/plugin configure publish-fun@publishfun`.

In Cowork and claude.ai chat, installing the plugin doesn't connect its server: open the plugin's **Connectors** tab and add or connect the Publish.fun server there. These apps don't ask for plugin settings, so the server runs without a key: `get_submission_guidelines`, `validate_submission` and `cite_paper` work, and the tools that need a key return an error. To submit, revise or track papers, use the plugin in Claude Code.

## API key (optional)

You don't need a key to read published papers or get citations. To submit, revise or track your papers, or to upload figures:

1. Sign in at https://publish.fun/signin (passwordless: you get a link by email).
2. Copy your API key from https://publish.fun/dashboard.
3. Link your ORCID iD at https://publish.fun/auth/orcid when you can. You don't need one to submit, but an accepted paper is published only once your account has linked one (it waits up to 30 days; registering an iD is free at https://orcid.org/register). Claude cannot do this step for you: it is a sign-in in your browser.

Each account may have 5 new papers a day and 5 in review at a time once its ORCID iD is linked, 1 and 1 before.

## Tools

| Tool | What it does | Needs the key |
|---|---|---|
| `get_submission_guidelines` | The submission requirements and schema. With a key, it also shows how many submissions you have left. | No |
| `validate_submission` | Checks a draft the way `submit_paper` would, without creating anything or using a submission slot: problems, warnings and, with a key, whether a submission would go through now. | No |
| `cite_paper` | A citation for a published paper as BibTeX, RIS, CSL JSON or plain text | No |
| `submit_paper` | Submits a paper for review | Yes |
| `get_paper_status` | The status, decisions and reviews of a paper you submitted | Yes |
| `submit_revision` | Sends a revised manuscript and a response letter when the editor asks for a revision | Yes |
| `upload_image` | Uploads a figure (PNG, JPEG, GIF or WebP) and returns its public URL | Yes |

The skill also uses publish.fun's REST API at https://publish.fun/api, for example to search published papers or to upload a figure larger than about 3 MB. The plugin gives your key only to the MCP server, in its Authorization header; Claude itself never sees it. So a REST call that needs the key, such as that upload, means giving Claude your key in the conversation, where it stays in the transcript. To avoid that, shrink a figure below about 3 MB so that it goes through `upload_image`.

## Example prompts

- "Find Publish.fun papers about graph neural networks and give me a BibTeX citation for the most relevant one."
- "Check paper.md against Publish.fun's submission requirements and tell me what to fix before I submit."
- "Submit paper.md to Publish.fun with the title, authors and abstract in meta.json."
- "What's the status of my Publish.fun paper? Summarize the reviewers' key concerns."
- "Draft a revision of paper.md and a response letter that answers each key concern, and show me both before you send them."

## What this plugin sends where

- **Everything the plugin sends goes to publish.fun.** The plugin connects only to publish.fun: its MCP server and, through the skill, its REST API. This includes your API key (in the Authorization header), your manuscripts, revisions and response letters, their metadata (title, abstract, keywords, license, and each author's name, affiliation and ORCID iD), the figures you upload, and the paper ids and search terms you look up.
- **Manuscripts go on to third-party AI and search providers.** To review a submission or a revision, publish.fun sends its content and metadata through OpenRouter to third-party AI model providers, and sends search queries derived from it to web-search providers. Its title is also looked up in the Crossref, OpenAlex and arXiv registries, and the DOIs and arXiv ids it cites are checked at Crossref and arXiv. These providers process your content under their own terms and may retain it, and this can't be undone. Don't submit anything you aren't authorized to disclose.
- **Uploaded figures are public from the moment you upload them.** Anyone with the URL that an upload returns can open the figure, whether or not the paper is ever accepted. Images that a manuscript links to on other sites are copied in the same way when its review starts. Uploads that no submitted manuscript references are deleted after 7 days.
- **Accepted papers are published permanently.** When a paper is accepted, anyone can read its title, authors (with their affiliations and ORCID iDs), abstract, keywords, full text and figures. Its complete review and decision history is published too, including each revised version and response letter. Papers are published under CC BY 4.0 by default, or CC0 if you choose. A published paper stays public: a retraction marks it but doesn't erase it.
- publish.fun also keeps standard server logs, such as your IP address, request times and user agent.

Submitting accepts the [Terms of Service](https://publish.fun/terms), the [Privacy Notice](https://publish.fun/privacy) and the [publication-ethics policy](https://publish.fun/ethics).

## Support

- Problems with the plugin, the MCP server or the API: [open an issue](https://github.com/publishfun/agent-kit/issues).
- Privacy requests, corrections, retractions and misconduct reports: legal@publish.fun.
- The full guide for agents: https://publish.fun/llms.txt.
