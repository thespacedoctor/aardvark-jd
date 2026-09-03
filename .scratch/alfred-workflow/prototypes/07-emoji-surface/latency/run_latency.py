#!/usr/bin/env python
"""PROTOTYPE - wayfinder ticket 07. THROWAWAY.

Part A of the ticket 07 probe: how long does the emoji suggestion call
actually take? The ticket says the median is what decides whether the Claude
suggestion can sit on Alfred's interactive path, so measure the spread over
many realistic new-folder titles rather than eyeballing one.

This calls the Claude API with the EXACT request shape aardvark uses
(`emoji_picker.CLAUDE_MODEL`, effort, max_tokens, system prompt), so the
numbers transfer directly. It needs ANTHROPIC_API_KEY in the environment and
the `anthropic` package installed (both true wherever `aardvark add_area`
already works).

Run:

    python run_latency.py                 # 3 passes over titles.txt
    python run_latency.py --passes 5
    python run_latency.py --titles other.txt

Output: one line per call, then a summary (median / p90 / max, failure rate,
mean output-token count - the thinking budget is the usual reason a "trivial"
classification is slow).
"""
import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

# THROWAWAY: REACH STRAIGHT INTO THE PACKAGE FOR THE CANONICAL REQUEST SHAPE.
from aardvark_jd import emoji_picker

HERE = Path(__file__).resolve().parent


def load_titles(path):
    """Read "title | description" lines, skipping blanks and # comments."""
    pairs = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            title, description = (part.strip() for part in line.split("|", 1))
        else:
            title, description = line, ""
        pairs.append((title, description))
    return pairs


def timed_call(client, title, description):
    """One emoji request. Returns (elapsed_seconds, emoji_or_None, output_tokens, note)."""
    prompt = f"Folder title: {title}"
    if description:
        prompt += f"\nFolder description: {description}"

    start = time.perf_counter()
    try:
        response = client.messages.create(
            model=emoji_picker.CLAUDE_MODEL,
            max_tokens=emoji_picker.CLAUDE_MAX_TOKENS,
            output_config={"effort": emoji_picker.CLAUDE_EFFORT},
            system=emoji_picker._SUGGESTER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as error:  # NOQA: BLE001 - PROBE, REPORT ANYTHING
        return time.perf_counter() - start, None, 0, f"error: {type(error).__name__}: {error}"
    elapsed = time.perf_counter() - start

    output_tokens = getattr(getattr(response, "usage", None), "output_tokens", 0)

    if getattr(response, "stop_reason", None) == "refusal":
        return elapsed, None, output_tokens, "refusal"

    reply = ""
    for block in getattr(response, "content", None) or []:
        if getattr(block, "type", None) == "text":
            reply = block.text
            break

    validated = emoji_picker._validate_single_emoji(reply)
    if validated is None:
        return elapsed, None, output_tokens, f"not-one-emoji: {reply!r}"
    return elapsed, validated, output_tokens, ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument("--titles", default=str(HERE / "titles.txt"))
    parser.add_argument("--out", default=str(HERE / "latency-results.json"))
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set - this probe needs it (so does `aardvark add_area`).")
    try:
        import anthropic
    except ImportError:
        sys.exit("the `anthropic` package is not installed in this interpreter.")

    client = anthropic.Anthropic(
        timeout=emoji_picker.CLAUDE_TIMEOUT_SECONDS,
        max_retries=emoji_picker.CLAUDE_MAX_RETRIES,
    )

    titles = load_titles(args.titles)
    print(f"{len(titles)} titles x {args.passes} passes = {len(titles) * args.passes} calls")
    print(f"model={emoji_picker.CLAUDE_MODEL} effort={emoji_picker.CLAUDE_EFFORT} "
          f"max_tokens={emoji_picker.CLAUDE_MAX_TOKENS} timeout={emoji_picker.CLAUDE_TIMEOUT_SECONDS}s\n")
    print(f"{'pass':>4}  {'secs':>6}  {'tok':>5}  {'llm':>3}  {'offline':>7}  title")
    print("-" * 72)

    records = []
    for pass_index in range(1, args.passes + 1):
        for title, description in titles:
            elapsed, llm_emoji, tokens, note = timed_call(client, title, description)
            offline_emoji = emoji_picker.pick_emoji(title, description)
            records.append({
                "pass": pass_index,
                "title": title,
                "description": description,
                "elapsed_s": round(elapsed, 3),
                "output_tokens": tokens,
                "llm_emoji": llm_emoji,
                "offline_emoji": offline_emoji,
                "note": note,
            })
            flag = llm_emoji or "-"
            print(f"{pass_index:>4}  {elapsed:>6.2f}  {tokens:>5}  {flag:>3}  "
                  f"{offline_emoji:>7}  {title}{('  <' + note + '>') if note else ''}")

    Path(args.out).write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    times = [r["elapsed_s"] for r in records]
    ok = [r for r in records if r["llm_emoji"]]
    failed = [r for r in records if not r["llm_emoji"]]
    agree = [r for r in ok if r["llm_emoji"] == r["offline_emoji"]]
    toks = [r["output_tokens"] for r in ok if r["output_tokens"]]

    def pct(values, fraction):
        ordered = sorted(values)
        return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]

    print("\n" + "=" * 72)
    print(f"calls              {len(records)}")
    print(f"failed / fell back {len(failed)}  ({100 * len(failed) / len(records):.0f}%)")
    print(f"latency  median    {statistics.median(times):.2f}s")
    print(f"         mean      {statistics.mean(times):.2f}s")
    print(f"         p90       {pct(times, 0.90):.2f}s")
    print(f"         p95       {pct(times, 0.95):.2f}s")
    print(f"         max       {max(times):.2f}s")
    print(f"         min       {min(times):.2f}s")
    if toks:
        print(f"output tokens med  {statistics.median(toks):.0f}   max {max(toks)}")
    print(f"llm == offline     {len(agree)}/{len(ok)}  (how often the API pick just matches the free one)")
    if failed:
        print("\nfailures:")
        for r in failed:
            print(f"  {r['title']!r}: {r['note']}")
    print(f"\nfull results: {args.out}")
    print("paste the block between the ==== lines into ticket 07 when done.")


if __name__ == "__main__":
    main()
