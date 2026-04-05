#!/usr/bin/env python3
import csv
import sys
from collections import defaultdict

if len(sys.argv) < 3:
    print("Usage: cluster_from_dist.py <dist_tsv> <threshold>")
    sys.exit(1)

dist_path = sys.argv[1]
threshold = float(sys.argv[2])

parent = {}

def find(x):
    parent.setdefault(x, x)
    if parent[x] != x:
        parent[x] = find(parent[x])
    return parent[x]

def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra

with open(dist_path, newline="") as fh:
    reader = csv.reader(fh, delimiter="\t")
    for row in reader:
        if len(row) < 3:
            continue
        a, b, d = row[0], row[1], float(row[2])
        if d <= threshold:
            union(a, b)

clusters = defaultdict(list)
for key in list(parent.keys()):
    clusters[find(key)].append(key)

for i, members in enumerate(sorted(clusters.values(), key=lambda x: (len(x), x), reverse=True), 1):
    print(f"cluster_{i}\t{len(members)}\t" + ",".join(sorted(members)))
