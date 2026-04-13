## Generic Judge Rubric

Use this skeleton when you need an LLM to score and rank a batch of
items (news articles, leads, candidates, ideas). The caller should
replace the `<DOMAIN>` placeholders with their specific criteria.

### Scoring

Score each item on four dimensions, 1–5 each (5 = best). Return the
total as `score` and the per-dimension breakdown as `breakdown`.

1. **Novelty** — does this item surface something new, or repeat what
   readers of `<DOMAIN>` already know? Penalize restated consensus.
2. **Actionability** — can a `<AUDIENCE>` practitioner do something
   concrete with this insight? Theoretical-only items score lower.
3. **Credibility** — is the source reliable in `<DOMAIN>`? First-party
   research, primary sources, and recognized experts score higher than
   aggregators or SEO-bait blogs.
4. **Specificity** — does the item make a concrete claim with a
   mechanism or number, or is it a vague trend piece? Vague scores low.

### Anti-repetition

You will receive a `recent_angles` list. If an item's framing matches
any `angle_tag` in that list, subtract 3 from its total score. The goal
is feed freshness, not just per-item quality.

### Selection

After scoring, pick the top `n` items (the caller specifies `n`,
usually 3). Ties broken by Novelty first, then Actionability.

### Output fields

- `scored`: array of `{ id, score, breakdown, angle_tag, rationale }`
- `selected`: array of `id` values in final rank order
- `rationale` per item: 1–2 sentences, plain prose, no marketing-speak
