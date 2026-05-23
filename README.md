# Nokura Storage Throughput Benchmark

Measures read throughput from Princeton's nokura storage (neuroglancer-precomputed over HTTPS) at varying concurrency and chunk sizes. **The bottleneck is ops/sec, not bandwidth** — larger chunks dramatically increase throughput.

## Results (Sarek single node, curl, 2026-05-22)

### 1 MB chunks (40nm, 1024x1024)

| Parallelism | Ops/sec | MB/s |
|-------------|---------|------|
| 32          | 96.2    | 96   |
| 64          | 88.7    | 89   |
| 128         | 69.5    | 70   |
| 256         | 35.3    | 35   |

With 1 MB chunks, throughput **peaks at ~96 MB/s** and **degrades** at higher parallelism. The server handles ~100 small requests/sec per client node.

### 16 MB chunks (5nm, 4096x4096)

| Parallelism | Ops/sec | MB/s  |
|-------------|---------|-------|
| 32          | 23.5    | 376   |
| 64          | 25.1    | 402   |
| 128         | 28.4    | **455** |

With 16 MB chunks, throughput reaches **455 MB/s** — 4.7x higher than 1 MB chunks. The server has plenty of bandwidth; the 1 MB ceiling is per-request overhead (TLS, HTTP headers, server-side lookup).

### The bottleneck is ops/sec

The server can sustain ~100 ops/sec for small (1 MB) requests from a single node. Per-request overhead dominates:
- At 1 MB: ~100 ops/sec × 1 MB = **~100 MB/s**
- At 16 MB: ~28 ops/sec × 16 MB = **~455 MB/s**
- High parallelism with small chunks actually **hurts** (P=256 is 3x slower than P=32)

### Impact on alignment

The pairwise fine alignment pipeline does ~3 TB of I/O per z-section (4 offsets), mostly in 1 MB chunks (1024x1024 encodings/fields). At the 1 MB ceiling of ~100 MB/s per node, this limits throughput even with many SLURM workers.

For comparison, GCS from a GCP VM delivers **~2 GB/s**, completing the same I/O in ~25 minutes instead of hours.

## Quick start

```bash
# Curl benchmark (simplest, zero Python deps for the download itself):
./bench_curl.sh 500 8,32,64

# Python benchmark (stdlib only):
python bench_raw.py --num-chunks 500 --workers 8,32,64

# Python with multiprocessing (bypasses GIL, ~2x faster than threads):
python bench_raw.py --mode processes --num-chunks 500 --workers 4,8,16

# Test 16 MB chunks at 5nm:
python bench_raw.py --resolution 8_8_45 --num-chunks 200 --workers 8,32,64

# Plot results:
pip install matplotlib
python plot_results.py results/sarek_2026-05-22.csv -o results/plot.png
```

## Methodology

Downloads random chunks from a precomputed layer via HTTP GET, discards the data, measures wall-clock time. `bench_curl.sh` uses `curl + xargs` (no Python overhead). `bench_raw.py` uses Python stdlib `urllib`.

**Python GIL note**: Python threads are ~50% slower than curl due to GIL contention. Use `--mode processes` to match curl throughput from Python.

## Cluster details

- **Cluster**: Princeton Sarek HPC
- **Storage**: nokura (c10s), neuroglancer-precomputed over HTTPS
- **Source layer**: `https://c10s.pni.princeton.edu/zfish_2025_public/stack/0406`
- **Data type**: uint8, single channel (zebrafish EM)
