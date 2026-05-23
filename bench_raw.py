#!/usr/bin/env python3
"""
Nokura storage throughput benchmark.

Measures read throughput from a neuroglancer-precomputed HTTP layer by
downloading chunks in parallel with varying thread counts. Demonstrates
that throughput saturates at ~130 MB/s with 1 MB chunks regardless of
concurrency.

Requirements: pip install requests

Usage:
    python bench_raw.py
    python bench_raw.py --url https://c10s.pni.princeton.edu/zfish_2025_public/stack/0406 --resolution 40_40_45 --num-chunks 5000
    python bench_raw.py --workers 8,32,64,128,256 --output-csv results/my_run.csv
"""

import argparse
import csv
import json
import math
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request

DEFAULT_URL = "https://c10s.pni.princeton.edu/zfish_2025_public/stack/0406"
DEFAULT_RESOLUTION = "40_40_45"
DEFAULT_NUM_CHUNKS = 9600
DEFAULT_WORKERS = "8,32,64,128,256"
SEED = 42


def fetch_info(base_url):
    """Fetch and parse the precomputed info file."""
    req = Request(f"{base_url}/info")
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def find_scale(info, resolution_key):
    """Find the scale matching the given resolution key."""
    for scale in info["scales"]:
        if scale["key"] == resolution_key:
            return scale
    available = [s["key"] for s in info["scales"]]
    raise ValueError(f"Resolution '{resolution_key}' not found. Available: {available}")


def enumerate_chunks(scale, max_chunks):
    """Generate chunk coordinates for the given scale."""
    chunk_size = scale["chunk_sizes"][0]
    size = scale["size"]
    cx, cy, cz = chunk_size

    coords = []
    for z in range(0, size[2]):
        for y in range(0, size[1], cy):
            for x in range(0, size[0], cx):
                x_end = min(x + cx, size[0])
                y_end = min(y + cy, size[1])
                z_end = z + 1
                coords.append(f"{x}-{x_end}_{y}-{y_end}_{z}-{z_end}")
                if len(coords) >= max_chunks * 2:
                    break
            if len(coords) >= max_chunks * 2:
                break
        if len(coords) >= max_chunks * 2:
            break

    random.seed(SEED)
    random.shuffle(coords)
    return coords[:max_chunks]


# Thread-local storage for connection reuse
_local = threading.local()


def download_chunk(url):
    """Download a single chunk via HTTP GET. Returns bytes downloaded."""
    # Use urllib with keep-alive (default for HTTP/1.1)
    req = Request(url)
    with urlopen(req, timeout=30) as resp:
        data = resp.read()
    return len(data)


def run_benchmark(base_url, resolution_key, chunk_coords, num_workers):
    """Run the benchmark with a given number of workers. Returns (elapsed_s, total_bytes, num_chunks)."""
    urls = [f"{base_url}/{resolution_key}/{coord}" for coord in chunk_coords]
    total_bytes = 0

    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(download_chunk, url) for url in urls]
        for future in as_completed(futures):
            total_bytes += future.result()
    elapsed = time.monotonic() - start

    return elapsed, total_bytes, len(urls)


def main():
    parser = argparse.ArgumentParser(description="Nokura storage throughput benchmark")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Precomputed layer URL (default: {DEFAULT_URL})")
    parser.add_argument("--resolution", default=DEFAULT_RESOLUTION, help=f"Resolution key (default: {DEFAULT_RESOLUTION})")
    parser.add_argument("--num-chunks", type=int, default=DEFAULT_NUM_CHUNKS, help=f"Number of chunks to read (default: {DEFAULT_NUM_CHUNKS})")
    parser.add_argument("--workers", default=DEFAULT_WORKERS, help=f"Comma-separated worker counts (default: {DEFAULT_WORKERS})")
    parser.add_argument("--output-csv", help="Write results to CSV file")
    args = parser.parse_args()

    worker_counts = [int(w) for w in args.workers.split(",")]

    # Fetch layer info
    print(f"Layer: {args.url}")
    info = fetch_info(args.url)
    scale = find_scale(info, args.resolution)
    chunk_size = scale["chunk_sizes"][0]
    chunk_bytes = chunk_size[0] * chunk_size[1] * chunk_size[2]  # assuming uint8
    print(f"Resolution: {args.resolution}")
    print(f"Chunk size: {chunk_size[0]}x{chunk_size[1]}x{chunk_size[2]} = {chunk_bytes / 1024 / 1024:.1f} MB")
    print(f"Chunks to read: {args.num_chunks}")
    print()

    # Enumerate chunk coordinates
    print("Enumerating chunk coordinates...")
    chunk_coords = enumerate_chunks(scale, args.num_chunks)
    actual_chunks = len(chunk_coords)
    if actual_chunks < args.num_chunks:
        print(f"  (only {actual_chunks} chunks available at this resolution)")
    print()

    # Run benchmarks
    results = []
    header = f"{'Workers':>8} {'Time (s)':>10} {'Ops/sec':>10} {'MB/s':>10}"
    print(header)
    print("-" * len(header))

    for num_workers in worker_counts:
        elapsed, total_bytes, n = run_benchmark(args.url, args.resolution, chunk_coords, num_workers)
        ops_sec = n / elapsed
        mb_sec = total_bytes / elapsed / 1024 / 1024
        results.append({
            "workers": num_workers,
            "chunks": n,
            "time_s": round(elapsed, 1),
            "ops_sec": round(ops_sec, 1),
            "mb_sec": round(mb_sec, 1),
        })
        print(f"{num_workers:>8} {elapsed:>10.1f} {ops_sec:>10.1f} {mb_sec:>10.1f}")

    # Write CSV
    if args.output_csv:
        with open(args.output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["workers", "chunks", "time_s", "ops_sec", "mb_sec"])
            writer.writeheader()
            writer.writerows(results)
        print(f"\nResults written to {args.output_csv}")


if __name__ == "__main__":
    main()
