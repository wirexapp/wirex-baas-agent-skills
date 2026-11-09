# Wirex BaaS MCP Server Setup

The Wirex BaaS Model Context Protocol (MCP) server lets AI development tools interact directly with the Wirex BaaS API and documentation. MCP is an open standard that allows AI applications to securely access external data sources and tools.

**MCP Server URL:** `https://docs.wirexapp.com/mcp` (a remote MCP server hosted by Wirex)

The docs describe it for AI code editors such as Cursor and Windsurf, plus general-purpose tools like Claude Desktop.

---

## What the MCP Server Provides

| Capability | Description |
|---|---|
| **Direct API access** | Access to Wirex BaaS functionality from your AI tool. |
| **Documentation search** | Search across the Wirex BaaS documentation. |
| **Real-time data** | Real-time data from your Wirex BaaS account. |
| **Code generation assistance** | Help generating Wirex BaaS integration code. |

---

## Setup Instructions

All three documented tools use the same JSON config:

```json
{
  "mcpServers": {
    "wirex-baas": {
      "url": "https://docs.wirexapp.com/mcp"
    }
  }
}
```

### Configuration File Locations

| Tool | Config File |
|------|------------|
| **Cursor** | `~/.cursor/mcp.json` |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` |
| **Claude Desktop** | `claude_desktop_config.json` |

If your APIs require authentication, you can pass headers via query parameters or however headers are configured in your MCP client.

---

## Testing the Connection

1. Open your AI editor (Cursor, Windsurf, etc.).
2. Start a new chat with the AI assistant.
3. Ask about Wirex BaaS, for example:
   - "How do I [common use case]?"
   - "Show me an example of [API functionality]"
   - "Create a [integration type] using Wirex BaaS"

The AI should now have access to your Wirex BaaS account data and documentation through the MCP server.

---

## Agent Skills

Wirex also publishes this skillset (Agent Skills specification) for AI agents. Repository: `https://github.com/wirexapp/wirex-baas-agent-skills`.

| Agent | Install |
|---|---|
| **Claude Code** | `/plugin marketplace add wirexpay/wirex-baas-agent-skills` then `/plugin install wirex-baas@wirex-baas-agent-skills`; or `claude --plugin-dir ./wirex-baas-agent-skills` from a local clone |
| **OpenAI Codex** | Clone the repository; `agents/AGENTS.md` provides skill discovery |
| **Google Gemini CLI** | `gemini-extension.json` at the repo root provides discovery and MCP server integration |
| **Any agent (npx skills)** | `npx skills add wirexpay/wirex-baas-agent-skills --all` (or `--skill wirex-baas-auth`, or `-a claude-code --all`) |

Skills live in `skills/wirex-baas-{name}/` with a `SKILL.md` (YAML frontmatter) and a `references/` directory.
