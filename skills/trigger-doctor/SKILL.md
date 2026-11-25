---
name: trigger-doctor
description: "Use when skills never fire when they should, after installing community skill packs, or for library hygiene - audit and rewrite skill triggers so relevant skills load at the right times."
version: 1.1.0
author: Darin Yantzer (DeezGit21), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, triggers, audit, curation, descriptions]
    related_skills: []
---

# Trigger Doctor

An audit-and-repair pass for a Hermes skill library. Downloaded and community skills
routinely carry name-prefixed descriptions, missing frontmatter, wrong `platforms:` or
placeholder text - structurally unable to trigger when they should. This skill finds
those failure modes mechanically and rewrites them trigger-first so the right skill
loads at the right time.

## When to Use

- A user says a skill "never fires", "never got utilized", or they keep loading it manually.
- After installing a community skill pack, hub skills, or bulk imports.
- Periodic library hygiene pass (monthly is plenty).
- A skill seems deleted: audit may reveal it exists but is untriggerable (looks dead, isn't).

Don't use for: creating a brand-new skill from scratch (follow skill-authoring
conventions instead) or archive/prune decisions (curation skills handle retention;
coordinate: 0-use broken skills may merit archiving, not rewriting).

## Failure modes, ranked by real-world impact

1. **Name-prefixed description** - `github-issues - Create, triage...` never matches how
   a user phrases a request. The most common pack-skill defect.
2. **`platforms:` missing the host OS** - the skill can be excluded from the catalog
   entirely on that host (e.g. `[linux, macos]` on a Windows machine). Silent and total.
3. **No frontmatter, or a broken delimiter** (`--- ` with a trailing space, leading
   whitespace before `---`) - the loader falls back to the first body line or skips
   indexing triggers.
4. **Placeholder description** - `One sentence - what this skill does and when to invoke it`.
5. **Terse capability statement with no trigger context** - `Gmail: Send an email.`.
6. **Orphaned sibling routes** - SKILL.md's routed-skills list points at skills that no
   longer exist (restore the siblings or drop the route line).

## Procedure

1. **Scan.** Run the bundled scanner through the `terminal` tool:
   `python scripts/audit_triggers.py --skills-dir "<skills dir>" --host-os <os> --json`
   Default skills dir: `$HERMES_HOME/skills` (or `~/.hermes/skills`); host OS: `sys.platform`.
   Completion criterion: JSON report on disk or printed, findings count captured.
2. **Hand-review every finding.** Keyword scoring WILL misclassify (a terse description
   may be perfect for a single-purpose skill; a long one may bury its trigger). Nothing
   gets edited from the report alone - read each flagged SKILL.md body first.
3. **Rewrite trigger-first.** Pattern: `Use when <situation in the user's own
   vocabulary> - <capability>.` Rules:
   - First ~60 chars must stand alone (some hosts truncate the index there); front-load
     the trigger words.
   - Bake in the user's real vocabulary: their project names, repos, tools, file paths.
   - Under ~200 chars total - the description is paid for on every turn; detail belongs
     in the body.
   - Never repeat the skill name as a prefix; state the situation, not the tool.
4. **Fix `platforms:`** to include the host OS when the skill's scripts/prose are
   cross-platform; gate narrower only for genuinely platform-bound content, and only
   after reading the scripts for POSIX-only calls (pty, termios, /proc, os.fork).
5. **Fix structure:** add full frontmatter to frontmatter-less skills (name must equal
   the directory name), normalize broken `--- ` delimiters, drop or restore orphaned
   sibling routes.
6. **Verify.** Re-run the scanner (expect zero hard-severity findings) and confirm every
   touched skill still shows enabled in the skill list. Note: the skill loader is
   initialized at session start - rewritten triggers take effect next session, which is
   expected, not a bug.

## Pitfalls

- **Never bulk-rewrite from the report alone.** The scanner finds candidates; judgment
  about what a skill is *for* comes from reading it. One rewrite should read like a human
  who knows the user wrote it.
- **Don't invent triggers.** A rewritten description must match what the body actually
  does, or the skill fires at wrong times - the inverse failure, and worse.
- **0-use + broken is an archive question, not just a rewrite question.** Flag it to the
  user rather than silently resurrecting a skill they may have abandoned on purpose.
- **Category-qualified usage keys:** usage stats may store bare names and
  `category/name` keys for the same skill - take the MAX across key variants when ranking.
- **Frontmatter descriptions containing `:` must be quoted** or YAML parses them as a mapping.

## Verification

- Scanner re-run: zero hard-severity findings (info-severity notes acceptable).
- `hermes skills list`: every touched skill present and enabled.
- Spot-check in a NEW session: describe a task that should invoke a rewritten skill and
  confirm it is retrieved; if not, the trigger vocabulary needs another pass.
