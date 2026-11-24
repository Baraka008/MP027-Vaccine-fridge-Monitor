"""Command-line entry point for MP027."""
from monitor import run_pipeline


def main() -> None:
    results = run_pipeline()
    sizes = results["sizes"]
    print("\nVACCINE FRIDGE COLD-CHAIN MONITOR")
    print("-" * 38)
    print(f"Readings processed:       {results['readings']}")
    print(f"Monitoring days:          {results['days_summarised']}")
    print(f"Excursions detected:      {results['excursions']}")
    print(f"Raw CSV size:             {sizes['raw_bytes']:,} bytes")
    print(f"Edge summary size:        {sizes['edge_bytes']:,} bytes")
    print(f"File-size reduction:      {sizes['reduction_percent']:.1f}%")
    print("\nGenerated files:")
    for key in ("excursion_file", "daily_file", "edge_file", "plot_file"):
        print(f"  - {results[key]}")
    print("\nNote: Simulated educational project; not a validated vaccine-storage alarm.")


if __name__ == "__main__":
    main()
