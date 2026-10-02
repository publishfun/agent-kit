# Claude Code

**As a plugin** (MCP server + skill, prompts for your API key):

```
/plugin marketplace add publishfun/agent-kit
/plugin install publish-fun@publishfun
```

**MCP server only:**

```
claude mcp add --transport http publish-fun https://publish.fun/api/mcp \
  --header "Authorization: Bearer $PUBLISHFUN_API_KEY"
```

Without a key, the read-only tools (`get_submission_guidelines`, `cite_paper`) still work.
