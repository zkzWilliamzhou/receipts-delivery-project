# Installed skills

Installed from GitHub into the workspace `.skills/` directory on 2026-11-10; a copy of the generated manifest is bundled as `installed_skills_manifest.json` in the delivery zip. `github.com` git transport returned 403 in this environment; `codeload.github.com` and `raw.githubusercontent.com` worked, so each repository was fetched as a tarball and extracted in place. These are local file installs. I read and applied their `SKILL.md` rules; I did not register them as native runtime tools.

| Requested | Upstream repo | Branch | SKILL.md files | Used for |
|---|---|---|---|---|
| Anthropic skills | `anthropics/skills` | main | 20 | `skill-creator` template for `docs/skills/receipts-verify/SKILL.md`, `webapp-testing` patterns |
| Matt Pocock skills | `mattpocock/skills` | main | 39 | `improve-codebase-architecture`, `codebase-design`, `grill-me`, `grilling`, `tdd`, `code-review`, `diagnosing-bugs` |
| Vercel Labs | `vercel-labs/agent-skills` | main | 9 | `writing-guidelines` for README and docs |
| Vercel Labs CLI | `vercel-labs/skills` | main | 5 | Agent Skills spec, `find-skills`, distribution format |
| stop-slop | `tomerose/stop-slop` | master | 1 | Prose checks on README and docs (41 anti-patterns, 5-dimension score) |
| Superpowers | `obra/superpowers` | main | 15 | `brainstorming`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `requesting-code-review`, `receiving-code-review`, `writing-plans`, `subagent-driven-development` |
| Brainstorming | `obra/superpowers/skills/brainstorming` | main | 1 | Self-grilling in `docs/BRAINSTORM.md` |

Total: 89 `SKILL.md` files across six repositories. The generated manifest is bundled as `installed_skills_manifest.json`; the live copy lives in the workspace `.skills/repo_manifest.json`.

## Skills applied to this program specifically

- `test-driven-development`: phase 4 writes tests before implementation.
- `verification-before-completion`: every completion claim needs a fresh command and its exit code.
- `systematic-debugging` and `diagnosing-bugs`: reproduce, isolate, root cause, fix, regression test.
- `requesting-code-review` / `code-review`: review rounds 1-8 with findings and re-runs.
- `improve-codebase-architecture` + `codebase-design`: phase 9 deepened `sandbox.py` into the `Backend` value object, using the deletion test, locality, and `GLOSSARY.md` vocabulary; the golden contract stayed byte-identical. See `docs/ARCHITECTURE_REVIEW.html`.
- `grill-me` / `grilling`: 14 adversarial self-questions in `BRAINSTORM.md`.
- `writing-guidelines` + `stop-slop`: README and docs pass a prose lint.
- `skill-creator`: the bundled `receipts-verify` skill that teaches an agent to call `receipts verify` before claiming done.
- `find-skills` and `web-design-guidelines`: offline HTML architecture report layout.

## Marketplace check

`FindSkill` returned no matching installed skill for brainstorming, improve-codebase-architecture, or superpowers, so the GitHub installs were necessary. No candidate from the marketplace was used as a substitute.
