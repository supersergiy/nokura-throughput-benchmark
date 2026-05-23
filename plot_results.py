#!/usr/bin/env python3
"""
Plot nokura throughput benchmark results.

Usage:
    python plot_results.py -o results/sarek_2026-05-22.png
"""

import sys

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default=None, help="Output PNG (default: show)")
    args = parser.parse_args()

    try:
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        print("pip install matplotlib", file=sys.stderr)
        sys.exit(1)

    # === Single-node curl results (16MB chunks, 500 downloads) ===
    par_16mb =  [8,     16,    24,    32,    48,    64,    96,   128,   192,   256]
    ops_16mb =  [12.3,  16.3,  23.0,  23.5,  27.2,  36.9,  24.1, 36.3,  33.6,  36.5]
    mbs_16mb =  [197,   261,   368,   376,   435,   590,   386,  581,   538,   584]

    # === Single-node curl results (1MB chunks, 2000 downloads) ===
    par_1mb =   [8,     32,    64,    128,   256]
    ops_1mb =   [71.1,  96.2,  88.7,  69.5,  35.3]
    mbs_1mb =   [71.1,  96.2,  88.7,  69.5,  35.3]

    # === Multi-node aggregate (16MB chunks, 100 per worker, P=32 each) ===
    # Per-node totals from 64-worker SLURM run
    multinode = {
        "sarekl15-1": {"workers": 3, "ops": [34.0, 35.4, 33.7], "mbs": [544, 567, 539]},
        "sarekl15-2": {"workers": 2, "ops": [34.1, 35.0], "mbs": [546, 560]},
        "sarek17":    {"workers": 4, "ops": [12.2, 12.2, 6.3, 12.1], "mbs": [195, 195, 100, 193]},
        "sarek13":    {"workers": 4, "ops": [9.9, 9.7, 10.1, 9.9], "mbs": [159, 156, 162, 159]},
        "sarek16":    {"workers": 4, "ops": [10.1, 10.4, 10.9, 10.7], "mbs": [161, 167, 174, 171]},
        "sarek-r27-05": {"workers": 18, "ops": [2.7]*18, "mbs": [40]*18},
        "sarek-r27-01": {"workers": 11, "ops": [3.3]*11, "mbs": [49]*11},
        "sarek-r27-02": {"workers": 18, "ops": [2.0]*18, "mbs": [33]*18},
    }

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # --- Left plot: Single-node, MB/s and ops/s ---
    ax1 = axes[0]
    ax1_ops = ax1.twinx()

    l1, = ax1.plot(par_16mb, mbs_16mb, "o-", color="#2563eb", lw=2, ms=7, label="16MB chunks — MB/s")
    l2, = ax1.plot(par_1mb, mbs_1mb, "s-", color="#dc2626", lw=2, ms=7, label="1MB chunks — MB/s")
    l3, = ax1_ops.plot(par_16mb, ops_16mb, "^--", color="#2563eb", lw=1.5, ms=6, alpha=0.6, label="16MB chunks — ops/s")
    l4, = ax1_ops.plot(par_1mb, ops_1mb, "v--", color="#dc2626", lw=1.5, ms=6, alpha=0.6, label="1MB chunks — ops/s")

    ax1.set_xlabel("Parallel downloads (single node)", fontsize=12)
    ax1.set_ylabel("Throughput (MB/s)", fontsize=12, color="#333")
    ax1_ops.set_ylabel("Operations/sec", fontsize=12, color="#666")
    ax1.set_title("Single Node — Chunk Size Comparison", fontsize=13, fontweight="bold")
    ax1.set_xscale("log", base=2)
    ax1.set_ylim(0, 700)
    ax1_ops.set_ylim(0, 120)
    ax1.grid(True, alpha=0.2)
    ax1.legend(handles=[l1, l2, l3, l4], fontsize=9, loc="upper left")

    # --- Right plot: Per-node throughput (multi-node run) ---
    ax2 = axes[1]
    ax2_ops = ax2.twinx()

    nodes_sorted = sorted(multinode.keys(), key=lambda n: sum(multinode[n]["mbs"]), reverse=True)
    node_labels = []
    node_mbs = []
    node_ops = []
    for n in nodes_sorted:
        d = multinode[n]
        node_labels.append(f"{n}\n({d['workers']}w)")
        node_mbs.append(sum(d["mbs"]))
        node_ops.append(sum(d["ops"]))

    x = range(len(node_labels))
    bars = ax2.bar(x, node_mbs, color="#2563eb", alpha=0.7, label="MB/s (total)")
    ax2_ops.plot(list(x), node_ops, "D-", color="#e67e22", lw=2, ms=8, label="ops/s (total)")

    ax2.set_xticks(list(x))
    ax2.set_xticklabels(node_labels, fontsize=8)
    ax2.set_ylabel("Node total throughput (MB/s)", fontsize=12)
    ax2_ops.set_ylabel("Node total ops/s", fontsize=12, color="#e67e22")
    ax2.set_title("Multi-Node Aggregate (64 workers, 16MB chunks)", fontsize=13, fontweight="bold")
    ax2.grid(True, alpha=0.2, axis="y")

    total_mbs = sum(node_mbs)
    total_ops = sum(node_ops)
    ax2.axhline(y=total_mbs/len(nodes_sorted), color="#16a34a", ls=":", lw=1.5)
    ax2.text(len(nodes_sorted)-1, total_mbs/len(nodes_sorted)+30,
             f"Aggregate: {total_mbs:.0f} MB/s ({total_mbs/1024:.1f} GB/s)\n{total_ops:.0f} ops/s total",
             fontsize=9, color="#16a34a", ha="right")
    ax2.legend(loc="upper right", fontsize=9)
    ax2_ops.legend(loc="center right", fontsize=9)

    plt.tight_layout()
    if args.output:
        plt.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Saved to {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
