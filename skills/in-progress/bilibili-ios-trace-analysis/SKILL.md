---
name: bilibili-ios-trace-analysis
description: Analyze Bilibili iOS Instruments .trace bundles using the Codex session's initial working directory as the source root. Covers hangs, microhangs, freezes, suspected deadlocks, main-thread stalls, Time Profiler and thread-state evidence, memory/VM/Allocations/Metal, os_log, Memory Tag 246, playback growth, image decode, BFCLog, WebKit/JSC, and Kotlin/Native memory. Use for trace triage, top-N reports, timestamp and source correlation, malformed bundles, or choosing Instruments capture settings.
---

# Bilibili iOS Trace Analysis

Analyze Bilibili iOS traces with trace evidence primary and source inspection secondary.

## Path contract

- At the start of the task, capture the Codex session's current working directory with `PROJECT_ROOT="$(pwd -P)"`. Treat that fixed value as the project/source root for the whole analysis, even if later commands change directory. Do not replace it with a Git top-level directory, the trace's parent, or the Skill directory unless the user explicitly requests a different root.
- Resolve user-provided relative trace and source paths against `PROJECT_ROOT`. Preserve absolute paths exactly as provided.
- Search source only inside `PROJECT_ROOT`. If Codex was launched outside the relevant checkout, state the source-correlation boundary instead of searching arbitrary home-directory locations.
- Resolve and assign `TRACE_SKILL_ROOT` as the absolute directory containing this `SKILL.md`, using the path from which the Skill was loaded, before running examples that reference the variable. Do not assume a username, `$HOME/.codex`, or that the Skill lives under `PROJECT_ROOT`.
- Keep `PROJECT_ROOT` and `TRACE_SKILL_ROOT` separate: the former is user code; the latter contains this Skill's scripts and references.

## Core contract

- Start with the direct conclusion in Chinese when the request is Chinese.
- Anchor claims to timestamps, tables, categories, thread states, stacks, callers, or source lines.
- Separate trace evidence, source evidence, and inference.
- Treat `candidate` and `confirmed finding` differently.
- Run heavy `xctrace` exports serially. Never start parallel export pipelines.
- Write exports and remodeled copies under `/tmp`; never modify the original `.trace`.
- Prefer `/usr/bin/grep`, `/usr/bin/find`, and purpose-built parsers. Do not depend on `rg` on this Mac.
- Validate TOC readability before deep analysis.

## Route to the right workflow

- For Hang, Microhang, freeze, watchdog, main-thread stall, lock wait, or suspected deadlock, read [references/hang-deadlock.md](references/hang-deadlock.md) completely before diagnosing.
- For exported Hangs and Time Profiler XML, run the bundled script from `TRACE_SKILL_ROOT` before manually reading stacks.
- For memory, VM, Metal, playback growth, Tag 246, image decode, or log amplification, follow the sections below.
- For a malformed or crashing export, follow `Export recovery` before retrying.

## Standard trace workflow

1. Validate the bundle and inspect routing metadata:

```bash
xcrun xctrace export \
  --input /path/to/file.trace \
  --toc \
  --output /tmp/name_toc.xml
```

2. Read the TOC and export only tables that actually exist. Common data-table exports:

```bash
xcrun xctrace export \
  --input /path/to/file.trace \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="os-log"]' \
  --output /tmp/name_os_log.xml

xcrun xctrace export \
  --input /path/to/file.trace \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="potential-hangs"]' \
  --output /tmp/name_hangs.xml

xcrun xctrace export \
  --input /path/to/file.trace \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="time-profile"]' \
  --output /tmp/name_time_profile.xml
```

3. For track/detail tables, copy the exact XPath from the TOC instead of guessing:

```bash
xcrun xctrace export \
  --input /path/to/file.trace \
  --xpath '/trace-toc/run[@number="1"]/tracks/track[@name="Allocations"]/details/detail[@name="Allocations List"]' \
  --output /tmp/name_alloc_list.xml

xcrun xctrace export \
  --input /path/to/file.trace \
  --xpath '/trace-toc/run[@number="1"]/tracks/track[@name="Allocations"]/details/detail[@name="Statistics"]' \
  --output /tmp/name_alloc_stats.xml

xcrun xctrace export \
  --input /path/to/file.trace \
  --xpath '/trace-toc/run[@number="1"]/tracks/track[@name="VM Tracker"]/details/detail[@name="Regions Map"]' \
  --output /tmp/name_vm_regions.xml
```

4. Aggregate before reading rows. Slice a narrow exact window, then nearby context, then the business phase.

5. Correlate the exported evidence with source only after identifying a trace-proven caller.

## Hang quick path

Export `potential-hangs` and `time-profile`, then run:

```bash
python3 "$TRACE_SKILL_ROOT/scripts/summarize_hangs.py" \
  --hangs /tmp/name_hangs.xml \
  --time-profile /tmp/name_time_profile.xml \
  --toc /tmp/name_toc.xml \
  --top 30
```

Use `--hang-index 5` to focus on one interval. The script resolves xctrace `id/ref` values, matches the affected thread, reports sampled states and weights, and prints inclusive and leaf stacks.

Interpret the output correctly:

- A Hangs interval is wall time.
- Time Profiler weight is sampled running or recorded thread time, not the interval duration.
- Inclusive frames are nested. Never add parent and child weights.
- A long `dispatchEvent` or notification frame identifies a synchronous container; inspect the observer below it to find the actual work.
- Do not call CPU-heavy running work a deadlock.
- This is the affected-thread CPU attribution path. If samples are missing, waiting, or end in a blocking primitive, branch to the all-thread owner/cycle workflow in `references/hang-deadlock.md`; this script alone cannot prove a deadlock.

## Memory terminology

- `Allocations List`: recorded allocation rows. Liveness depends on the recording/export; for generation or end-state questions inspect and filter `live=true` when that field exists.
- `Allocations Statistics persistent-bytes`: final still-live accumulation, not a time series and not process RSS.
- `VM Tracker Regions Map`: end-state resident, dirty, swapped, and virtual bytes by region. Verify the exported table contains rows; TOC presence alone is not data.
- `metal-resource-allocations`: Metal allocation and release churn.
- `metal-current-allocated-size`: current/peak Metal allocation state; pair it with churn tables.
- `GC.lastGCInfo`: Kotlin logical heap-after-GC, not process RSS or Tag 246 resident memory.
- Crash logs containing stacks and `mem_free` cannot reconstruct resident, dirty, swapped, virtual, or Tag 246 values.

## Memory quick path

Verify exported row counts before interpreting a table. For attribute-style Allocations List XML, aggregate a time window without treating explicitly freed rows as live:

```bash
perl -ne 'sub sec { my($t)=@_; $t =~ /^(\d+):(\d+)\.(\d+)\.(\d+)/; return $1*60+$2+$3/1000+$4/1000000; }
while (/<row\s+([^>]+)\/>/g) {
  $a=$1; next unless $a =~ /timestamp="([^"]+)"/; $v=sec($1);
  next unless $v >= 19.0 && $v <= 19.5;
  next if $a =~ /live="(?:false|0)"/;
  ($size)=$a =~ /size="(\d+)"/; ($cat)=$a =~ /category="([^"]*)"/;
  ($caller)=$a =~ /responsible-caller="([^"]*)"/; ($lib)=$a =~ /responsible-library="([^"]*)"/;
  $key="$caller | $cat | $lib"; $sum{$key}+=$size; $count{$key}++; $total+=$size;
}
END { printf "total %.2f MiB\n", $total/1048576;
  for $k (sort {$sum{$b}<=>$sum{$a}} keys %sum) {
    printf "%.2f MiB count=%d | %s\n", $sum{$k}/1048576, $count{$k}, $k;
  }
}' /tmp/name_alloc_list.xml
```

Adjust the window to the user's exact phase. If rows are nested rather than attribute-style, use a purpose-built XML parser. For Generations/Heap Shot analysis, compare stable generation boundaries and retain only rows proven live at the boundary.

## os_log correlation

- Locate business events, request start/completion, first frame, manual GC, and custom markers.
- Parse one row at a time; protobuf prefixes and XML escaping make broad text matches misleading.
- Correlate `BFCLogLargeMessage`, IGNET request ID and URL, Foundation string-format warnings, and allocation callers at the same timestamp.
- If no normal `os-log` table exists, state the attribution boundary and continue with available tables.

## Memory Tag 246 and Kotlin

- Split by business phase: launch, pre-play, first frame, resolver, after GC, and back home.
- Filter `Allocations List` by `category="VM: Memory Tag 246"` and timestamp boundaries.
- Use Statistics for final still-live totals and VM Tracker for end-state physical/virtual composition.
- Require repeated growth across stable phase boundaries before calling a leak.
- Treat repeated 128 KiB `kotlin::alloc::SafeAlloc` regions as Kotlin/Native heap allocation, not a business object identity.

## Playback memory

Separate likely contributors:

- Playback core: AVPlayer, IJK, AudioToolbox, CoreMedia, IOSurface, Metal, and thread stacks.
- Page UI: CALayer, CoreAnimation, CG raster, images, collection views, Swift, and Objective-C objects.
- Danmaku: services, render layers, text, and raster allocations.
- Logs: BFCLog, DDLog, CFString, and DEBUG protobuf dumps.

Preserve user-provided phase boundaries such as first frame, resolver completion, and returning home.

## Image decode and network source

- Correlate CG/ImageIO decode callers with IGNET or URLSession rows.
- Inspect both request creation and the decode sink.
- If URL equality misses, check transformed URLs, escaping, image suffix normalization, and wrapper conversion timing.

## BFCLog and DDLog amplification

Separate:

- Trigger: the business call site that logs a large object.
- Amplifier: formatting copies, raw-string conversions, dual sinks, and DDLog CFString creation.
- Scope: DEBUG-only call sites are not release behavior, but shared log-system amplification may affect production.

## Export recovery

Classify the failure before retrying:

- `Trace is malformed - run data is missing.`: inspect `RunIssues.storedata`. Try one remodeled copy. If remodel repeats the same error, stop CLI retries and use Instruments UI re-save/reopen or re-record.
- Exit `139` or `Missing features`: first ensure no other `xctrace` export/remodel pipeline is active and retry the TOC once serially. Read the error to identify the missing feature/package; do not blindly add Hangs.
- Only when the error names Hangs features/package registration, remodel to a temporary copy with the Hangs package, then export the copy:

```bash
XCODE_DEVELOPER_DIR="$(xcode-select -p)"
HANGS_PACKAGE="${XCODE_DEVELOPER_DIR%/Contents/Developer}/Contents/Applications/Instruments.app/Contents/Packages/Hangs.instrdst"

xcrun xctrace remodel \
  --input /path/to/file.trace \
  --output /tmp/name_remodeled.trace \
  --package "$HANGS_PACKAGE"
```

Treat `Can't add the same store twice` as non-fatal only when the command also reports that remodeling completed and saved the output.

The warning `Signpost intervals with backdated timestamps ... not visualized ... until immediate mode recording is stopped` describes live timeline visualization. It does not by itself prove save failure.

## Report contract

For each major anomaly, report:

1. Direct conclusion and classification.
2. Exact interval or phase.
3. Table, thread, state, and weighted stack evidence.
4. Trigger, synchronous container, dominant observer/caller, and downstream work.
5. Confirmed evidence versus static candidates.
6. Source locations only for trace-proven paths.
7. Fix priority and what the fix will not eliminate.
8. Missing metrics or capture limitations.

For top-N reports, rank by the metric requested, state whether it is inclusive/exclusive, and expand one item at a time when exports are large.

## Common pitfalls

- Do not infer RSS from Allocations persistent bytes or crash-log `mem_free`.
- Do not mix virtual reservation with physical pressure.
- Do not call a lock frame a deadlock without a stable wait and ownership cycle.
- Do not attribute an entire wall-time Hang to a smaller sampled subtree.
- Do not add nested inclusive frame weights.
- Do not blame a synchronous broadcaster without identifying the heavy observer.
- Do not treat an empty `potential-hangs` table as proof that no freeze occurred; thresholds, capture gaps, and permanent freezes can escape an interval detector.
- Do not call a normal RunLoop `mach_msg` wait a lock wait or deadlock without interval and all-thread dependency evidence.
- Do not repeatedly remodel a genuinely malformed trace.
- Do not use `nice` as load control on this Mac; keep exports serial instead.
- Do not dump huge XML rows into the answer; aggregate first.
