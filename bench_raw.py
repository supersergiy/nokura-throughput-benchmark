#!/usr/bin/env python3
"""
Nokura storage throughput benchmark.

Downloads chunks from a neuroglancer-precomputed HTTP layer in parallel,
sweeping worker counts to show throughput saturation.

Zero dependencies (stdlib only). Usage:
    python bench_raw.py
    python bench_raw.py --num-chunks 500 --workers 8,32,64
    python bench_raw.py --mode processes --workers 4,8,16
"""

import argparse
import json
import random
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen

URL = "https://c10s.pni.princeton.edu/zfish_2025_public/stack/0406"
RES = "40_40_45"


def get_chunks(base_url, res, n):
    info = json.loads(urlopen(f"{base_url}/info").read())
    scale = next(s for s in info["scales"] if s["key"] == res)
    cx, cy = scale["chunk_sizes"][0][:2]
    sx, sy = scale["size"][:2]
    coords = [
        f"{x}-{min(x+cx,sx)}_{y}-{min(y+cy,sy)}_3000-3001"
        for x in range(0, sx, cx) for y in range(0, sy, cy)
    ]
    random.seed(42)
    random.shuffle(coords)
    return coords[:n], cx * cy  # coords, bytes_per_chunk (uint8)


def download(url):
    with urlopen(Request(url), timeout=30) as r:
        return len(r.read())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=URL)
    p.add_argument("--resolution", default=RES)
    p.add_argument("--num-chunks", type=int, default=2000)
    p.add_argument("--workers", default="8,32,64,128,256")
    p.add_argument("--mode", choices=["threads", "processes"], default="threads",
                   help="threads (GIL-limited) or processes (no GIL, ~2x faster)")
    p.add_argument("--output-csv", default=None)
    args = p.parse_args()

    Executor = ProcessPoolExecutor if args.mode == "processes" else ThreadPoolExecutor

    coords, chunk_bytes = get_chunks(args.url, args.resolution, args.num_chunks)
    urls = [f"{args.url}/{args.resolution}/{c}" for c in coords]
    n = len(urls)
    mb = chunk_bytes / 1024 / 1024
    print(f"Layer: {args.url}")
    print(f"Resolution: {args.resolution}  Chunk: {mb:.1f} MB  Count: {n}")
    print(f"Mode: {args.mode}")
    print()
    print(f"{'Workers':>8} {'Time(s)':>8} {'Ops/s':>8} {'MB/s':>8}")
    print("-" * 36)

    rows = []
    for w in [int(x) for x in args.workers.split(",")]:
        t0 = time.monotonic()
        with Executor(max_workers=w) as ex:
            total = sum(f.result() for f in as_completed(
                [ex.submit(download, u) for u in urls]))
        dt = time.monotonic() - t0
        ops = n / dt
        mbs = total / dt / 1048576
        print(f"{w:>8} {dt:>8.1f} {ops:>8.1f} {mbs:>8.1f}")
        rows.append(f"{w},{n},{dt:.1f},{ops:.1f},{mbs:.1f}")

    if args.output_csv:
        with open(args.output_csv, "w") as f:
            f.write("workers,chunks,time_s,ops_sec,mb_sec\n")
            f.write("\n".join(rows) + "\n")
        print(f"\nSaved to {args.output_csv}")


if __name__ == "__main__":
    main()
