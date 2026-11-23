#!/usr/bin/env python3
"""audit_triggers.py - scan a Hermes skill library for skills that are
structurally unable to trigger (bad descriptions, missing frontmatter,
wrong platforms) and report them ranked by usage.

Stdlib only. Exit code 0 = clean, 1 = hard findings, 2 = usage error.
"""
import argparse
import json
import os
import re
import sys

PLACEHOLDER_PATTERNS = [
    r"^one sentence\b",
    r"what this skill does",
    r"describe .{0,20}here",
    r"^todo\b",
    r"^placeholder",
]
GENERIC_STARTERS = [r"^expert guide", r"^a skill that", r"^this skill (?:provides|is)"]

def parse_frontmatter(text):
    """Return (fm_dict|None, error|None)."""
    if not text.lstrip("\ufeff").startswith("---"):
        return None, "no_frontmatter"
    end = re.search(r"^---\s*$", text[3:], re.M)
    if not end:
        return None, "unclosed_frontmatter"
    fm_text = text[3:end.start()]
    fm = {}
    current_key = None
    block = None  # active block scalar: {'fold': bool, 'lines': []}

    for line in fm_text.splitlines():
        if block is not None:
            if not line.strip():
                block["lines"].append("")
                continue
            if line[:1] in (" ", "\t"):
                block["lines"].append(line.strip())
                continue
            # non-indented, non-blank line: block scalar ends
            joiner = " " if block["fold"] else "\n"
            if current_key:
                fm[current_key] = joiner.join(block["lines"]).strip()
            block = None
        if not line.strip():
            continue
        m_item = re.match(r"^\s*-\s+(.*)$", line)
        if m_item:
            if current_key:
                fm.setdefault(current_key, []).append(m_item.group(1).strip())
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            current_key = m.group(1).lower()
            val = m.group(2).strip().strip('"\'' )
            if val:
                fm[current_key] = val
                if val in (">", ">-", "|", "|-", "|+", ">+"):
                    block = {"fold": val.startswith(">"), "lines": []}
    if block is not None:
        joiner = " " if block["fold"] else "\n"
        if current_key:
            fm[current_key] = joiner.join(block["lines"]).strip()
    return fm, None

def max_usage(usage, name):
    best = 0
    for k, v in usage.items():
        if k.split("/")[-1] == name and isinstance(v, dict):
            try:
                best = max(best, int(v.get("use_count") or 0))
            except (TypeError, ValueError):
                pass
    return best

def audit_skill(rel, skill_md_path, host_os, usage):
    findings = []
    sev = lambda s: s  # clarity
    try:
        text = open(skill_md_path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        return [(sev("hard"), "unreadable", str(e))]
    if text.startswith("--- "):
        findings.append((sev("hard"), "broken_delimiter", "frontmatter delimiter has trailing space"))
    fm, err = parse_frontmatter(text)
    if err:
        findings.append((sev("hard"), err, err.replace("_", " ")))
        return findings
    name = fm.get("name") or os.path.basename(rel)
    if not fm.get("name"):
        findings.append((sev("hard"), "missing_name", "frontmatter has no name field"))
    elif fm.get("name") != os.path.basename(rel):
        findings.append((sev("hard"), "name_mismatch",
                         f"frontmatter name '{fm['name']}' != directory '{os.path.basename(rel)}'"))
    desc = str(fm.get("description", ""))
    if not desc:
        findings.append((sev("hard"), "empty_description", "no description"))
        return findings
    bare = desc.lower()
    if re.match(rf"^{re.escape(name)}\s*[-:\u2014\u2013]", bare):
        findings.append((sev("hard"), "name_prefixed",
                         "description starts with the skill name - never matches user phrasing"))
    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, bare):
            findings.append((sev("hard"), "placeholder", f"placeholder text: matches /{pat}/"))
            break
    for pat in GENERIC_STARTERS:
        if re.search(pat, bare):
            findings.append((sev("hard"), "generic", f"generic opener: matches /{pat}/"))
            break
    if len(desc) < 25:
        findings.append((sev("hard"), "too_short", f"description only {len(desc)} chars"))
    platforms = fm.get("platforms") or []
    if isinstance(platforms, str):
        platforms = [p.strip() for p in platforms.strip("[]").split(",") if p.strip()]
    platforms = [p.lower() for p in platforms]
    host = {"win32": "windows", "darwin": "macos"}.get(host_os, host_os)
    if not platforms:
        # no platforms field = loads everywhere (standard for user-local skills); info only
        findings.append((sev("info"), "platforms_unset", "no platforms field - loads on all hosts"))
    elif host in ("windows", "linux", "macos") and host not in platforms:
        findings.append((sev("hard"), "platform_excluded",
                         f"platforms {platforms} excludes host '{host}' - skill cannot load on this machine"))
    if "use when" not in bare and "use this" not in bare and "use for" not in bare:
        findings.append((sev("info"), "no_trigger_phrase",
                         "description states capability but no situation - consider trigger-first rewrite"))
    if len(desc) > 250:
        findings.append((sev("info"), "too_long", f"{len(desc)} chars - trim; detail belongs in the body"))
    return findings

def main():
    ap = argparse.ArgumentParser(description="Audit Hermes skill triggers")
    ap.add_argument("--skills-dir", default=os.path.join(
        os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")), "skills"))
    ap.add_argument("--host-os", default=sys.platform)
    ap.add_argument("--json", dest="as_json", action="store_true", help="emit JSON report")
    ap.add_argument("--out", help="write JSON report to this path")
    args = ap.parse_args()

    root = os.path.abspath(os.path.expanduser(args.skills_dir))
    if not os.path.isdir(root):
        print(f"skills dir not found: {root}", file=sys.stderr)
        sys.exit(2)
    usage = {}
    usage_path = os.path.join(root, ".usage.json")
    if os.path.isfile(usage_path):
        try:
            usage = json.load(open(usage_path, encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            pass

    report, scanned = [], 0
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root).replace("\\", "/")
        top = rel.split("/")[0]
        if rel != "." and (top.startswith(".") or top.startswith("skills-archive")):
            dirnames[:] = []
            continue
        if "SKILL.md" not in filenames:
            continue
        scanned += 1
        fnd = audit_skill(rel, os.path.join(dirpath, "SKILL.md"), args.host_os, usage)
        if fnd:
            report.append({
                "skill": rel,
                "use_count": max_usage(usage, os.path.basename(rel)),
                "severity": "hard" if any(s == "hard" for s, _, _ in fnd) else
                            ("medium" if any(s == "medium" for s, _, _ in fnd) else "info"),
                "findings": [{"severity": s, "check": c, "detail": d} for s, c, d in fnd],
            })

    hard = sum(1 for r in report if r["severity"] == "hard")
    order = {"hard": 0, "medium": 1, "info": 2}
    report.sort(key=lambda r: (order[r["severity"]], r["skill"]))
    payload = {"skills_dir": root, "host_os": args.host_os,
               "skills_scanned": scanned, "skills_flagged": len(report),
               "hard_findings": hard, "findings": report}
    out = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.out:
        open(os.path.expanduser(args.out), "w", encoding="utf-8").write(out)
    if args.as_json:
        print(out)
    else:
        print(f"scanned {scanned} skills in {root}")
        print(f"flagged: {len(report)} skills, {hard} hard findings\n")
        for r in report:
            print(f"[{r['severity']:^6}] use={r['use_count']:<4} {r['skill']}")
            for f in r["findings"]:
                print(f"          - {f['check']}: {f['detail']}")
    sys.exit(1 if hard else 0)

if __name__ == "__main__":
    main()
