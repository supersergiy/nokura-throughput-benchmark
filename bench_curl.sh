#!/bin/bash
# Nokura throughput benchmark — pure curl.
# Usage: ./bench_curl.sh [num_chunks] [workers_csv]
#   ./bench_curl.sh              # 2000 chunks, sweep 8,32,64,128,256
#   ./bench_curl.sh 500 64       # 500 chunks, 64 parallel
#   ./bench_curl.sh 1000 8,32,64 # 1000 chunks, sweep 8,32,64

URL="https://c10s.pni.princeton.edu/zfish_2025_public/stack/0406/40_40_45"
N="${1:-2000}"
WORKERS="${2:-8,32,64,128,256}"

python3 -c "
import random, time, subprocess, sys
random.seed(42)
urls = [f'$URL/{x}-{x+1024}_{y}-{y+1024}_3000-3001'
        for x in range(0,65536,1024) for y in range(0,51200,1024)]
random.shuffle(urls)
urls = urls[:$N]
with open('/tmp/_bench_urls.txt','w') as f:
    f.write('\n'.join(urls)+'\n')
n = len(urls)
print(f'Chunks: {n} x 1MB\n')
print(f'{\"Workers\":>8} {\"Time(s)\":>8} {\"MB/s\":>8}')
print('-'*28)
for w in '$WORKERS'.split(','):
    t0 = time.monotonic()
    subprocess.run(f'xargs -P {w} -n 1 curl -s -o /dev/null < /tmp/_bench_urls.txt',
                   shell=True, check=True)
    dt = time.monotonic() - t0
    print(f'{w:>8} {dt:>8.1f} {n/dt:>8.1f}')
"
rm -f /tmp/_bench_urls.txt
