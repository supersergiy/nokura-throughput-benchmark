# Nokura Storage Throughput Benchmark

Measures read throughput from Princeton's nokura storage (neuroglancer-precomputed over HTTP) at varying concurrency levels. Demonstrates that throughput saturates at **~130 MB/s** with 1 MB chunks, regardless of worker count.

## Results (Sarek, 2026-05-22)

### Worker count sweep (40nm, 1 MB chunks, 9600 reads)

| Workers | Time (s) | Ops/sec | MB/s  |
|---------|----------|---------|-------|
| 8       | 112.5    | 85.3    | 85.3  |
| 32      | 85.0     | 112.9   | 112.9 |
| 64      | 77.5     | 123.9   | 123.9 |
| 128     | 74.1     | 129.6   | 129.6 |
| 256     | 75.8     | 126.6   | 126.6 |

Throughput flattens at 64 workers. Adding more workers (up to 256) does not increase throughput. The ceiling is **~130 MB/s** (~1 Gbps).

### Resolution comparison (128 workers)

| Resolution | Chunk size | Ops/sec | MB/s  |
|------------|-----------|---------|-------|
| 320nm      | 1 MB      | 113.8   | 113.8 |
| 80nm       | 1 MB      | 126.1   | 126.1 |
| 40nm       | 1 MB      | 129.6   | 129.6 |
| 5nm        | 16 MB     | 12.0    | 191.5 |

Larger chunks (16 MB) achieve higher MB/s by amortizing per-request overhead, but even then the ceiling is under 200 MB/s.

### Impact on alignment

The full pairwise fine alignment pipeline requires **~3 TB of I/O per z-section** (4 offsets). At 130 MB/s, that's **~6.4 hours** of I/O per section — a significant fraction of the ~22-hour total processing time.

For comparison, GCS from a GCP VM in the same region delivers **~2 GB/s**, which would complete the same I/O in **~25 minutes**.

## Quick start

```bash
pip install requests

# Run from a Sarek login or compute node:
python bench_raw.py

# Custom settings:
python bench_raw.py \
    --url https://c10s.pni.princeton.edu/zfish_2025_public/stack/0406 \
    --resolution 40_40_45 \
    --num-chunks 5000 \
    --workers 8,32,64,128,256 \
    --output-csv results/my_run.csv

# Plot results:
pip install matplotlib
python plot_results.py results/my_run.csv -o results/my_run.png
```

## Methodology

The benchmark reads random chunks from a precomputed layer via HTTP GET using Python's `urllib` with connection pooling. Each chunk is downloaded fully and discarded. Timing starts after chunk coordinates are enumerated and measures only the download phase.

This is a pure I/O test — no computation, no GPU, no framework overhead. The same saturation was independently confirmed using the zetta_utils mazepa framework with SLURM workers (128 array jobs across multiple nodes).

**Note**: Running from a single login node will show a lower ceiling (~60 MB/s) due to per-node network limits. The ~130 MB/s ceiling is the aggregate across many nodes hitting the storage endpoint concurrently — which is the production configuration. To reproduce the full result, run the script simultaneously from multiple compute nodes, or use the SLURM-based benchmark.

## Cluster details

- **Cluster**: Princeton Sarek HPC
- **Storage**: nokura (c10s), neuroglancer-precomputed over HTTPS
- **Source layer**: `https://c10s.pni.princeton.edu/zfish_2025_public/stack/0406`
- **Data type**: uint8, single channel (zebrafish EM)
