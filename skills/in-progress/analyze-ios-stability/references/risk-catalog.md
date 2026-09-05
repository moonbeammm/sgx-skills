# iOS Stability Risk Catalog

Use this catalog as review prompts, not as a list of automatic defects. For every signal, prove reachability, trigger, mechanism, and impact.

## Classification model

Classify each issue by one external outcome and one root mechanism. Add the language/bridge as a tag; do not duplicate one root cause under every symptom.

| Outcome | Meaning |
| --- | --- |
| `O1` | Crash or abnormal termination: trap, ObjC exception, bad access, C++ terminate, watchdog, or jetsam |
| `O2` | Memory: leak, retained growth, native/graphics budget, peak, or fragmentation |
| `O3` | Hang or responsiveness: deadlock, blocking, livelock, starvation, priority inversion, or timeout |
| `O4` | Thread safety or state corruption: race, stale callback, duplicate completion, cancellation race, or off-main UI |
| `O5` | Structural stability risk: non-idempotent init, lifecycle coupling, hidden blocking, error loss, or observability gap |

| Mechanism | Meaning |
| --- | --- |
| `M1` | Memory safety and ownership: UAF, bounds, double release, or ARC/CF/RAII imbalance |
| `M2` | Lifecycle and cancellation: task, coroutine, timer, observer, StableRef, or callback outlives its owner |
| `M3` | Synchronization and scheduling: lock order, queue reentry, semaphore/condition, actor, or dispatcher |
| `M4` | Cross-language contract: nullability, exception, thread, ownership, callback count, cancellation, or allocator domain |
| `M5` | Initialization and state machine: repeated setup, reentry, partial initialization, or invalid transition |
| `M6` | UIKit/Compose lifecycle: main-thread rule, effect cleanup, snapshot state, or host controller lifetime |
| `M7` | Resource budget: image/video/WebKit/CoreAnimation/native buffer or unbounded cache |
| `M8` | Architecture and observability: dependency direction, implicit side effect, generated drift, logging, or test gap |

Example: `O3/M3 · Swift -> C++` or `O2/M2 · Kotlin/Native <-> ObjC`.

## Evidence levels

| Level | Meaning | Reporting rule |
| --- | --- | --- |
| `E0` | Lexical scan or generic dangerous pattern | Review queue only; never a finding |
| `E1` | Real code inspected, but reachability or trigger remains unproved | Candidate needing evidence |
| `E2` | Shipping target/source set, production call chain, guards, and trigger are statically established | High-confidence static risk; do not claim it occurred |
| `E3` | Aligned crash/trace/log/sample observes the path, but causal alternatives remain | Runtime-observed, not confirmed root cause |
| `E4` | Reproducer, sanitizer, fault injection, or controlled A/B establishes causality | Confirmed defect |

Keep evidence, confidence, and severity independent. P0 normally requires E3/E4. A P1 claim should normally have at least E2. An E1 candidate can have high potential impact but remains a candidate. Pure structure without a demonstrated failure path is normally P3.

## Crash and corruption

| Surface | Review signals | Evidence required before reporting |
| --- | --- | --- |
| Swift | `try!`, `as!`, force unwraps, unchecked indices, `fatalError`, unowned captures, unsafe pointers | Show the input/lifecycle state that violates the assumption and the reachable production caller |
| Objective-C | collection bounds/nil insertion, invalid selectors, KVC/KVO imbalance, dangling delegates, block ABI misuse, C API contracts | Trace the receiver/object lifetime and exact exception, signal, or invalid access path |
| Kotlin/Native | unchecked casts/assertions, uncaught exception crossing an exported boundary, invalid native handles, cancellation swallowed as success | Trace the exported call/callback and verify how exceptions or cancellation are translated at that boundary |
| C/C++ | buffer bounds, use-after-free, double release, integer overflow used for allocation, lifetime across async callbacks, data races | Establish ownership and the concrete read/write/free order; prefer sanitizer or crash-address evidence |
| UI/lifecycle | repeated module setup, duplicate child/controller insertion, update after disposal, reentrant state transition | Trace the lifecycle entry points and show the invalid second transition or stale owner |

Do not treat framework or allocator frames as root cause without walking back to the application ownership or mutation that corrupted state.

## Memory leak, growth, and OOM

Review these ownership pairs:

- Swift/ObjC closure or block capture -> owner -> callback/token/task -> closure.
- `Timer`, `CADisplayLink`, `DispatchSource`, notification block token, KVO observation, delegate, task, or subscription -> cancellation/invalidation/removal.
- Core Foundation `Create`/`Copy`, bridging retains, `Unmanaged`, C allocations, image/pixel buffers -> balanced release/free on every success and error path.
- Kotlin/Native `StableRef.create`, pinned objects, native callbacks, ObjC/Swift wrappers -> deterministic `dispose`/unpin/unregister.
- UIKit controller/view -> Compose host -> remembered state/coroutine -> UIKit controller/view.
- Cache key/cardinality/cost -> eviction, memory-warning handling, background transition, and process-specific budget.

Classify observed memory correctly:

- **Leak:** an object/resource has no legitimate future use but remains owned.
- **Persistent growth:** live or resident memory rises across repeated identical cycles and does not return to an expected plateau.
- **Cache:** retained memory remains reachable by policy; it is still a risk if unbounded or incompatible with the process budget.
- **Transient peak:** memory returns after the phase; peak can still cause jetsam and needs peak reduction.
- **Fragmentation/reservation:** address space or allocator pages grow without equivalent live payload; validate resident/dirty/physical footprint.

Do not equate virtual bytes or cumulative allocation bytes with current physical memory. For render/image issues, cross-check IOSurface, CoreAnimation, CG raster, IOAccelerator, image decode, CoreVideo/CoreMedia, WebKit, and app caches against resident/dirty and the scenario timeline.

## Deadlock, hang, and concurrency

Build a wait-for graph using queues, threads, actors, locks, semaphores, and continuations.

High-value signals:

- synchronous dispatch to the current serial queue or a queue that synchronously waits back;
- inconsistent lock ordering, nested callbacks while holding a lock, or lock acquisition during deinit/cancellation;
- main-thread semaphore, condition, future, file/network wait, sleep, synchronous I/O, or `runBlocking`;
- actor/queue isolation escaped by mutable references or callbacks invoked on undocumented executors;
- checked/unsafe continuation not resumed exactly once on every terminal path;
- coroutine cancellation swallowed, long non-suspending work on a constrained dispatcher, or scope lifetime longer than its UI owner;
- C/ObjC callbacks that race teardown or Kotlin/Native callbacks that outlive disposed stable state.

Use precise labels:

- **Deadlock:** permanent dependency cycle or equivalent impossible wake-up.
- **Blocking/stall:** progress resumes when I/O, work, or a timeout completes.
- **Starvation:** runnable work cannot obtain an executor/resource.
- **Livelock:** participants run but repeatedly prevent progress.
- **Race:** unsynchronized ordering permits an invalid state; a race is not automatically a deadlock.

Never infer a deadlock from the presence of `sync`, `lock`, or `wait` alone.

## Lifecycle and structure

Look for structural conditions that amplify incidents:

- initialization that is not idempotent or teardown that does not mirror setup;
- hidden global mutable state, ambiguous singleton ownership, or service lifetime coupled to a view;
- error/cancellation converted into success, empty recovery, retry without bound/backoff, or callback invoked more than once;
- shared state modified from multiple language runtimes without a single concurrency contract;
- app/common code depending directly on an implementation target, making lifecycle and replacement unclear;
- platform behavior placed in the wrong source set or duplicated in divergent platform implementations;
- very large coordinator/controller/state machine with mixed ownership, rendering, I/O, and concurrency responsibilities;
- experiment branches that share newly changed helpers and unintentionally alter the non-hit legacy path;
- missing observability at a risky boundary: no state, queue, owner, allocation category, or correlation identifier.

Report maintainability-only concerns as P3 unless a concrete incident mechanism raises them.

For every finding, record the strongest existing guard or contrary evidence and a **falsifier**: the concrete observation that would disprove the diagnosis.

## Severity versus confidence examples

| Evidence | Severity | Confidence |
| --- | --- | --- |
| Aligned crash report and source show a reachable invalid access in a common flow | P1 | Confirmed |
| Complete lock-order cycle exists in production call paths but has not reproduced | P1 or P2 by reach | High |
| `Timer.scheduledTimer` appears with no local invalidation, but owner/lifetime is unknown | Not yet assigned; Candidate | Low or Medium |
| Large virtual VM region without resident/dirty growth | Usually no finding | High confidence that virtual size alone is insufficient |
| God-object structure with no failure path | P3 | Medium or High |

## Recommendation quality bar

For each finding, include:

- immediate containment when incident risk is active;
- smallest durable ownership, ordering, bounds, or lifecycle correction;
- regression test or deterministic reproducer;
- runtime verification that measures the failed invariant;
- observability needed to detect recurrence;
- trade-offs and any residual risk.

Avoid generic advice such as “use weak”, “add a lock”, “clear the cache”, or “refactor this class” without naming which ownership edge, invariant, policy, or responsibility must change.
