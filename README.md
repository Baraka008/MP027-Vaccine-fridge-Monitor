# MP027 — Vaccine Fridge Cold-Chain Monitor

A Python mini-project that analyses simulated vaccine-fridge temperature readings against the required 2–8 °C range.

## Features

- Generates 14 days of reproducible readings every five minutes (4,032 samples).
- Injects a few clearly simulated excursions for testing.
- Detects consecutive out-of-range readings and records start, end, duration, direction and peak temperature.
- Produces a daily summary and a compact edge summary.
- Compares the raw CSV and edge-summary file sizes.
- Plots the readings with horizontal 2 °C and 8 °C limit lines.
- Includes automated tests for the CAT hand-check: 8.4, 8.6, 7.9 at five-minute intervals gives one 10-minute excursion.

## Requirements

- Python 3.10+
- matplotlib

## Run

    python -m venv .venv

Activate the environment:

Windows PowerShell:
    
    .venv\Scripts\Activate.ps1

Linux/macOS:

    source .venv/bin/activate

Install and run:

    python -m pip install -r requirements.txt
    python main.py

On the first run, the program creates data/temperature_readings.csv. Results are written to output/:

- excursions.csv
- daily_summary.csv
- edge_summary.csv
- temperature_14_days.png

The program does not overwrite an existing raw CSV. Delete it if you want to generate a fresh dataset.

## Tests

    python -m unittest discover -s tests -v

## Duration convention

An excursion starts at the timestamp of its first out-of-range sample and ends at the timestamp of the first subsequent in-range sample. Thus 8.4, 8.6, 7.9 at five-minute steps is a 10-minute excursion. If an excursion continues to the final sample, one additional sampling interval is counted.

## Edge-versus-raw comparison

The edge summary aggregates each day into one row containing count, average, minimum, maximum, excursion count and out-of-range minutes. The raw log stores every five-minute sample. File sizes and percentage reduction are measured from the actual files at runtime.

## Safety note

This is simulated educational software, not a validated medical-device monitoring system. Do not use it to make real vaccine-storage decisions. Real deployments require calibrated sensors, validated alarm logic, reliable timekeeping, fault handling and applicable health-authority procedures.
