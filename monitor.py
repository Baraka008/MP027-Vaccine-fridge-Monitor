"""Core processing functions for the MP027 vaccine-fridge monitor."""
from __future__ import annotations

import csv
import random
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

MIN_TEMP_C = 2.0
MAX_TEMP_C = 8.0
INTERVAL_MINUTES = 5
MONITORING_DAYS = 14
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def generate_readings(days: int = MONITORING_DAYS,
                      interval_minutes: int = INTERVAL_MINUTES,
                      seed: int = 42,
                      start: datetime | None = None) -> list[dict]:
    """Generate deterministic sample readings with deliberate test excursions."""
    if days <= 0 or interval_minutes <= 0:
        raise ValueError("days and interval_minutes must be positive")

    rng = random.Random(seed)
    start = start or datetime(2026, 1, 1)
    count = days * 24 * 60 // interval_minutes
    readings = []
    for index in range(count):
        timestamp = start + timedelta(minutes=index * interval_minutes)
        readings.append({
            "timestamp": timestamp,
            "temperature_c": round(rng.uniform(3.5, 6.5), 1),
        })

    # (first index, last index inclusive, simulated temperature)
    injected_events = [
        (100, 102, 8.7),
        (500, 503, 1.5),
        (1200, 1201, 9.2),
        (2500, 2505, 1.2),
        (3500, 3502, 8.9),
    ]
    for first, last, temperature in injected_events:
        for index in range(first, min(last + 1, count)):
            readings[index]["temperature_c"] = temperature
    return readings


def save_readings(readings: Iterable[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "temperature_c"])
        for row in readings:
            writer.writerow([
                row["timestamp"].strftime(TIMESTAMP_FORMAT),
                f"{float(row['temperature_c']):.1f}",
            ])


def load_readings(path: Path) -> list[dict]:
    readings = []
    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        required = {"timestamp", "temperature_c"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("CSV must contain timestamp and temperature_c columns")
        for line_number, row in enumerate(reader, start=2):
            try:
                timestamp = datetime.strptime(row["timestamp"], TIMESTAMP_FORMAT)
                temperature = float(row["temperature_c"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid reading on CSV line {line_number}: {exc}") from exc
            readings.append({"timestamp": timestamp, "temperature_c": temperature})
    return sorted(readings, key=lambda item: item["timestamp"])


def is_out_of_range(temperature: float) -> bool:
    """The permitted range is inclusive: 2.0 through 8.0 °C."""
    return temperature < MIN_TEMP_C or temperature > MAX_TEMP_C


def detect_excursions(readings: list[dict],
                      interval_minutes: int = INTERVAL_MINUTES) -> list[dict]:
    """Group consecutive out-of-range samples into excursion events."""
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be positive")
    if not readings:
        return []

    ordered = sorted(readings, key=lambda item: item["timestamp"])
    events = []
    active = []

    def finish_event(samples: list[dict], next_timestamp: datetime | None) -> None:
        start_time = samples[0]["timestamp"]
        end_time = next_timestamp or (
            samples[-1]["timestamp"] + timedelta(minutes=interval_minutes)
        )
        values = [float(item["temperature_c"]) for item in samples]
        high = max(values) > MAX_TEMP_C
        low = min(values) < MIN_TEMP_C
        events.append({
            "start": start_time,
            "end": end_time,
            "duration_minutes": int((end_time - start_time).total_seconds() // 60),
            "reading_count": len(samples),
            "direction": "both" if high and low else ("high" if high else "low"),
            "peak_temperature_c": max(values),
            "minimum_temperature_c": min(values),
        })

    for reading in ordered:
        if is_out_of_range(float(reading["temperature_c"])):
            active.append(reading)
        elif active:
            finish_event(active, reading["timestamp"])
            active = []

    if active:
        finish_event(active, None)
    return events


def build_daily_summary(readings: list[dict], excursions: list[dict]) -> list[dict]:
    daily = defaultdict(list)
    for reading in readings:
        daily[reading["timestamp"].date()].append(float(reading["temperature_c"]))

    events_by_day = defaultdict(list)
    for event in excursions:
        events_by_day[event["start"].date()].append(event)

    summaries = []
    for day in sorted(daily):
        values = daily[day]
        events = events_by_day[day]
        summaries.append({
            "date": day.isoformat(),
            "reading_count": len(values),
            "average_temperature_c": sum(values) / len(values),
            "minimum_temperature_c": min(values),
            "maximum_temperature_c": max(values),
            "excursion_count": len(events),
            "out_of_range_minutes": sum(e["duration_minutes"] for e in events),
        })
    return summaries


def save_excursions(excursions: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["start", "end", "duration_minutes", "reading_count", "direction",
              "peak_temperature_c", "minimum_temperature_c"]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for event in excursions:
            row = event.copy()
            row["start"] = row["start"].strftime(TIMESTAMP_FORMAT)
            row["end"] = row["end"].strftime(TIMESTAMP_FORMAT)
            writer.writerow(row)


def save_daily_summary(summaries: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["date", "reading_count", "average_temperature_c",
              "minimum_temperature_c", "maximum_temperature_c",
              "excursion_count", "out_of_range_minutes"]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for summary in summaries:
            row = summary.copy()
            row["average_temperature_c"] = f"{row['average_temperature_c']:.2f}"
            row["minimum_temperature_c"] = f"{row['minimum_temperature_c']:.1f}"
            row["maximum_temperature_c"] = f"{row['maximum_temperature_c']:.1f}"
            writer.writerow(row)


def save_edge_summary(summaries: list[dict], path: Path) -> None:
    """Write one compact daily record instead of every sensor sample."""
    save_daily_summary(summaries, path)


def compare_file_sizes(raw_path: Path, edge_path: Path) -> dict:
    raw_bytes = raw_path.stat().st_size
    edge_bytes = edge_path.stat().st_size
    reduction = (1 - edge_bytes / raw_bytes) * 100 if raw_bytes else 0.0
    return {
        "raw_bytes": raw_bytes,
        "edge_bytes": edge_bytes,
        "reduction_percent": reduction,
    }


def plot_temperatures(readings: list[dict], path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "matplotlib is required. Install with: python -m pip install -r requirements.txt"
        ) from exc

    times = [row["timestamp"] for row in readings]
    values = [float(row["temperature_c"]) for row in readings]
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(times, values, linewidth=0.8, label="Fridge temperature")
    ax.axhline(MIN_TEMP_C, linestyle="--", linewidth=1.2, label="Lower limit (2 °C)")
    ax.axhline(MAX_TEMP_C, linestyle="--", linewidth=1.2, label="Upper limit (8 °C)")
    ax.set_title("Vaccine Fridge Temperature — 14-Day Monitoring")
    ax.set_xlabel("Date and time")
    ax.set_ylabel("Temperature (°C)")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_pipeline(data_dir: Path = Path("data"),
                 output_dir: Path = Path("output")) -> dict:
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = data_dir / "temperature_readings.csv"
    if not raw_path.exists():
        save_readings(generate_readings(), raw_path)

    readings = load_readings(raw_path)
    excursions = detect_excursions(readings)
    daily = build_daily_summary(readings, excursions)

    excursion_path = output_dir / "excursions.csv"
    daily_path = output_dir / "daily_summary.csv"
    edge_path = output_dir / "edge_summary.csv"
    plot_path = output_dir / "temperature_14_days.png"

    save_excursions(excursions, excursion_path)
    save_daily_summary(daily, daily_path)
    save_edge_summary(daily, edge_path)
    plot_temperatures(readings, plot_path)
    sizes = compare_file_sizes(raw_path, edge_path)

    return {
        "readings": len(readings),
        "excursions": len(excursions),
        "days_summarised": len(daily),
        "excursion_file": excursion_path,
        "daily_file": daily_path,
        "edge_file": edge_path,
        "plot_file": plot_path,
        "sizes": sizes,
    }
