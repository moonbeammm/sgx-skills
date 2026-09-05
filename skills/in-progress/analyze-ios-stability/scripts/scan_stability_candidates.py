#!/usr/bin/env python3
"""Collect high-signal iOS stability review candidates from KNTR source files.

This is deliberately a lexical triage tool, not a bug detector. A match must be
reviewed for production reachability, trigger, failure mechanism, and guards.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Rule:
    rule_id: str
    category: str
    priority_hint: str
    languages: frozenset[str]
    expression: re.Pattern[str]
    review_question: str


@dataclass(frozen=True)
class Candidate:
    rule_id: str
    category: str
    priority_hint: str
    path: str
    line: int
    languages: str
    snippet: str
    review_question: str


def rule(
    rule_id: str,
    category: str,
    priority_hint: str,
    languages: Sequence[str],
    expression: str,
    review_question: str,
) -> Rule:
    return Rule(
        rule_id=rule_id,
        category=category,
        priority_hint=priority_hint,
        languages=frozenset(languages),
        expression=re.compile(expression),
        review_question=review_question,
    )


RULES: tuple[Rule, ...] = (
    rule(
        "swift-forced-try",
        "crash",
        "high",
        ("swift",),
        r"\btry\s*!",
        "Can the throwing operation fail for production input, state, or I/O?",
    ),
    rule(
        "swift-forced-cast",
        "crash",
        "high",
        ("swift",),
        r"\bas\s*!\s*[A-Za-z_(\[]",
        "What proves the dynamic value always has the forced target type?",
    ),
    rule(
        "swift-explicit-trap",
        "crash",
        "high",
        ("swift",),
        r"\b(?:fatalError|preconditionFailure|assertionFailure)\s*\(",
        "Is this path reachable in a production build, and is termination intended?",
    ),
    rule(
        "kotlin-forced-null",
        "crash",
        "medium",
        ("kotlin",),
        r"(?<![!])!!(?![=!])",
        "Which invariant proves the receiver is non-null on every iOS call path?",
    ),
    rule(
        "kotlin-explicit-trap",
        "crash",
        "medium",
        ("kotlin",),
        r"\b(?:error|TODO)\s*\(",
        "Can a shipping iOS path reach this explicit termination?",
    ),
    rule(
        "native-process-trap",
        "crash",
        "high",
        ("objc", "c", "cpp"),
        r"\b(?:abort|__builtin_trap)\s*\(",
        "Can recoverable input or lifecycle state reach this process termination?",
    ),
    rule(
        "swift-unowned-reference",
        "lifetime",
        "high",
        ("swift",),
        r"(?:\[\s*unowned\b|,\s*unowned\b|\bunowned\s+(?:let|var)\b)",
        "What guarantees the referenced owner outlives every callback or access?",
    ),
    rule(
        "objc-unsafe-unretained",
        "lifetime",
        "high",
        ("objc", "cpp"),
        r"\b(?:__unsafe_unretained|unsafe_unretained)\b",
        "What synchronizes teardown so this non-zeroing reference cannot dangle?",
    ),
    rule(
        "observer-registration",
        "lifetime",
        "medium",
        ("swift", "objc", "kotlin"),
        r"(?:NotificationCenter\s*\.\s*default\s*\.\s*addObserver|\baddObserverForName\b|\baddObserver\s*:\s*)",
        "Who owns the observation/token, and when is block/callback observation removed?",
    ),
    rule(
        "timer-or-display-link",
        "lifetime",
        "medium",
        ("swift", "objc"),
        r"(?:\bTimer\s*\.\s*scheduledTimer\b|\bscheduledTimerWithTimeInterval\b|\bCADisplayLink\b|\bdisplayLinkWithTarget\b)",
        "Where is this source invalidated, and can its callback retain or outlive the owner?",
    ),
    rule(
        "swift-retained-interop",
        "cross-language",
        "high",
        ("swift",),
        r"\bUnmanaged\s*\.\s*(?:passRetained|passUnretained|fromOpaque)|\b(?:takeRetainedValue|takeUnretainedValue)\s*\(",
        "Does the retain/unretained convention match the foreign API on every path?",
    ),
    rule(
        "objc-retained-bridge",
        "cross-language",
        "high",
        ("objc", "cpp"),
        r"\b(?:CFBridgingRetain|CFBridgingRelease)\s*\(|__bridge_retained\b|__bridge_transfer\b",
        "Is ownership transferred exactly once, including error and cancellation paths?",
    ),
    rule(
        "kotlin-stable-ref",
        "cross-language",
        "high",
        ("kotlin",),
        r"\bStableRef\s*\.\s*create\s*\(|\basStableRef\s*\(",
        "Which owner disposes the StableRef after unregister, timeout, or late callback?",
    ),
    rule(
        "kotlin-pinned-memory",
        "cross-language",
        "medium",
        ("kotlin",),
        r"\b(?:usePinned|pin)\s*\(",
        "Can the pointer escape the pinned scope or remain in a native async callback?",
    ),
    rule(
        "swift-continuation",
        "concurrency",
        "high",
        ("swift",),
        r"\bwith(?:Checked|Unsafe)(?:Throwing)?Continuation\b",
        "Is the continuation resumed exactly once on success, error, cancellation, and timeout?",
    ),
    rule(
        "swift-detached-task",
        "concurrency",
        "medium",
        ("swift",),
        r"\bTask\s*\.\s*detached\s*\{",
        "Who owns cancellation, and which actor/priority/task-local assumptions are lost?",
    ),
    rule(
        "sync-dispatch",
        "concurrency",
        "high",
        ("swift", "objc", "c", "cpp"),
        r"\bdispatch_sync(?:_f)?\s*\(|\.\s*sync\s*\{",
        "Can the target serial queue be current or wait synchronously back on the caller?",
    ),
    rule(
        "native-lock-or-wait",
        "concurrency",
        "medium",
        ("swift", "objc", "c", "cpp"),
        r"\b(?:pthread_mutex_lock|os_unfair_lock_lock|dispatch_semaphore_wait|objc_sync_enter)\s*\(|@synchronized\s*\(",
        "What is the lock/wait ordering, expected waker, timeout, and callback behavior while held?",
    ),
    rule(
        "blocking-main-thread-candidate",
        "concurrency",
        "high",
        ("swift", "objc", "kotlin"),
        r"\b(?:Thread\s*\.\s*sleep|NSThread\s+sleepForTimeInterval|waitUntilFinished|runBlocking)\b",
        "Can this execute on the main thread or another constrained executor?",
    ),
    rule(
        "kotlin-global-scope",
        "lifetime",
        "medium",
        ("kotlin",),
        r"\bGlobalScope\b",
        "What component owns this work, and how is it cancelled when the iOS owner ends?",
    ),
    rule(
        "kotlin-broad-catch",
        "concurrency",
        "medium",
        ("kotlin",),
        r"\bcatch\s*\(\s*[A-Za-z_][A-Za-z0-9_]*\s*:\s*(?:Throwable|Exception)\b",
        "Does this path rethrow cancellation and preserve the original failure semantics?",
    ),
    rule(
        "unsafe-native-pointer",
        "cross-language",
        "medium",
        ("swift", "kotlin"),
        r"\b(?:unsafeBitCast|UnsafeMutableRawPointer|UnsafeRawPointer|CPointer|COpaquePointer)\b",
        "Who owns the pointee, what bounds apply, and can the pointer outlive or race its storage?",
    ),
    rule(
        "unsafe-c-copy",
        "memory-safety",
        "high",
        ("objc", "c", "cpp"),
        r"\b(?:strcpy|strcat|sprintf|gets)\s*\(",
        "What statically or dynamically proves the destination capacity is sufficient?",
    ),
    rule(
        "manual-native-allocation",
        "lifetime",
        "medium",
        ("objc", "c", "cpp"),
        r"\b(?:malloc|calloc|realloc|posix_memalign)\s*\(",
        "Which owner frees this allocation on every normal, error, cancellation, and teardown path?",
    ),
    rule(
        "native-thread-start",
        "concurrency",
        "medium",
        ("objc", "c", "cpp"),
        r"\bpthread_create\s*\(",
        "How is the thread stopped/joined, and can callbacks race owner teardown?",
    ),
)


SOURCE_LANGUAGES: dict[str, frozenset[str]] = {
    ".swift": frozenset(("swift",)),
    ".m": frozenset(("objc",)),
    ".mm": frozenset(("objc", "cpp")),
    ".h": frozenset(("objc", "c", "cpp")),
    ".hpp": frozenset(("cpp",)),
    ".hh": frozenset(("cpp",)),
    ".c": frozenset(("c",)),
    ".cc": frozenset(("cpp",)),
    ".cpp": frozenset(("cpp",)),
    ".kt": frozenset(("kotlin",)),
    ".kts": frozenset(("kotlin",)),
}

EXCLUDED_PARTS = frozenset(
    {
        ".agents",
        ".claude",
        ".git",
        ".gradle",
        ".gradle_extractor",
        ".idea",
        "bazel-bin",
        "bazel-out",
        "bazel-testlogs",
        "build",
        "carthage",
        "deriveddata",
        "docs",
        "examples",
        "external",
        "fixtures",
        "generated",
        "genfiles",
        "multimedia-thirdparty",
        "node_modules",
        "pods",
        "third_party",
        "third-party",
        "thirdparty",
        "vendor",
        "venders",
        "vendors",
        "vendor_src",
    }
)
EXCLUDED_PREFIXES = (
    ("bapis",),
    ("bili_resource",),
    ("docs",),
    ("rules",),
    ("tools",),
    ("srcs", "legacy-andruid"),
)
TEST_PARTS = frozenset(
    {
        "androidinstrumentedtest",
        "androidtest",
        "commontest",
        "iostest",
        "iosuitest",
        "nativetest",
        "test",
        "tests",
        "testdata",
    }
)
NON_IOS_SOURCE_SETS = frozenset(
    {
        "androidmain",
        "androidtest",
        "harmonyMain".lower(),
        "harmonytest",
        "jsmain",
        "jvmMain".lower(),
        "windowMain".lower(),
        "windowsmain",
    }
)
GENERATED_MARKERS = (
    "<auto-generated",
    "automatically generated",
    "generated by",
    "do not edit",
    "@generated",
)


class ScanError(RuntimeError):
    pass


def run_git(repo: Path, arguments: Sequence[str], *, allow_failure: bool = False) -> bytes:
    process = subprocess.run(
        ("git", *arguments),
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode and not allow_failure:
        error = process.stderr.decode("utf-8", errors="replace").strip()
        raise ScanError(error or f"git {' '.join(arguments)} failed")
    return process.stdout if process.returncode == 0 else b""


def repository_root() -> Path:
    process = subprocess.run(
        ("git", "rev-parse", "--show-toplevel"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode:
        raise ScanError("run this script inside a Git worktree")
    return Path(process.stdout.decode("utf-8").strip()).resolve()


def normalized_scopes(repo: Path, raw_scopes: Sequence[str]) -> list[str]:
    scopes = raw_scopes or (".",)
    normalized: list[str] = []
    for raw_scope in scopes:
        path = Path(raw_scope).expanduser()
        absolute = path.resolve() if path.is_absolute() else (Path.cwd() / path).resolve()
        try:
            relative = absolute.relative_to(repo)
        except ValueError as error:
            raise ScanError(f"scope is outside the repository: {raw_scope}") from error
        normalized.append(relative.as_posix() or ".")
    return normalized


def split_nul(output: bytes) -> set[str]:
    return {
        item.decode("utf-8", errors="surrogateescape")
        for item in output.split(b"\0")
        if item
    }


def candidate_paths(repo: Path, scopes: Sequence[str], changed: bool) -> list[str]:
    if not changed:
        return sorted(split_nul(run_git(repo, ("ls-files", "-z", "--", *scopes))))

    changed_files = split_nul(
        run_git(
            repo,
            ("diff", "--name-only", "--diff-filter=ACMR", "-z", "HEAD", "--", *scopes),
            allow_failure=True,
        )
    )
    if not changed_files:
        changed_files.update(
            split_nul(
                run_git(
                    repo,
                    ("diff", "--name-only", "--diff-filter=ACMR", "-z", "--", *scopes),
                    allow_failure=True,
                )
            )
        )
    changed_files.update(
        split_nul(
            run_git(
                repo,
                ("ls-files", "--others", "--exclude-standard", "-z", "--", *scopes),
            )
        )
    )
    return sorted(changed_files)


def languages_for(path: Path) -> frozenset[str]:
    return SOURCE_LANGUAGES.get(path.suffix.lower(), frozenset())


def excluded_reason(relative_path: str, languages: frozenset[str], include_tests: bool) -> str | None:
    path = Path(relative_path)
    lowered_parts = tuple(part.lower() for part in path.parts)
    if not languages:
        return "unsupported-extension"
    if any(lowered_parts[: len(prefix)] == prefix for prefix in EXCLUDED_PREFIXES):
        return "generated-or-nonproduction-path"
    if any(part in EXCLUDED_PARTS for part in lowered_parts):
        return "generated-or-nonproduction-path"
    if not include_tests and any(part in TEST_PARTS or part.endswith("test") for part in lowered_parts):
        return "test-path"
    if "kotlin" in languages:
        if any(part in NON_IOS_SOURCE_SETS for part in lowered_parts):
            return "non-ios-source-set"
        if lowered_parts[:2] == ("binary", "application") and "ios" not in lowered_parts:
            return "non-ios-application-source"
    return None


def strip_comments(line: str, in_block_comment: bool) -> tuple[str, bool]:
    output: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False
    while index < len(line):
        pair = line[index : index + 2]
        character = line[index]
        if in_block_comment:
            if pair == "*/":
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote:
            output.append(" ")
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            index += 1
            continue
        if character in ('"', "'"):
            quote = character
            output.append(" ")
            index += 1
            continue
        if pair == "//":
            break
        if pair == "/*":
            in_block_comment = True
            index += 2
            continue
        output.append(character)
        index += 1
    return "".join(output), in_block_comment


def is_generated(lines: Sequence[str]) -> bool:
    prefix = "\n".join(lines[:12]).lower()
    return any(marker in prefix for marker in GENERATED_MARKERS)


def compact_snippet(line: str, limit: int = 180) -> str:
    compact = " ".join(line.strip().split())
    return compact if len(compact) <= limit else f"{compact[: limit - 1]}…"


def scan_file(
    repo: Path,
    relative_path: str,
    rules: Sequence[Rule],
    include_generated: bool,
) -> tuple[list[Candidate], bool]:
    path = repo / relative_path
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], False
    if "\0" in text:
        return [], False
    lines = text.splitlines()
    generated = is_generated(lines)
    if generated and not include_generated:
        return [], True

    languages = languages_for(path)
    language_label = "/".join(sorted(languages))
    candidates: list[Candidate] = []
    in_block_comment = False
    for line_number, raw_line in enumerate(lines, start=1):
        code, in_block_comment = strip_comments(raw_line, in_block_comment)
        if not code.strip():
            continue
        for current_rule in rules:
            if not languages.intersection(current_rule.languages):
                continue
            if current_rule.expression.search(code):
                candidates.append(
                    Candidate(
                        rule_id=current_rule.rule_id,
                        category=current_rule.category,
                        priority_hint=current_rule.priority_hint,
                        path=relative_path,
                        line=line_number,
                        languages=language_label,
                        snippet=compact_snippet(raw_line),
                        review_question=current_rule.review_question,
                    )
                )
    return candidates, generated


def scan(
    repo: Path,
    paths: Sequence[str],
    include_tests: bool,
    include_generated: bool,
    max_per_rule: int,
) -> tuple[list[Candidate], dict[str, int], list[str]]:
    candidates: list[Candidate] = []
    skipped: Counter[str] = Counter()
    rule_counts: Counter[str] = Counter()
    truncated: set[str] = set()
    for relative_path in paths:
        languages = languages_for(Path(relative_path))
        reason = excluded_reason(relative_path, languages, include_tests)
        if reason:
            skipped[reason] += 1
            continue
        matches, generated = scan_file(repo, relative_path, RULES, include_generated)
        if generated and not include_generated:
            skipped["generated-marker"] += 1
            continue
        skipped["scanned-files"] += 1
        for match in matches:
            if rule_counts[match.rule_id] >= max_per_rule:
                truncated.add(match.rule_id)
                continue
            candidates.append(match)
            rule_counts[match.rule_id] += 1
    candidates.sort(key=lambda item: (item.category, item.rule_id, item.path, item.line))
    return candidates, dict(sorted(skipped.items())), sorted(truncated)


def escape_markdown(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_markdown(
    candidates: Sequence[Candidate],
    scopes: Sequence[str],
    changed: bool,
    skipped: dict[str, int],
    truncated: Sequence[str],
) -> str:
    lines = [
        "# iOS stability candidate scan",
        "",
        "> Lexical review candidates only. These are not confirmed defects or severity assignments.",
        "",
        f"- Scope: `{', '.join(scopes)}`",
        f"- Mode: `{'changed files' if changed else 'tracked files'}`",
        f"- Files scanned: {skipped.get('scanned-files', 0)}",
        f"- Candidates emitted: {len(candidates)}",
    ]
    if truncated:
        lines.append(f"- Truncated rules: `{', '.join(truncated)}`")
    if not candidates:
        lines.extend(("", "No lexical candidates found in the inspected files."))
        return "\n".join(lines)

    grouped: dict[str, list[Candidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.category].append(candidate)
    for category in sorted(grouped):
        lines.extend(
            (
                "",
                f"## {category}",
                "",
                "| Rule | Priority hint | Location | Signal | Review question |",
                "| --- | --- | --- | --- | --- |",
            )
        )
        for candidate in grouped[category]:
            lines.append(
                "| "
                + " | ".join(
                    (
                        escape_markdown(candidate.rule_id),
                        candidate.priority_hint,
                        f"`{escape_markdown(candidate.path)}:{candidate.line}`",
                        f"`{escape_markdown(candidate.snippet)}`",
                        escape_markdown(candidate.review_question),
                    )
                )
                + " |"
            )
    return "\n".join(lines)


def render_json(
    candidates: Sequence[Candidate],
    scopes: Sequence[str],
    changed: bool,
    skipped: dict[str, int],
    truncated: Sequence[str],
) -> str:
    document = {
        "schema_version": 1,
        "disclaimer": "Lexical review candidates only; not confirmed defects.",
        "scope": list(scopes),
        "mode": "changed" if changed else "tracked",
        "statistics": {
            "files_scanned": skipped.get("scanned-files", 0),
            "candidates_emitted": len(candidates),
            "skipped": {key: value for key, value in skipped.items() if key != "scanned-files"},
            "truncated_rules": list(truncated),
        },
        "candidates": [asdict(candidate) for candidate in candidates],
    }
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True)


def list_rules() -> str:
    lines = [
        "| Rule | Category | Priority hint | Languages | Review question |",
        "| --- | --- | --- | --- | --- |",
    ]
    for current_rule in RULES:
        lines.append(
            "| "
            + " | ".join(
                (
                    current_rule.rule_id,
                    current_rule.category,
                    current_rule.priority_hint,
                    ", ".join(sorted(current_rule.languages)),
                    current_rule.review_question,
                )
            )
            + " |"
        )
    return "\n".join(lines)


def self_test() -> None:
    examples = {
        "swift-forced-try": (frozenset(("swift",)), "let value = try! decode(payload)"),
        "swift-continuation": (
            frozenset(("swift",)),
            "return await withCheckedContinuation { continuation in",
        ),
        "kotlin-stable-ref": (frozenset(("kotlin",)), "val ref = StableRef.create(owner)"),
        "sync-dispatch": (frozenset(("objc",)), "dispatch_sync(queue, ^{"),
        "unsafe-c-copy": (frozenset(("c",)), "strcpy(destination, source);"),
    }
    for expected_rule, (languages, source) in examples.items():
        matches = {
            current_rule.rule_id
            for current_rule in RULES
            if languages.intersection(current_rule.languages) and current_rule.expression.search(source)
        }
        if expected_rule not in matches:
            raise AssertionError(f"{expected_rule} did not match its self-test source")

    code, in_block = strip_comments("let value = try! decode(payload) // try! ignored", False)
    if in_block or "try! decode" not in code or "ignored" in code:
        raise AssertionError("line-comment stripping failed")
    code, in_block = strip_comments("/* try! hidden */ let value = 1", False)
    if in_block or "try! hidden" in code or "let value" not in code:
        raise AssertionError("block-comment stripping failed")
    code, _ = strip_comments('let message = "try! is documentation"', False)
    if "try!" in code:
        raise AssertionError("string-literal stripping failed")


def positive_integer(raw_value: str) -> int:
    value = int(raw_value)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return value


def parse_arguments(arguments: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect lexical iOS stability review candidates from KNTR sources.",
    )
    parser.add_argument(
        "--scope",
        action="append",
        default=[],
        metavar="PATH",
        help="Repository path to scan; repeat for multiple paths. Required unless --changed is used.",
    )
    parser.add_argument(
        "--changed",
        action="store_true",
        help="Scan files changed from HEAD plus untracked, non-ignored files.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "--max-per-rule",
        type=positive_integer,
        default=50,
        help="Maximum emitted matches per rule (default: 50).",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include test source sets and test directories.",
    )
    parser.add_argument(
        "--include-generated",
        action="store_true",
        help="Include files carrying a generated-code marker.",
    )
    parser.add_argument("--list-rules", action="store_true", help="Print the rule catalog and exit.")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic matcher tests and exit.")
    return parser.parse_args(arguments)


def main(arguments: Sequence[str]) -> int:
    options = parse_arguments(arguments)
    if options.list_rules:
        print(list_rules())
        return 0
    if options.self_test:
        self_test()
        print(f"self-test passed: {len(RULES)} rules")
        return 0
    if not options.scope and not options.changed:
        print("error: pass --scope PATH or --changed; whole-repository scans must be explicit", file=sys.stderr)
        return 2

    try:
        repo = repository_root()
        scopes = normalized_scopes(repo, options.scope)
        paths = candidate_paths(repo, scopes, options.changed)
        candidates, skipped, truncated = scan(
            repo,
            paths,
            include_tests=options.include_tests,
            include_generated=options.include_generated,
            max_per_rule=options.max_per_rule,
        )
    except (OSError, ScanError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if options.format == "json":
        print(render_json(candidates, scopes, options.changed, skipped, truncated))
    else:
        print(render_markdown(candidates, scopes, options.changed, skipped, truncated))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
