# Runtime Artifact Playbooks

Use artifacts before source speculation. Record artifact identity, capture scenario, time window, device/OS, app version, UUID, and revision.

## Crash reports (`.ips` / `.crash`)

1. Confirm process, app version/build, OS/device, timestamp, incident identifier, and binary UUID.
2. Confirm symbolication quality and dSYM UUID. Do not guess symbols from offsets when binaries do not align.
3. Read exception type/codes, termination reason/namespace, signal, watchdog subtype, and application-specific information.
4. Identify the crashed or triggered thread. Inspect all threads when corruption, watchdog, or deadlock is plausible.
5. Find the first actionable application frame, then trace callers and ownership/lifecycle context in the matching source revision.
6. Separate the terminal operation from the earliest violated invariant.
7. Compare sibling incidents by mechanism, not only by top frame.

For `EXC_BAD_ACCESS`, distinguish use-after-free, invalid pointer, stack overflow, and prior memory corruption. For ObjC exceptions, capture exception name/reason and mutation/collection/KVC context. For watchdog termination, analyze main-thread state and termination subtype rather than calling it a crash in application code.

## Hang, watchdog, and suspected deadlock

Prefer a spindump, repeated process samples, Time Profiler/System Trace, or complete thread dump over a single screenshot.

1. Identify main-thread state and the user-visible blocked operation.
2. Record every waiting thread's primitive, owner/resource, and expected waker.
3. Map synchronous queue calls and lock acquisitions back to source.
4. Draw edges as `waiter -> resource/queue -> owner/waker`.
5. Require a cycle or impossible wake-up before declaring deadlock.
6. If samples change, classify CPU loop/livelock; if stable on I/O/work, classify blocking; if runnable work never schedules, investigate starvation.
7. Validate by reproducing under the same queue topology and adding signposts or lock/queue diagnostics where safe.

## Memory graph, leak, growth, and jetsam

1. Define the repeated scenario and phase boundaries: launch, enter page, play, leave, background, repeat, settle.
2. Capture a baseline under the same device/OS/build/scenario.
3. Separate cumulative allocations from still-live allocations and separate virtual from resident/dirty/physical footprint.
4. For object leaks, identify the shortest unexpected ownership path and the owner that should have released it.
5. For native/graphics growth, map allocation or VM backtraces to the decoder/cache/render/resource lifecycle.
6. For jetsam/OOM, inspect peak footprint, process limit, jetsam reason, concurrent phase, and extensions separately from the host app.
7. Repeat enough identical cycles to distinguish a rising slope from warm-up and cache plateau.

In Instruments, start with the trace table of contents rather than assuming schemas:

```bash
xcrun xctrace export --input <trace> --toc
```

Then export only relevant tables with the exact schema/xpath present in that trace. Keep the original trace immutable and place exports under `/tmp`.

For view/render memory, inspect IOSurface, CoreAnimation, CG raster, IOAccelerator, image decode, CoreVideo/CoreMedia, WebKit, and application caches. Confirm physical cost with VM resident/dirty or footprint before ranking a virtual region.

## Sanitizers and diagnostics

Choose the tool from the mechanism:

- Address Sanitizer: invalid native memory access and some use-after-free/overflow cases.
- Thread Sanitizer: data races; validate platform/target support and expect timing changes.
- Zombies: over-released ObjC objects; use for diagnosis, not normal performance measurement.
- Memory Graph / Leaks: ownership cycles and leaked allocations visible to the runtime.
- Allocations + VM Tracker: live allocation growth, native/graphics categories, resident and dirty pages.
- Guard Malloc / scribble / stack logging: focused allocator diagnosis with high overhead.
- Time Profiler / System Trace / signposts: long main-thread work, scheduling, queue contention, and phase attribution.

Do not combine high-overhead diagnostics indiscriminately. State how instrumentation changes timing, memory, or allocator behavior.

## Evidence alignment checklist

- Artifact binary matches dSYM and source revision.
- Scenario and time window are known.
- Baseline uses comparable build and conditions.
- Application frame/caller is resolved, not only framework category.
- Memory units distinguish cumulative/live/resident/dirty/virtual.
- Thread evidence includes the expected waker/owner.
- Recommendations map to the observed mechanism.

