#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="${root_dir}/skills"
official_validator="${CODEX_HOME:-${HOME}/.codex}/skills/.system/skill-creator/scripts/quick_validate.py"

validate_fallback() {
    python3 - "$1" <<'PY'
import re
import sys
from pathlib import Path

skill_dir = Path(sys.argv[1])
skill_file = skill_dir / "SKILL.md"
content = skill_file.read_text()
match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
if not match:
    raise SystemExit(f"[ERROR] {skill_dir.name}: invalid frontmatter")

frontmatter = match.group(1)
name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
description_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
if not name_match or not description_match:
    raise SystemExit(f"[ERROR] {skill_dir.name}: name or description missing")

name = name_match.group(1).strip().strip("\"'")
description = description_match.group(1).strip().strip("\"'")
if name != skill_dir.name or not re.fullmatch(r"[a-z0-9-]+", name):
    raise SystemExit(f"[ERROR] {skill_dir.name}: invalid skill name")
if not re.search(r"[\u4e00-\u9fff]", description):
    raise SystemExit(f"[ERROR] {skill_dir.name}: description must use Chinese")
if re.search(r"\[TODO|TODO[:：(\]]", content):
    raise SystemExit(f"[ERROR] {skill_dir.name}: TODO placeholder found")

agent_file = skill_dir / "agents" / "openai.yaml"
if agent_file.exists():
    if f"${name}" not in agent_file.read_text():
        raise SystemExit(f"[ERROR] {skill_dir.name}: default prompt must mention ${name}")
else:
    print(f"[SKIP] {skill_dir.name}: no agents/openai.yaml (Claude-only skill)")

print(f"[OK] {skill_dir.name}")
PY
}

validate_structure() {
    python3 - "$1" <<'PY'
import re
import sys
from pathlib import Path
from urllib.parse import unquote

skill_dir = Path(sys.argv[1])
skill_file = skill_dir / "SKILL.md"
content = skill_file.read_text()
name_match = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
if not name_match:
    raise SystemExit(f"[ERROR] {skill_dir.name}: name missing")
name = name_match.group(1).strip().strip("\"'")

agent_file = skill_dir / "agents" / "openai.yaml"
if agent_file.exists() and f"${name}" not in agent_file.read_text():
    raise SystemExit(f"[ERROR] {skill_dir.name}: default prompt must mention ${name}")

missing = []
for source in [skill_file, *sorted((skill_dir / "references").glob("*.md"))] if (skill_dir / "references").exists() else [skill_file]:
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", source.read_text()):
        if target.startswith(("http://", "https://", "#")):
            continue
        resolved = (source.parent / unquote(target)).resolve()
        if not resolved.exists():
            missing.append(f"{source.relative_to(skill_dir)} -> {target}")
if missing:
    raise SystemExit(f"[ERROR] {skill_dir.name}: broken links: {', '.join(missing)}")

print(f"[OK] {skill_dir.name} structure")
PY
}

for skill_dir in "${source_dir}"/*; do
    [[ -d "${skill_dir}" && -f "${skill_dir}/SKILL.md" ]] || continue

    if [[ -f "${official_validator}" ]] && python3 -c 'import yaml' >/dev/null 2>&1; then
        python3 "${official_validator}" "${skill_dir}"
    else
        validate_fallback "${skill_dir}"
    fi
    validate_structure "${skill_dir}"
done
