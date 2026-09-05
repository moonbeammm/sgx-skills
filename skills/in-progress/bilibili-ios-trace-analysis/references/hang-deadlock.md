# Hang, Freeze, and Deadlock Analysis

Read this reference completely before diagnosing a Hang, Microhang, freeze, watchdog termination, lock wait, or suspected deadlock.

## Capture configuration

Choose the capture based on the question:

- Start with the **Hangs** template for user-visible stalls. It identifies Hang/Microhang intervals and the affected thread.
- Add **Time Profiler** with a short sampling interval to attribute CPU work inside each interval. Inspect the TOC's `time-sample`/`time-profile` metadata; `all-thread-states="NO"` means waiting-thread absence is not evidence.
- Add **System Trace** and enable waiting/all-thread-state stack recording when the suspected cause is a lock, semaphore, condition variable, synchronous dispatch, IPC, or I/O wait. The exact setting label varies by Xcode version, so confirm the resulting TOC instead of assuming it was captured.
- Enable all-thread stack collection when ownership may be on a background thread. A main-thread wait stack alone cannot identify the owner.
- Keep Points of Interest, os_log, and business signposts when available so the interval can be tied to a page phase, response, broadcast, first frame, or user action.
- For an intermittent freeze, capture several seconds before and after recovery. For a permanent freeze, pause the process in Xcode two or three times and save all-thread backtraces each time.
- For production watchdog exits, retain the `.ips` report. Check termination namespace/code, lifecycle phase, triggering thread, and symbolication, and distinguish watchdog termination from jetsam/OOM. The report proves the termination class and supplies a termination-time stack, but usually does not prove the entire preceding timeline or a lock cycle by itself.

`Heap Shot` and `Generations` belong to Allocations memory investigation. They do not add the thread-state evidence needed to diagnose a Hang.

## Trace-first workflow

1. Export the TOC and confirm the bundle is readable.
2. Export `potential-hangs` and `time-profile` serially. Export thread information, os_log, signposts, and lifecycle tables only when present.
3. Resolve `TRACE_SKILL_ROOT` as the directory containing the loaded `SKILL.md`, then run its `scripts/summarize_hangs.py` to associate samples with each interval and affected thread.
4. If the affected thread is predominantly Running with symbolized work, use the CPU quick path. If it is waiting, has no matching samples, or ends in a blocking primitive, stop CPU attribution and use the all-thread wait path below.
5. For waits, inspect every thread for the resource owner or the other edge of a cycle. Time Profiler affected-thread output alone is insufficient.
6. For synchronous containers such as notifications, event buses, delegates, or callback fan-out, descend to the expensive observer/callback.
7. Open source only for trace-proven frames and reconstruct `business trigger -> synchronous edge -> blocking or expensive work`.

Typical exports:

```bash
xcrun xctrace export \
  --input /path/to/file.trace \
  --toc \
  --output /tmp/name_toc.xml

xcrun xctrace export \
  --input /path/to/file.trace \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="potential-hangs"]' \
  --output /tmp/name_hangs.xml

xcrun xctrace export \
  --input /path/to/file.trace \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="time-profile"]' \
  --output /tmp/name_time_profile.xml

python3 "$TRACE_SKILL_ROOT/scripts/summarize_hangs.py" \
  --hangs /tmp/name_hangs.xml \
  --time-profile /tmp/name_time_profile.xml \
  --toc /tmp/name_toc.xml \
  --top 30
```

Copy exact XPaths from the TOC when track/detail names differ. Do not guess a schema that is not present.

## CPU quick path versus all-thread wait path

The summarizer is deliberately an affected-thread CPU attribution tool:

- Use it when the Hangs row supplies a resolvable TID and Time Profiler has samples for that thread.
- Predominantly `Running` samples plus repeated executable leaf work support a CPU-bound stall classification.
- No matching samples, `all-thread-states="NO"`, a wait primitive, or a normal RunLoop wait does not identify an owner and must branch to the workflow below.

For a lock/deadlock candidate:

1. Export `thread-info` and preserve the exact scheduling/thread-state tables shown by the TOC:

```bash
xcrun xctrace export \
  --input /path/to/file.trace \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="thread-info"]' \
  --output /tmp/name_thread_info.xml
```

2. In Instruments, select the exact Hang interval, expand all threads in System Trace/CPU Strategy, and record the main-thread wait primitive plus candidate owner stacks. If waiting-thread stacks are absent, re-record with waiting/all-thread-state collection enabled.
3. For a permanent freeze, pause in Xcode and run `thread backtrace all`. Resume briefly when possible, pause again, and capture at least two or three snapshots. Stable stacks across snapshots establish stable waiting; changing stacks usually indicate contention or progress.
4. Write one wait-for edge per proven dependency. Identify the lock, queue, token, semaphore, or condition and the thread that owns or can satisfy it.
5. Report **confirmed deadlock** only if the edges close a stable cycle or prove completion impossible. Otherwise report **lock contention** or **suspected deadlock** and name the missing owner/edge.

Do not infer an owner from CPU weight. A waiting owner may have little or no Time Profiler weight.

## Classification decision tree

Classify each interval independently.

### 1. Main thread is mostly Running

Evidence:

- Thread state is predominantly `Running`.
- Samples repeatedly land in parsing, layout, drawing, image decode, model conversion, sorting, logging/formatting, runtime initialization, or synchronous observer code.
- Sampled weight concentrates in an executable subtree rather than a wait primitive.

Classification: **CPU-bound main-thread stall**. It is a Hang, but not a deadlock.

Look for a synchronous entrypoint and its dominant leaf or observer. Move work off the main thread, reduce fan-out, batch updates, cache conversion, or eliminate repeated formatting as appropriate.

### 2. Main thread is blocked in synchronous I/O or IPC

Evidence:

- Repeated stacks end in file, database, keychain, network, XPC/Mach message, or other blocking calls.
- Thread state is waiting or blocked for a substantial part of the interval.
- The call is made synchronously from the main thread.

Classification: **blocking I/O/IPC stall**. Do not label it a deadlock unless a stable cycle is also proven.

### 3. Main thread waits on a lock, semaphore, condition, or sync dispatch

Evidence:

- Repeated main-thread stacks show `os_unfair_lock`, mutex, rwlock, semaphore, condition wait, `dispatch_sync`, `dispatch_group_wait`, `dispatch_once`, Swift concurrency blocking, or an equivalent primitive.
- Samples remain stable across the interval or across repeated debugger pauses.

Next step: identify the resource and inspect other threads.

- If another thread owns the resource and is still progressing, classify **lock contention / dependency wait**.
- If the owner is blocked back on the main thread or on another resource that closes a stable cycle, classify **confirmed deadlock**.
- If ownership cannot be recovered, classify **suspected lock wait**, state the missing owner evidence, and do not claim deadlock.

Seeing a lock symbol, `dispatch_once`, or `dispatch_sync` in one stack is not enough to prove a deadlock.

### 4. Threads are Running but repeat without progress

Evidence:

- One or more threads remain runnable and consume CPU.
- Repeated stacks or program-state evidence show retry/spin behavior without forward progress.

Classification: **livelock or spin candidate**. Confirm with repeated stacks, CPU use, and a stable no-progress condition. It is not a lock-wait deadlock.

### 5. Watchdog termination

Evidence:

- The `.ips` termination namespace/code or event identifies a watchdog class such as launch, resume, suspend, scene update, or event handling.
- A termination-time stack identifies what the sampled thread was doing at kill time.

Classification: **watchdog termination**, plus a narrower mechanism only when trace or multi-stack evidence supports it. A single `.ips` stack should not be expanded into an unproven deadlock narrative.

## Proving a deadlock

A confirmed deadlock report should establish all of the following:

1. **Stable waiting:** the involved threads show the same blocked dependency across multiple samples or debugger pauses.
2. **Resource or synchronous edge:** identify the lock, queue, semaphore, condition, once token, join, callback, or equivalent dependency.
3. **Owner/waiter relationship:** show which thread holds or can satisfy the resource.
4. **Cycle or impossible completion:** demonstrate an edge back to an already waiting thread/resource, or another condition that makes completion impossible.

Use a compact wait-for graph when evidence permits:

```text
Main Thread --waits on Queue A--> Worker Thread
Worker Thread --dispatch_sync main--> Main Thread
```

If only the first edge is known, report it as contention or suspected deadlock and list the missing edge.

## Time and stack semantics

Keep these metrics separate:

- `potential-hangs.duration` is elapsed wall time for the detected interval.
- `time-profile.weight` is sampled/recorded thread time represented by samples. It is not the Hang duration.
- Sample counts depend on profiler cadence and gaps. They are evidence density, not milliseconds unless converted from weight.
- Inclusive frame weight means a frame appeared anywhere in a sample stack.
- Leaf/exclusive weight means the frame was at the top of the sampled stack.
- Parent and child inclusive weights overlap. Never add them.
- Recursive occurrences of the same symbol in one sample must count once for inclusive aggregation.

An 892 ms Hang can legitimately contain much less than 892 ms of Time Profiler weight. State both values rather than assigning the full wall time to one subtree.

## Synchronous broadcast and callback fan-out

Notification centers, event buses, delegates, routers, and callback arrays commonly appear as large inclusive containers. The container proves synchronous fan-out, not that its own implementation performed all the work.

Trace the path at this granularity:

```text
network response / page event
  -> synchronous broadcast or dispatcher
    -> observer or callback
      -> model conversion / diff / layout / render / logging
```

Rank the observers beneath the container by sampled weight. Report the heaviest trace-proven observer separately. Fixing the dispatcher boundary may reduce main-thread blocking, while the expensive observer can still remain expensive on its new execution context; make that boundary explicit.

## Source correlation

After the trace establishes a path:

- Locate the exact method or symbol in the checkout.
- Find the business caller, registration site, observer, and synchronous boundary.
- Check whether execution is guaranteed on the main thread.
- Check for hidden synchronous work: parsing, model mapping, collection copies, locks, disk reads, image decode, layout invalidation, logging, or nested notifications.
- Preserve the distinction between the trace-proven runtime path and static candidates that were not sampled.

Do not begin with a broad source scan and then retrofit the trace to a favorite hypothesis.

## Export failures and recovery

For exit `139` or `Missing features`, first stop concurrent export/remodel work and retry the TOC once serially. Identify the named missing feature/package from the error. Only for a Hangs feature-registration failure should the Hangs package be supplied explicitly:

```bash
XCODE_DEVELOPER_DIR="$(xcode-select -p)"
HANGS_PACKAGE="${XCODE_DEVELOPER_DIR%/Contents/Developer}/Contents/Applications/Instruments.app/Contents/Packages/Hangs.instrdst"

xcrun xctrace remodel \
  --input /path/to/file.trace \
  --output /tmp/name_remodeled.trace \
  --package "$HANGS_PACKAGE"
```

Then export from the remodeled copy. `xctrace export` itself does not accept `--package`.

`Can't add the same store twice` is acceptable only if the same remodel command also reports completion and a saved output. Never modify the original trace.

For another missing feature, locate the matching Instruments package rather than substituting `Hangs.instrdst`.

For `Trace is malformed - run data is missing.`, inspect `RunIssues.storedata` and try only one remodeled copy. If the same malformed error repeats, stop CLI retries and use Instruments to reopen/re-save, or re-record.

The warning about signpost intervals with backdated timestamps being hidden until immediate-mode recording stops concerns live visualization. It does not by itself prove a stalled save or corrupt trace.

## Reporting template

Use this structure for each interval or grouped mechanism:

```markdown
### Conclusion and classification

- Classification: CPU stall / blocking I/O / lock contention / suspected deadlock / confirmed deadlock / livelock candidate / watchdog.
- Interval: start-end, wall duration, affected thread.

### Trace evidence

- Hangs row and type.
- Thread-state distribution, sample count, and sampled weight.
- Dominant inclusive containers and leaf/exclusive work.
- For waits: owner threads and wait-for edges.

### Trigger and source path

- Business event -> synchronous edge -> heavy observer or blocking primitive.
- Trace-proven source locations.
- Static candidates kept separate.

### Recommendation and boundary

- Highest-priority fix.
- What the fix should reduce.
- Work or risk it will not remove.
- Missing evidence needed to raise confidence.
```

## Evidence boundaries

- A Hangs interval proves a responsiveness stall, not its cause.
- No `potential-hangs` rows do not rule out a freeze; the detector threshold, capture gaps, or a permanent freeze may prevent a completed interval from appearing.
- A Time Profiler stack proves sampled presence, not continuous execution for the entire interval.
- A TOC with `record-waiting-threads="0"` or `all-thread-states="NO"` cannot exclude waits from missing samples.
- A wait primitive proves a wait at that sample, not ownership or a cycle.
- `mach_msg` in a normal idle RunLoop is not by itself a blocking-I/O or deadlock finding.
- A main-thread wait plus an owner stack can prove contention; a closed stable wait-for cycle is needed for a deadlock.
- A source path that was not sampled remains a candidate.
- No `os-log` table means business attribution may remain bounded even when the thread mechanism is clear.
