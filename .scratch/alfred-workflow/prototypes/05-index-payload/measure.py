#!/usr/bin/env python
"""
PROTOTYPE - throwaway. Measures the payload side of ticket 05.

Runs the generator across a scale sweep and reports, per scale:
  - minified CLI-JSON envelope bytes (ticket 03 `fd --json`)
  - Alfred items bytes: fat (per-mod URL blocks) vs lean (one urls object)
  - what folding description into `match` costs
  - the mirror-URL fraction of the payload
  - gzip size (what a cached file costs on disk, and a redundancy signal)
  - wall-clock to build + serialise (the CLI's cost before Alfred sees a byte)
  - json.loads time for the fat payload (a proxy for Alfred's own parse step)

The keyboard-latency and matching-quality halves need Alfred itself - see probe.md.
"""

import gzip
import io
import json
import time

import generate

SCALES = [100, 1000, 5000, 15000, 25000]


def _minified(payload):
    buf = io.StringIO()
    json.dump(payload, buf, ensure_ascii=False, separators=(",", ":"))
    return buf.getvalue()


def _url_bytes(entities):
    return sum(len(v.encode("utf-8"))
               for e in entities for v in e["urls"].values() if v)


def main():
    hdr = (f"{'entities':>8} | {'cli-json':>9} | {'fat':>9} | {'fat+desc':>9} | "
           f"{'lean':>9} | {'url %(fat)':>10} | {'fat gzip':>9} | {'build s':>8} | {'parse s':>8}")
    print(hdr)
    print("-" * len(hdr))
    for scale in SCALES:
        t0 = time.perf_counter()
        entities = generate.build_index(scale, seed=42)
        cli = _minified(generate.cli_json_envelope(entities))
        fat = _minified(generate.alfred_items(entities, False, lean=False))
        fat_desc = _minified(generate.alfred_items(entities, True, lean=False))
        lean = _minified(generate.alfred_items(entities, False, lean=True))
        build_s = time.perf_counter() - t0

        fat_b = len(fat.encode("utf-8"))
        t1 = time.perf_counter()
        json.loads(fat)
        parse_s = time.perf_counter() - t1

        gz = len(gzip.compress(fat.encode("utf-8"), compresslevel=6))
        url_b = _url_bytes(entities)
        n = len(entities)
        print(f"{n:>8} | {len(cli.encode())/1e6:>8.2f}M | {fat_b/1e6:>8.2f}M | "
              f"{len(fat_desc.encode())/1e6:>8.2f}M | {len(lean.encode())/1e6:>8.2f}M | "
              f"{100*url_b/fat_b:>9.1f}% | {gz/1e6:>8.2f}M | {build_s:>8.3f} | {parse_s:>8.3f}")


if __name__ == "__main__":
    main()
