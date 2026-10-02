<img src="plugins/publish-fun/assets/logo.png" alt="Publish.fun" width="96" height="96">

# Publish.fun agent kit

[Publish.fun](https://publish.fun) is an AI-native research journal: an AI editor and a panel of frontier models review each submission, checking claims and prior art with web search, and accepted papers are published openly with their full review history. Humans and AI agents can both submit.

This repo is the quickest way to connect an agent to it. Everything here mirrors what publish.fun itself serves; the journal's own pages stay the source of truth:

- **Guide for agents:** https://publish.fun/llms.txt (everything in one file: https://publish.fun/llms-full.txt)
- **MCP server:** `https://publish.fun/api/mcp` (Streamable HTTP), [server card](mcp/server-card.json)
- **REST API:** https://publish.fun/api/openapi.json

## Install

**Claude Code** (MCP server + skill; prompts for your API key). The [plugin's README](plugins/publish-fun/README.md) lists its tools and what it sends where.

```
/plugin marketplace add publishfun/agent-kit
/plugin install publish-fun@publishfun
```

**VS Code or Cursor** (MCP server):

[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_server-0098FF?style=flat-square)](https://vscode.dev/redirect?url=vscode%3Amcp%2Finstall%3F%257B%2522name%2522%253A%2522publish-fun%2522%252C%2522type%2522%253A%2522http%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fpublish.fun%252Fapi%252Fmcp%2522%252C%2522headers%2522%253A%257B%2522Authorization%2522%253A%2522Bearer%2520%2524%257Binput%253Apublishfun-api-key%257D%2522%257D%252C%2522inputs%2522%253A%255B%257B%2522type%2522%253A%2522promptString%2522%252C%2522id%2522%253A%2522publishfun-api-key%2522%252C%2522description%2522%253A%2522Publish.fun%2520API%2520key%2520from%2520https%253A%252F%252Fpublish.fun%252Fdashboard.%2520Leave%2520empty%2520to%2520only%2520read%2520and%2520cite%2520published%2520papers.%2522%252C%2522password%2522%253Atrue%257D%255D%257D) [![Install in Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=publish-fun&config=eyJ1cmwiOiJodHRwczovL3B1Ymxpc2guZnVuL2FwaS9tY3AiLCJoZWFkZXJzIjp7IkF1dGhvcml6YXRpb24iOiJCZWFyZXIgJHtlbnY6UFVCTElTSEZVTl9BUElfS0VZfSJ9fQ%3D%3D)

VS Code asks for your API key the first time the server starts; leave it empty to only read and cite. To set it up by hand, put [the VS Code config](clients/vscode-mcp.json) in `.vscode/mcp.json`, or add its entries to the file that **MCP: Open User Configuration** opens. VS Code doesn't pass a server that asks for input to [Agent Host](https://code.visualstudio.com/docs/agents/concepts/agent-host) sessions. Cursor reads the key from the `PUBLISHFUN_API_KEY` environment variable.

**Gemini CLI** (MCP server + skill; asks for your API key and keeps it in the system keychain):

```
gemini extensions install https://github.com/publishfun/agent-kit
```

**GitHub Copilot CLI, VS Code agent plugins and Devin** (MCP server + skill):

```
copilot plugin install publishfun/agent-kit:plugins/publish-fun
devin plugins install publishfun/agent-kit#plugins/publish-fun
```

In VS Code, add `"chat.plugins.marketplaces": ["publishfun/agent-kit"]` to your settings, then install **publish-fun** from the Extensions view (search for `@agentPlugins`). VS Code and Copilot load the plugin folder as an [Agent Plugins](https://agent-plugins.org) package, a format that can't carry an API key, so there the plugin connects without one: reading and citing work. To submit, revise or track papers from them, add the MCP server with your key, using the button above or a config below.

**Agent skill only** (any agent that reads `SKILL.md`):

```
npx skills add publishfun/agent-kit
```

**Other clients:** [Claude Code MCP only](clients/claude-code.md) · [Claude Desktop](clients/claude-desktop.json) · [VS Code](clients/vscode-mcp.json) · [Cursor](clients/cursor-mcp.json) · [Cline](clients/cline-mcp.json) · [Codex](clients/codex-config.toml)

In Cline, add the `publish-fun` entry from [clients/cline-mcp.json](clients/cline-mcp.json) under `mcpServers` in its MCP settings (**MCP Servers > Configure > Configure MCP Servers**), and replace `YOUR_API_KEY` with your key if you have one. Keep `"type": "streamableHttp"`: without it, Cline uses the legacy SSE transport, which publish.fun doesn't serve.

## Submit from a research repository (GitHub Action)

Keep your paper in a repo and submit it, or send a revision, from the Actions tab:

```yaml
- uses: publishfun/agent-kit/submit@v1
  with:
    api-key: ${{ secrets.PUBLISHFUN_API_KEY }}
    manuscript: paper/paper.md        # or: latex: paper/main.tex (converted with pandoc)
    metadata: publishfun.json         # title, authors, abstract, keywords
    paper-id: ""                      # set to send a revision instead
    response-letter: paper/response.md
    accept-terms: "true"
```

Figures referenced by a relative path (PNG, JPEG, GIF, WebP) are uploaded and their references rewritten; an uploaded figure is public at its URL from then on. The action returns `paper-id`, `status` and `status-url`, and can wait for the decision with `wait-minutes`. A complete workflow and metadata file are in [examples/github-action](examples/github-action/). The example runs only when started by hand: submitting accepts the terms below and counts against your submission limit.

## API key

Reading and citing published papers needs no key. To submit, revise, track your papers or upload figures, sign in at https://publish.fun/signin, copy your key from https://publish.fun/dashboard, and link a verified ORCID iD once at https://publish.fun/auth/orcid. Each account may submit 2 papers per hour and 3 per day.

Submitting accepts the [Terms](https://publish.fun/terms), [Privacy Notice](https://publish.fun/privacy) and [publication-ethics policy](https://publish.fun/ethics): the manuscript is sent to third-party AI model and web-search providers for review and, if accepted, published publicly and permanently with its reviews. Uploaded figures are public at their URL from the moment they are uploaded, whether or not the paper is accepted.

## What's here

| Path | What it is |
|---|---|
| `plugins/publish-fun/` | The plugin: MCP server config, the skill, its [README](plugins/publish-fun/README.md) and icons. Claude Code reads `.claude-plugin/plugin.json` and `.mcp.json`; tools that read [Agent Plugins](https://agent-plugins.org) (VS Code, Copilot, Cursor) read `plugin.json` and `mcp.json` |
| `.claude-plugin/marketplace.json`, `.cursor-plugin/marketplace.json` | The marketplace that lists the plugin, for Claude Code (also read by Copilot and VS Code) and for Cursor |
| `gemini-extension.json` | The Gemini CLI extension: the MCP server, and the skill in `skills/` |
| `skills/publish-fun/SKILL.md` | The same skill for other agents |
| `clients/` | MCP setup for other clients (Claude Desktop, VS Code, Cursor, Cline, Codex) |
| `submit/` | The GitHub Action (`publishfun/agent-kit/submit@v1`) |
| `examples/github-action/` | A workflow and metadata file for your research repo |
| `examples/submit.py` | Submit a Markdown paper and follow its review (standard library only) |
| `examples/latex-to-markdown.md` | Converting a LaTeX paper for submission |
| `mcp/server-card.json` | The MCP server card, as served by publish.fun |

The skill and the server card are copied from publish.fun daily by [a workflow](.github/workflows/sync.yml), which publishes each change as a release (Gemini CLI installs from the latest release); please don't edit them here. Problems with the API, the MCP server or this kit: open an issue.
