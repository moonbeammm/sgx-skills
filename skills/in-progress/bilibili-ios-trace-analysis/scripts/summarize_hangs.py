#!/usr/bin/env python3
"""Correlate xctrace potential-hangs and time-profile XML exports."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class HangInterval:
    index: int
    start_ns: int
    duration_ns: int
    hang_type: str
    tid: str
    thread_name: str

    @property
    def end_ns(self) -> int:
        return self.start_ns + self.duration_ns


@dataclass
class HangSummary:
    interval: HangInterval
    sample_count: int = 0
    sampled_weight_ns: int = 0
    missing_stack_count: int = 0
    missing_weight_count: int = 0
    sample_times_ns: list[int] = field(default_factory=list)
    state_samples: Counter[str] = field(default_factory=Counter)
    state_weight_ns: Counter[str] = field(default_factory=Counter)
    inclusive_samples: Counter[str] = field(default_factory=Counter)
    inclusive_weight_ns: Counter[str] = field(default_factory=Counter)
    leaf_samples: Counter[str] = field(default_factory=Counter)
    leaf_weight_ns: Counter[str] = field(default_factory=Counter)


class XctraceResolver:
    """Resolve the global id/ref encoding used by xctrace XML exports."""

    def __init__(self) -> None:
        self.scalars: dict[str, tuple[str, str]] = {}
        self.frames: dict[str, str] = {}
        self.backtraces: dict[str, list[str]] = {}
        self.threads: dict[str, tuple[str, str]] = {}

    @staticmethod
    def _text(element: ET.Element) -> str:
        raw = (element.text or "").strip()
        return raw or element.get("fmt", "").strip()

    def remember_row(self, row: ET.Element) -> None:
        # Scalar and frame definitions must be known before resolving complex
        # thread and backtrace definitions from the same row.
        for element in row.iter():
            element_id = element.get("id")
            if not element_id:
                continue
            text = self._text(element)
            self.scalars[element_id] = (text, element.get("fmt", "").strip())
            if element.tag == "frame":
                self.frames[element_id] = element.get("name", "").strip() or text

        for element in row.iter("thread"):
            element_id = element.get("id")
            if not element_id:
                continue
            tid_element = element.find("tid")
            tid = self.scalar(tid_element) if tid_element is not None else ""
            self.threads[element_id] = (tid, element.get("fmt", "").strip())

        for element in row.iter("backtrace"):
            element_id = element.get("id")
            if not element_id:
                continue
            frames: list[str] = []
            for frame in element.findall("frame"):
                name = self.frame(frame)
                if name:
                    frames.append(name)
            self.backtraces[element_id] = frames

    def scalar(self, element: ET.Element | None) -> str:
        if element is None:
            return ""
        ref = element.get("ref")
        if ref:
            value, fmt = self.scalars.get(ref, ("", ""))
            return value or fmt
        return self._text(element)

    def scalar_fmt(self, element: ET.Element | None) -> str:
        if element is None:
            return ""
        ref = element.get("ref")
        if ref:
            value, fmt = self.scalars.get(ref, ("", ""))
            return fmt or value
        return element.get("fmt", "").strip() or self._text(element)

    def thread(self, element: ET.Element | None) -> tuple[str, str]:
        if element is None:
            return "", ""
        ref = element.get("ref")
        if ref:
            return self.threads.get(ref, ("", ""))
        element_id = element.get("id")
        if element_id and element_id in self.threads:
            return self.threads[element_id]
        tid_element = element.find("tid")
        tid = self.scalar(tid_element) if tid_element is not None else ""
        return tid, element.get("fmt", "").strip()

    def frame(self, element: ET.Element) -> str:
        ref = element.get("ref")
        if ref:
            return self.frames.get(ref, f"<unresolved frame ref={ref}>")
        return element.get("name", "").strip() or self._text(element)

    def backtrace(self, element: ET.Element | None) -> list[str]:
        if element is None:
            return []
        ref = element.get("ref")
        if ref:
            return list(self.backtraces.get(ref, []))
        element_id = element.get("id")
        if element_id and element_id in self.backtraces:
            return list(self.backtraces[element_id])
        return [self.frame(frame) for frame in element.findall("frame")]


def parse_int(value: str, field_name: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"invalid {field_name}: {value!r}") from error


def iter_rows(path: Path) -> Iterable[tuple[ET.Element, XctraceResolver]]:
    resolver = XctraceResolver()
    try:
        for _event, element in ET.iterparse(path, events=("end",)):
            if element.tag != "row":
                continue
            resolver.remember_row(element)
            yield element, resolver
            element.clear()
    except ET.ParseError as error:
        raise ValueError(f"cannot parse XML {path}: {error}") from error


def parse_hangs(path: Path) -> list[HangInterval]:
    intervals: list[HangInterval] = []
    for row, resolver in iter_rows(path):
        start = resolver.scalar(row.find("start-time"))
        duration = resolver.scalar(row.find("duration"))
        if not start or not duration:
            continue
        hang_type = resolver.scalar_fmt(row.find("hang-type")) or "Unknown"
        tid, thread_name = resolver.thread(row.find("thread"))
        if not tid:
            raise ValueError(
                f"potential-hangs row {len(intervals) + 1} has no resolvable thread id"
            )
        intervals.append(
            HangInterval(
                index=len(intervals) + 1,
                start_ns=parse_int(start, "start-time"),
                duration_ns=parse_int(duration, "duration"),
                hang_type=hang_type,
                tid=tid,
                thread_name=thread_name or (f"tid {tid}" if tid else "unknown thread"),
            )
        )
    if not intervals:
        raise ValueError(f"no potential-hangs rows found in {path}")
    return intervals


def choose_intervals(
    intervals: list[HangInterval], hang_index: int | None
) -> list[HangInterval]:
    if hang_index is None:
        return intervals
    if hang_index < 1 or hang_index > len(intervals):
        raise ValueError(
            f"--hang-index must be between 1 and {len(intervals)}, got {hang_index}"
        )
    return [intervals[hang_index - 1]]


def aggregate_samples(
    path: Path, intervals: list[HangInterval]
) -> list[HangSummary]:
    summaries = [HangSummary(interval) for interval in intervals]
    ordered = sorted(summaries, key=lambda item: item.interval.start_ns)

    for row, resolver in iter_rows(path):
        sample_text = resolver.scalar(row.find("sample-time"))
        if not sample_text:
            continue
        sample_ns = parse_int(sample_text, "sample-time")
        tid, _thread_name = resolver.thread(row.find("thread"))
        matching = [
            summary
            for summary in ordered
            if summary.interval.start_ns <= sample_ns < summary.interval.end_ns
            and summary.interval.tid == tid
        ]
        if not matching:
            continue

        weight_text = resolver.scalar(row.find("weight"))
        weight_ns = parse_int(weight_text, "weight") if weight_text else 0
        state = resolver.scalar_fmt(row.find("thread-state")) or "Unknown"
        frames = resolver.backtrace(row.find("backtrace"))

        for summary in matching:
            summary.sample_count += 1
            summary.sampled_weight_ns += weight_ns
            summary.sample_times_ns.append(sample_ns)
            if not weight_text:
                summary.missing_weight_count += 1
            summary.state_samples[state] += 1
            summary.state_weight_ns[state] += weight_ns
            if not frames:
                summary.missing_stack_count += 1
                continue

            leaf = frames[0]
            summary.leaf_samples[leaf] += 1
            summary.leaf_weight_ns[leaf] += weight_ns

            # Inclusive stacks are nested. Count a recursive symbol once per
            # sample so one sample never contributes its weight repeatedly.
            for frame in dict.fromkeys(frames):
                summary.inclusive_samples[frame] += 1
                summary.inclusive_weight_ns[frame] += weight_ns

    return summaries


def format_seconds(value_ns: int) -> str:
    return f"{value_ns / 1_000_000_000:.6f}s"


def format_duration(value_ns: int) -> str:
    if abs(value_ns) >= 1_000_000_000:
        return f"{value_ns / 1_000_000_000:.3f}s"
    return f"{value_ns / 1_000_000:.3f}ms"


def print_counter(
    title: str,
    weights: Counter[str],
    samples: Counter[str],
    top: int,
) -> None:
    print(f"  {title}:")
    if not samples:
        print("    (no symbolized stack samples)")
        return
    use_weights = any(weights.values())
    ranked = weights.most_common(top) if use_weights else samples.most_common(top)
    for rank, (name, _ranked_value) in enumerate(ranked, start=1):
        weight = weights[name] if use_weights else 0
        print(
            f"    {rank:>2}. {format_duration(weight):>10}  "
            f"samples={samples[name]:>5}  {name}"
        )


def print_summary(summary: HangSummary, top: int) -> None:
    interval = summary.interval
    print(
        f"Hang #{interval.index}: {interval.hang_type}  "
        f"{format_seconds(interval.start_ns)}-{format_seconds(interval.end_ns)}  "
        f"wall={format_duration(interval.duration_ns)}"
    )
    print(f"  Thread: {interval.thread_name} [tid={interval.tid or 'unknown'}]")
    print(
        f"  Time Profiler: samples={summary.sample_count}, "
        f"sampled_weight={format_duration(summary.sampled_weight_ns)}, "
        f"missing_stack={summary.missing_stack_count}, "
        f"missing_weight={summary.missing_weight_count}"
    )
    if summary.sample_times_ns:
        times = sorted(summary.sample_times_ns)
        max_gap = max(
            (later - earlier for earlier, later in zip(times, times[1:])),
            default=0,
        )
        print(
            "  Target-sample coverage: "
            f"first=+{format_duration(times[0] - interval.start_ns)}, "
            f"last_before_end={format_duration(interval.end_ns - times[-1])}, "
            f"max_gap={format_duration(max_gap)}"
        )
        print("  Note: a target-sample gap is not proof of a wait or deadlock.")
    print("  Thread states:")
    if not summary.state_samples:
        print("    (no matching samples)")
    else:
        for state, count in summary.state_samples.most_common():
            print(
                f"    {state}: samples={count}, "
                f"weight={format_duration(summary.state_weight_ns[state])}"
            )
    print_counter(
        "Inclusive frames (nested; do not add)",
        summary.inclusive_weight_ns,
        summary.inclusive_samples,
        top,
    )
    print_counter(
        "Leaf/exclusive frames",
        summary.leaf_weight_ns,
        summary.leaf_samples,
        top,
    )


def inspect_toc(path: Path) -> tuple[list[str], bool]:
    settings: list[str] = []
    waiting_state_blind = False
    wanted = {
        "time-profile": ("record-waiting-threads", "context-switch-sampling"),
        "time-sample": ("all-thread-states",),
    }
    try:
        for _event, element in ET.iterparse(path, events=("start",)):
            schema = element.get("schema", "")
            keys = wanted.get(schema)
            if not keys:
                continue
            values = [
                f"{key}={element.get(key)}" for key in keys if key in element.attrib
            ]
            if values:
                settings.append(f"{schema}: " + ", ".join(values))
            if element.get("record-waiting-threads") == "0":
                waiting_state_blind = True
            if element.get("all-thread-states", "").upper() == "NO":
                waiting_state_blind = True
    except ET.ParseError as error:
        raise ValueError(f"cannot parse TOC XML {path}: {error}") from error
    return list(dict.fromkeys(settings)), waiting_state_blind


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Correlate xctrace potential-hangs intervals with affected-thread "
            "Time Profiler samples."
        )
    )
    parser.add_argument("--hangs", type=Path, required=True, help="potential-hangs XML")
    parser.add_argument(
        "--time-profile", type=Path, required=True, help="time-profile XML"
    )
    parser.add_argument("--toc", type=Path, help="optional xctrace TOC XML")
    parser.add_argument("--top", type=int, default=30, help="frames per ranking")
    parser.add_argument(
        "--hang-index", type=int, help="analyze one 1-based interval index"
    )
    args = parser.parse_args(argv)
    if args.top < 1:
        parser.error("--top must be at least 1")
    for field in ("hangs", "time_profile", "toc"):
        path = getattr(args, field)
        if path is not None and not path.is_file():
            parser.error(f"file does not exist: {path}")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        intervals = choose_intervals(parse_hangs(args.hangs), args.hang_index)
        summaries = aggregate_samples(args.time_profile, intervals)
        toc_settings, waiting_state_blind = (
            inspect_toc(args.toc) if args.toc else ([], False)
        )
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(
        "Warning: Hang wall time and Time Profiler sampled weight are different "
        "metrics. Inclusive frame weights overlap and must not be added."
    )
    if toc_settings:
        print("Capture metadata: " + " | ".join(toc_settings))
    if waiting_state_blind:
        print(
            "Warning: waiting/all-thread states were not fully recorded. Missing "
            "samples cannot exclude a wait, and this capture cannot prove a deadlock."
        )
    print()
    for index, summary in enumerate(summaries):
        if index:
            print()
        print_summary(summary, args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
