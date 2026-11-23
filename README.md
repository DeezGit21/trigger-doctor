# Trigger Doctor

A [Hermes Agent](https://github.com/nousresearch/hermes-agent) skill that finds the skills in
your library that **will never fire when they should** — and rewrites their triggers so they do.

Downloaded skills, community packs and bulk imports routinely carry descriptions that are
structurally unable to trigger. The skill exists; the agent just never retrieves it. The most
common defect is so invisible you never suspect it:

```yaml
name: github-issues
description: github-issues — Create, triage, label, assign GitHub issues via gh or REST.
```

A name-prefixed description never matches how a user phrases a request, so the skill sits in
the catalog dead. Worse: a pack that ships `platforms: [linux, macos]` means the skill can be
excluded **entirely on a Windows host** — silently, with no error anywhere.

## What it detects

| Finding | Severity | Why it matters |
|---|---|---|
| Name-prefixed description (`skill-name — does things`) | hard | Never matches user phrasing; never retrieved |
| `platforms:` present but excludes the host OS | hard | Skill cannot load on this machine at all |
| No frontmatter / unclosed frontmatter | hard | Index falls back to the first body line |
| Broken `--- ` delimiter (trailing space) | hard | Frontmatter silently ignored |
| Placeholder description (`One sentence - what this skill does...`) | hard | Zero trigger content |
| Description under 25 chars, no trigger context | hard | Fires on nothing (or everything) |
| Frontmatter `name` ≠ directory name | hard | Lookup mismatch |
| Generic opener (`Expert guide to...`) | hard | Describes a topic, not a situation |
| No `platforms:` field | info | Harmless — loads on all hosts |
| No "Use when..." trigger phrase | info | Capability stated but no situation |
| Description over 250 chars | info | Index cost on every turn |

The scanner ranks findings by real usage from `.usage.json`, so a broken skill you actually
need sorts above a broken skill you never use.

## Install

Copy the skill into your Hermes skills directory:

```
git clone https://github.com/DeezGit21/trigger-doctor.git
mkdir -p ~/.hermes/skills            # %LOCALAPPDATA%\hermes\skills on Windows
cp -r trigger-doctor/skills/trigger-doctor ~/.hermes/skills/
```

Start a new session (the skill loader is initialized at session start) and say
**"run trigger doctor on my skills"** — the SKILL.md drives the whole pass: scan,
hand-review, rewrite, verify.

## Standalone use (no agent)

The scanner is stdlib-only Python and works by itself:

```
python skills/trigger-doctor/scripts/audit_triggers.py --skills-dir ~/.hermes/skills
# exit 0 = clean, 1 = hard findings; add --json for a machine-readable report
```

## How the rewrite pass works

The scanner finds candidates — a human (or an agent reading each SKILL.md body) supplies
judgment. The rewrite pattern that actually triggers:

> `Use when <situation in the user's own vocabulary> — <capability>.`

Rules baked into the skill:

- Front-load the trigger in the first ~60 chars (some hosts truncate the index there)
- Bake in the user's real vocabulary — their project names, repos, tools
- Under ~200 chars; the description is paid for on every turn
- Never repeat the skill name; describe the situation, not the tool
- **Never bulk-rewrite from the report alone** — keyword scoring misclassifies; read each skill first
- Don't invent triggers: a description that over-promises fires the skill at wrong times, which is worse than never

## Provenance

Built out of a real repair session: a GitHub skill family and a trading scanner skill had
been deleted from the library and "never fired" before they were deleted — auditing the
recovered files showed name-prefixed descriptions plus `platforms: [linux, macos]` on a
Windows host. This skill is that audit, generalized.

## License

MIT
