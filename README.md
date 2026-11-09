# Wirex BaaS Agent Skills

Agent skills for **Wirex BaaS** — a blockchain financial services platform providing Account Abstraction wallets, KYC verification, Visa card issuance, crypto asset management, and fiat banking (SEPA/ACH) via REST APIs.

## Skills

| Skill | Description |
|-------|-------------|
| `wirex-baas-overview` | Platform introduction, environments, credentials, API basics, MCP server, supported countries |
| `wirex-baas-auth` | S2S OAuth2, Privy authentication, user token issuance, headers, token caching |
| `wirex-baas-onboarding` | Wallet deployment, user registration, 3 KYC flows, user profile, capabilities |
| `wirex-baas-crypto` | Unified balance (WUSD/WEUR), global deposit addresses, ERC20 withdrawals, ABI reference |
| `wirex-baas-cards` | Card issuance, details (PAN/CVV/PIN), limits, transactions, 3DS authentication |
| `wirex-baas-transfers` | SEPA/ACH bank transfers, Push-to-Card, recipient management |
| `wirex-baas-webhooks` | All webhook endpoints, payload formats, activity history feed |
| `wirex-baas-sandbox` | Helper API for test simulations (mint tokens, SEPA/ACH/card transactions) |

## Installation

### Claude Code

Add the marketplace and install the plugin:

```bash
/plugin marketplace add wirexapp/wirex-baas-agent-skills
/plugin install wirex-baas@wirex-baas-agent-skills
```

Or load directly from a local clone:

```bash
git clone https://github.com/wirexapp/wirex-baas-agent-skills.git
claude --plugin-dir ./wirex-baas-agent-skills
```

### OpenAI Codex

Clone and the `agents/AGENTS.md` file provides automatic skill discovery:

```bash
git clone https://github.com/wirexapp/wirex-baas-agent-skills.git
```

Or install individual skills with the built-in skill installer from within a Codex session.

### Google Gemini CLI

The `gemini-extension.json` at the repo root provides automatic discovery and MCP server integration.

### Any Agent (npx skills)

Install into any supported agent using the [skills CLI](https://github.com/vercel-labs/skills):

```bash
# Install all skills
npx skills add wirexapp/wirex-baas-agent-skills --all

# Install a specific skill
npx skills add wirexapp/wirex-baas-agent-skills --skill wirex-baas-auth

# Install to a specific agent
npx skills add wirexapp/wirex-baas-agent-skills -a claude-code --all
```

### Generic Agents (agentskills.io)

Each skill follows the [Agent Skills specification](https://agentskills.io). Skills are in `skills/`, each containing a `SKILL.md` with YAML frontmatter and a `references/` directory with detailed documentation.

### MCP Server

Wirex BaaS also provides a hosted MCP server for AI-powered editors:

```json
{
  "mcpServers": {
    "wirex-baas": {
      "url": "https://docs.wirexapp.com/mcp"
    }
  }
}
```

Works with Cursor, Windsurf, Claude Desktop, and other MCP-compatible tools.

## Documentation

Full API documentation: [docs.wirexapp.com](https://docs.wirexapp.com)

## License

Apache-2.0 — see [LICENSE](./LICENSE)
