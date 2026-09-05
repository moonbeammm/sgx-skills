# Stability Audit Report Template

Write in the user's language. Keep exact symbols, exception strings, and commands unchanged.

## Outcome

State the highest-priority conclusion, inspected scope, and evidence quality in two to four sentences. Say whether findings are confirmed, source-proven, or candidate-only.

## Findings

Order by severity, then confidence. Omit this section when there are no confirmed or high-confidence findings.

| ID | Severity | Confidence | Evidence | Classification | Location | Result |
| --- | --- | --- | --- | --- | --- | --- |
| IOS-STAB-001 | P1 | Confirmed | E4 | O1/M1 | `path/file.swift:123` or artifact frame | One-sentence mechanism and impact |

For each finding, provide:

### IOS-STAB-001 — Short mechanism-oriented title

- **Evidence:** Exact frame, allocation/backtrace, thread state, or source call chain.
- **Classification:** Exactly one primary outcome, one primary mechanism, and the language boundary, for example `O3/M3 · Swift -> C++`. Put secondary symptoms under impact.
- **Trigger:** Input, ordering, lifecycle state, repetition, or pressure required.
- **Mechanism:** The violated invariant and why existing guards do not prevent it.
- **Guards/contrary evidence:** Strongest existing safety mechanism or benign alternative.
- **Falsifier:** The concrete observation that would disprove this diagnosis.
- **Impact/reach:** User-visible result and known population/scope; do not invent frequency.
- **Recommendation:** Smallest durable correction, plus containment if needed.
- **Validation:** Focused test/reproducer and runtime measurement.
- **Residual risk:** Assumptions, compatibility, rollout, or performance trade-offs.

## Candidates needing evidence

List credible but unproved candidates separately:

| Candidate | Signal | Missing proof | Next check |
| --- | --- | --- | --- |

Do not assign an incident severity unless impact and reach are supported. A severity hint from the scanner is not a finding severity.

## Ruled out or benign signals

Record high-value false positives so reviewers do not repeat the same work. Examples: unreachable platform code, balanced cleanup elsewhere, bounded cache plateau, virtual-only region, or `sync` proven to target a different queue.

## Structural recommendations

Include only recommendations tied to concrete ownership, lifecycle, concurrency, dependency, or observability weaknesses. Separate P3 maintainability work from incident fixes.

## Coverage and verification

- **Inspected:** files/modules/artifacts and revision.
- **Not inspected:** explicit exclusions and why.
- **Executed:** exact commands/tests and outcomes.
- **Not executed:** device, dSYM, trace, account, build, or scenario gaps.
- **Next measurements:** smallest set that would change confidence or priority.

## Quality checks before sending

- Every main finding has an exact location and failure mechanism.
- Severity, confidence, and evidence level are independent.
- Every finding/candidate has exactly one primary `O` code and one primary `M` code.
- Runtime claims come from aligned artifacts or are labeled unverified.
- Candidate scan hits are not counted as bugs.
- Memory metrics use correct semantics.
- A deadlock has a supported wait cycle or is labeled a stall/hang.
- The recommendation fixes the earliest violated invariant.
- The report does not claim whole-repository safety from partial coverage.
