# Security

## What the skills touch

| Skill | Reads | Writes | Network |
|---|---|---|---|
| `bpmn` | `.bpmn` files you point it at, its own templates | `.bpmn` (and optional HTML) files in your working directory | None. The optional HTML card loads bpmn-js from unpkg.com when someone opens it in a browser |
| `bpmn-coach` | The `.bpmn` file you ask it to check | A temporary `.bpmn` file only when you paste XML into the chat | None |
| `bpmn-to-figjam` | The `.bpmn` file you name | Shapes on the FigJam board you name, inside a new section | Your connected Figma MCP server |

No credentials are stored by these skills. FigJam access goes through the Figma MCP server you have already connected and authorised in Claude Code.

## The validator and untrusted files

`validate.py` parses XML with Python's `xml.etree.ElementTree`. It does not resolve external entities, so XXE file reads and network fetches don't apply. Very large or deeply nested files can still use a lot of memory. Treat `.bpmn` files from unknown sources as you would any other untrusted document.

## Process diagrams can be sensitive

A process map can reveal how an organisation works: approval limits, team structure, systems, volumes. Before rendering into a shared FigJam board, check who can see it. Don't commit real process diagrams to a public fork.

## Reporting a vulnerability

Please don't open a public issue for security problems. Use GitHub's [private vulnerability reporting](https://github.com/gersoncorreias/claude-bpmn/security/advisories/new) for this repository.
