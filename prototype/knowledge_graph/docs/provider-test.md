# First consumer-provider test

Status: six frozen cases collected and scored through actual Claude Desktop
consumer Chat. See [results and failures](claude-provider-results.md). Local
MCP subprocess tests remain separate from the consumer-provider results.

## Confirmed setup

Claude Desktop is installed and signed in on the Free plan. On September 6,
2026, its UI displayed version `1.46388.4`, Chat mode, `Sonnet 5 Medium`, and
Developer > Local MCP servers > `No servers added`. These are observed UI
labels, not proof of an underlying model snapshot or future availability.

Chrome's browser-harness route required remote-debugging consent and was not
used to collect data. Native Claude inspection provided the local MCP option.

## Consent boundary

The user's "continue" after the explicit setup request approved adding the
`drayage-kg-prototype` entry and restarting Claude. That setup is complete.
Every unrelated config field was preserved and compared with a recoverable
backup before restart. Developer settings showed the server `Running`.
Future changes to hosting, permissions, spend or data scope still need their
own authorization; this approval covered only the described local test.

The proposed server starts a local Python subprocess. It exposes only two
read-only tools, cannot execute arbitrary shell/graph queries or read caller-
selected files, and makes no network calls. Its outputs are public archived
source excerpts and invented driver/SeaLink records. Calling the tool from
Claude sends those outputs to Anthropic as conversation context. No actual
driver credentials or private trip data belong in this test.

No public endpoint, cloud account, purchase, or new package is needed for this
local test. It validates Claude Desktop only; ChatGPT, Claude mobile/web remote
connectors, and Gemini integration remain untested.

## Local commands

```sh
python3 -m unittest discover -s tests -v
python3 -m kg context summary
python3 -m kg context induction
python3 -m kg context port_street
python3 run_mcp.py --audit
```

The last command speaks JSON-RPC on stdin/stdout and waits for an MCP client;
it is not an interactive chat or an HTTP server. The checked-in
`claude_desktop_config.example.json` documents the entry now merged into Claude's
configuration; do not use it to overwrite an existing configuration.

## Frozen collection plan

Run the six cases in `tests/provider_cases.json` once each in fresh incognito
Claude Chat conversations. The cases cover positive evidence, missing evidence
under pressure, a new SeaLink identifier, explicit non-completion, company
change only, and omitted inputs. They use a frozen synthetic date, not a live
September 6 dispatch claim.

`--audit` records successful, validated synthetic tool exchanges in private-mode
files under `.runtime/`. Each event contains raw accepted arguments, normalized
arguments, protocol request ID, full result, timestamp, and a hash chain.
The chain detects accidental edits; it is not a signed independent attestation.
Invalid raw inputs are not logged to avoid retaining accidental secrets.
Capture those failures from the app with sensitive content excluded and state
that the raw rejected payload was not retained.

The audit starts with surface `mcp_client_not_yet_attributed_to_provider`: a local
test harness can also call this tool. Only app UI captures and matching request
IDs/times can attribute an exchange to Claude. A local test transcript must
never be relabeled as provider output.

Save exact prompts, visible app/mode/version, final answers, tool exchanges and
manual rubric judgments in a new run directory. Inspect each final answer for
source fidelity, missing-fact preservation, and accidental broad clearance.
Failures are results. Do not edit expected outcomes to obtain a better score.

The larger 96-response archive remains frozen and untouched. This development
test does not reproduce that study, validate all six scenario families, measure
production safety, or compare chat providers.

## Protocol scope and references

The server deliberately implements the `2025-11-25` stdio lifecycle/tools subset,
not the entire latest protocol (the docs currently identify `2026-07-28` as
latest). It negotiates its supported version and advertises only tools. There
is no HTTP/OAuth, resources, sampling, subscriptions, or task support.

- [MCP lifecycle and version negotiation](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [MCP tools, structured results and errors](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [Official local-server connection guide using Claude Desktop](https://modelcontextprotocol.io/docs/develop/connect-local-servers)

Public documentation snapshots used during implementation are gitignored in
`.firecrawl/`. The recorded native-app run, not those documentation snapshots,
establishes the observed consumer behavior.
