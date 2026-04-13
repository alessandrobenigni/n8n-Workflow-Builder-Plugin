# Prompts Library

Shared, generic prompt primitives that ship with the n8n workflow builder
plugin. These are building blocks — not project-specific content.

## What belongs here

- **Output contracts** — JSON schemas, format rules, parser-friendly
  instructions (e.g. `library/citm-json-contract.md`).
- **Generic judging/ranking rubrics** — templated scoring skeletons
  with placeholders for domain-specific criteria
  (e.g. `library/judge-rubric.md`).
- **Reusable tone/voice scaffolds** — if they are genuinely generic.

## What does NOT belong here

- Brand voice samples
- Niche-specific style guides
- Proprietary rubrics, client-specific instructions
- Anything you would not want shipped in a public plugin release

Those live in the **project** under `.n8n-files/prompts/` or
`<project>/prompts/`, and are resolved by `prompts.py` with priority
over this library.

## Resolution order

The `prompts.py` loader searches in this order, first match wins:

    1. $N8N_PROMPTS_DIR           (explicit override)
    2. <cwd>/.n8n-files/prompts   (project-scoped)
    3. <cwd>/prompts              (project-scoped)
    4. <plugin>/data/prompts      (this directory — shared library)

Use `python3 prompts.py --sources` to print the active search path.

## Usage

    # Read a prompt (body printed to stdout)
    python3 prompts.py --get library/judge-rubric

    # List every key available in the current working directory
    python3 prompts.py --list

    # Find which file a key actually resolves to
    python3 prompts.py --path library/citm-json-contract
