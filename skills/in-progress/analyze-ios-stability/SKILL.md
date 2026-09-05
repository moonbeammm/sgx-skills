---
name: analyze-ios-stability
description: Analyze KNTR iOS code and runtime evidence for stability risks across Swift, Objective-C, Objective-C++, Kotlin/Native/KMP, Compose, C, and C++. Use for proactive stability audits or investigations involving crashes and .ips/.crash reports, memory leaks/growth/OOM and Instruments traces, deadlocks/hangs/thread-safety, lifecycle or reentrancy faults, unsafe cross-language ownership, and structural problems that can cause production incidents.
---

# Analyze KNTR iOS Stability

Perform an evidence-first, read-only stability investigation. Treat source scanning as triage; prove a failure mechanism before calling a candidate a defect.

## Operating Contract

- Start read-only. Do not edit production code, configuration, experiments, or generated projects unless the user explicitly asks for a fix.
- Never use `rg`. Use `git ls-files`, `find`, `grep`, and the bundled scanner.
- Inspect the checked-in implementation and current worktree before reasoning from pasted snippets, old stacks, or remembered code.
- Preserve unrelated and untracked user changes. Do not clean, stage, reset, or rewrite them.
- Separate severity from confidence. A severe hypothetical is not a confirmed P0/P1.
- Do not promote a pattern match, lint warning, allocation count, virtual-memory reservation, or top crash frame into a root cause by itself.
- Exclude generated code, build outputs, vendored/third-party sources, fixtures, and tests unless the evidence points there or the user includes them.
- Follow call chains across Swift, Objective-C, Kotlin/Native, Compose, C, and C++; do not stop at a language bridge or framework frame.
- Match the user's language. Lead with the outcome and exact evidence, not generic iOS guidance.

## Load the Relevant Guidance

1. Read [kntr-ios-context.md](references/kntr-ios-context.md) before choosing repository paths or validation commands.
2. Read [risk-catalog.md](references/risk-catalog.md) before classifying or prioritizing findings.
3. Read [artifact-playbooks.md](references/artifact-playbooks.md) when a crash report, hang sample, jetsam log, memory graph, or Instruments trace is available.
4. Read [report-template.md](references/report-template.md) before producing the final audit report.

## Route the Request

Choose one primary mode while allowing evidence from the others:

| Mode | Typical input | First objective |
| --- | --- | --- |
| Crash | `.ips`, `.crash`, exception, stack, signal | Identify the terminating condition and first actionable application frame |
| Memory | `.trace`, memory graph, jetsam/OOM, repeated-growth report | Distinguish leak, retained cache, transient peak, fragmentation, and VM reservation |
| Hang/deadlock | spindump, sample, watchdog, frozen UI, thread dump | Build a wait-for chain and distinguish deadlock from blocking, starvation, or livelock |
| Proactive audit | module, app, diff, feature path | Inventory high-risk boundaries, then deeply prove the most credible candidates |
| Structure | repeated init, lifecycle fault, ownership ambiguity, brittle layering | Trace state ownership, idempotency, teardown symmetry, and dependency direction |

If the scope is broad, use two passes: first rank changed and high-risk modules; then deep-review a bounded set. State what was and was not inspected. Do not imply whole-repository coverage from a sampled audit.

## Investigation Workflow

### 1. Establish scope and revision

- Record the app/extension, module or path, scenario, OS/device, build type, revision, and available baseline.
- Inspect `git status --short` and relevant diffs without modifying them.
- Locate the owning `BUILD.bazel`, source sets, entry point, and direct dependents.
- Determine whether the code ships on iOS. Shared `commonMain` and `nativeMain` code can be iOS-critical even when no Swift file exists.
- For an incident, align the binary UUID/dSYM and source revision before trusting symbolic frames.

### 2. Build a candidate inventory

Use the bundled scanner only to create a review queue:

```bash
python3 .agents/skills/analyze-ios-stability/scripts/scan_stability_candidates.py --changed
python3 .agents/skills/analyze-ios-stability/scripts/scan_stability_candidates.py --scope <module-or-file>
```

Use `--format json` for machine-readable output and `--list-rules` to inspect coverage. Never report the number of scanner hits as the number of bugs.

Also inspect:

- initialization and teardown pairs;
- callers, callbacks, cancellation paths, and error paths;
- queue/actor/dispatcher transitions and shared mutable state;
- ownership transfers at Swift/Objective-C/Kotlin/Native/C boundaries;
- caches, observers, timers, display links, tasks, continuations, locks, and file/network handles;
- existing focused tests, lint rules, experiments, and incident guards.

### 3. Prove or downgrade each candidate

For every candidate, answer all of these:

1. **Reachability:** What production entry point reaches it on iOS?
2. **Trigger:** What concrete timing, input, lifecycle state, or resource pressure is required?
3. **Mechanism:** What exact invariant fails—ownership, bounds, thread confinement, lock order, cancellation, idempotency, or cleanup symmetry?
4. **Evidence:** Which stack, allocation/backtrace, thread state, source call chain, test, or reproduction supports it?
5. **Impact:** Crash, OOM, watchdog, UI freeze, corruption, repeated work, or maintainability-only risk?
6. **Alternative:** What benign explanation or guard could make it a false positive?
7. **Validation:** What smallest test or runtime measurement would confirm the diagnosis and the fix?

Assign the `E0`-`E4` evidence level defined in [risk-catalog.md](references/risk-catalog.md). If any of reachability, trigger, or mechanism is missing, label it `Candidate`, not `Finding`. Continue useful source analysis even when an artifact is incomplete, but name the missing evidence.

Assign exactly one primary `O` outcome and one primary `M` mechanism. Put secondary symptoms under impact instead of combining multiple outcome or mechanism codes.

### 4. Trace the root cause

- For crashes, start with the termination reason and crashed thread, then walk outward to ownership and lifecycle causes. A UIKit, allocator, or Kotlin runtime frame can be downstream damage.
- For memory, keep live allocations, persistent growth, resident, dirty, virtual, compressed, and physical footprint distinct. Compare the same scenario and time window against a baseline.
- For hangs, draw the queue/thread/lock dependency chain. Call something a deadlock only when a wait cycle or equivalent permanent dependency is supported by evidence.
- For repeated initialization or layout failures, trace why initialization ran again before optimizing the downstream frame.
- For pasted code, verify the current checkout first; commented, guarded, experiment-gated, or unreachable code changes runtime risk.

### 5. Prioritize independently from confidence

Use these severity levels:

- `P0`: widespread or safety/security-critical production failure requiring immediate containment.
- `P1`: reproducible crash, OOM, watchdog, corruption, or major flow outage in a meaningful population.
- `P2`: bounded stability defect, credible leak/growth, race, or lifecycle fault with limited reach.
- `P3`: preventive hardening or structural debt without a demonstrated incident path.

Use these confidence levels:

- `Confirmed`: E4 causal evidence from a reproducer, sanitizer, fault injection, or controlled A/B validation.
- `High`: complete source mechanism and reachable call path, with only runtime confirmation missing.
- `Medium`: credible mechanism with a material unresolved assumption.
- `Low`: pattern candidate or weak correlation; keep outside the main findings list.

### 6. Recommend the smallest safe correction

- Fix the earliest violated invariant, not only the terminal frame.
- Prefer explicit ownership, idempotent lifecycle, structured concurrency, cancellation propagation, bounded caches, and consistent lock ordering.
- Keep recommendations compatible with KNTR source-set, Bazel, DI, and api/impl rules.
- Avoid broad rewrites when a narrow ownership or sequencing correction is sufficient.
- When proposing an experiment-gated fix, keep the non-hit legacy path structurally and behaviorally unchanged unless the user requests migration.
- Include containment, durable fix, regression test, and observability when they materially differ.

### 7. Validate proportionally

- Derive the smallest valid Bazel target from the nearest `BUILD.bazel`; never invent a target name.
- Use `./bazel-wrapper`, the correct iOS config, and `--experimental_convenience_symlinks=clean`.
- After Kotlin changes, run scoped `./ktlint` before a Bazel build or test.
- Use a focused unit/UI test, reproducer, sanitizer, Memory Graph, Leaks/Allocations, VM Tracker, Time Profiler, or thread sample according to the failure mechanism.
- Do not claim a fix is verified when only compilation or a scanner rerun passed.
- If runtime validation needs a device, dSYM, trace, account, or scenario unavailable locally, state the exact missing item and provide the next command/check.

## Reporting Rules

Use [report-template.md](references/report-template.md). Every main finding must include an exact path and line or an exact artifact frame/interval, trigger, mechanism, impact, confidence, recommendation, and validation.

Keep these sections distinct:

- confirmed/high-confidence findings;
- candidates needing evidence;
- ruled-out or benign signals;
- coverage gaps and next measurements.

If no issue is proved, say `No confirmed stability defect in the inspected scope`; do not say the code is safe. If source and runtime evidence disagree, present the disagreement and favor the evidence aligned to the shipping binary.
