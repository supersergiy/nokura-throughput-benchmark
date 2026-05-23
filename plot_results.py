#!/usr/bin/env python3
"""
Plot nokura throughput benchmark results.

Usage:
    python plot_results.py results/sarek_2026-05-22.csv -o results/sarek_2026-05-22.png
    python plot_results.py my_run.csv
"""

import argparse
import csv
import sys

def main():
    parser = argparse.ArgumentParser(description="Plot benchmark results")
    parser.add_argument("csv_file", help="CSV file from bench_raw.py")
    parser.add_argument("-o", "--output", default=None, help="Output PNG (default: show)")
    args = parser.parse_args()

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("pip install matplotlib", file=sys.stderr)
        sys.exit(1)

    workers = []
    mb_sec = []
    with open(args.csv_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            workers.append(int(row["workers"]))
            mb_sec.append(float(row["mb_sec"]))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(workers, mb_sec, "o-", linewidth=2, markersize=8, color="#2563eb")
    ax.axhline(y=130, color="#dc2626", linestyle="--", linewidth=1.5, label="~130 MB/s ceiling")
    ax.axhline(y=2000, color="#16a34a", linestyle=":", linewidth=1.5, label="GCS from GCP VM (~2 GB/s)")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Worker threads", fontsize=13)
    ax.set_ylabel("Throughput (MB/s)", fontsize=13)
    ax.set_title("Nokura Storage Throughput Saturation", fontsize=14, fontweight="bold")
    ax.set_xticks(workers)
    ax.set_xticklabels([str(w) for w in workers])
    ax.set_ylim(0, max(max(mb_sec) * 1.3, 250))
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if args.output:
        plt.savefig(args.output, dpi=150)
        print(f"Saved to {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
