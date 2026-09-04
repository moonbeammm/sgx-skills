#!/usr/bin/env bash
set -euo pipefail

# 把 sgx-skills 仓库内的技能（skills/*）symlink 到 Codex 和 Claude Code 的 skill 目录。
# 技能唯一源在 skills/；增删技能后重跑本脚本即可。

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="${root_dir}/skills"

# 目标目录：Codex + Claude Code。可用环境变量覆盖各自的 home。
target_dirs=(
    "${CODEX_HOME:-${HOME}/.codex}/skills"
    "${CLAUDE_HOME:-${HOME}/.claude}/skills"
)

sync_target() {
    local target_dir="$1"
    echo "=== ${target_dir} ==="
    mkdir -p "${target_dir}"

    for skill_dir in "${source_dir}"/*; do
        [[ -d "${skill_dir}" && -f "${skill_dir}/SKILL.md" ]] || continue

        local skill_name target current
        skill_name="$(basename "${skill_dir}")"
        target="${target_dir}/${skill_name}"

        if [[ -L "${target}" ]]; then
            current="$(readlink "${target}")"
            if [[ "${current}" == "${skill_dir}" ]]; then
                echo "[OK] ${skill_name} already installed"
                continue
            fi
            rm "${target}"
        elif [[ -e "${target}" ]]; then
            echo "[ERROR] ${target} exists and is not a symlink" >&2
            exit 1
        fi

        ln -s "${skill_dir}" "${target}"
        echo "[OK] installed ${skill_name} -> ${skill_dir}"
    done

    # 清理悬空软链：只处理指回本仓库 skills/ 但源已删除的软链，不碰其它 skill。
    local link dest
    for link in "${target_dir}"/*; do
        [[ -L "${link}" ]] || continue
        dest="$(readlink "${link}")"
        [[ "${dest}" == "${source_dir}/"* ]] || continue
        [[ -e "${dest}" ]] && continue
        rm "${link}"
        echo "[RM] removed stale link $(basename "${link}") -> ${dest}"
    done
}

for target_dir in "${target_dirs[@]}"; do
    sync_target "${target_dir}"
done
