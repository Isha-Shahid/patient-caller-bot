"""Download Telnyx call recordings and pair each with its transcript.

Transcripts are named <scenario>-<unix dispatch time>.txt. For each one we pick the
earliest unclaimed recording that started shortly after that dispatch time, save it as
recordings/<same name>.mp3, and print the match so you can sanity-check it.

Usage:
    python fetch_recordings.py                      # last 24h
    python fetch_recordings.py --since 2026-10-28T10:00:00Z
    python fetch_recordings.py --dry-run            # list matches, download nothing
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
API = "https://api.telnyx.com/v2/recordings"
OUT = Path("recordings")
EARLY_SLACK = 10     # recording may start a few seconds "before" dispatch clocks line up
MAX_LAG = 240        # a recording must start within this many seconds after dispatch


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def list_recordings(key, since_iso):
    recs, page = [], 1
    while True:
        qs = urllib.parse.urlencode({"filter[created_at][gte]": since_iso,
                                     "page[size]": 250, "page[number]": page})
        req = urllib.request.Request(f"{API}?{qs}", headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req) as r:
            body = json.load(r)
        recs += body.get("data", [])
        if page >= body.get("meta", {}).get("total_pages", 1):
            return recs
        page += 1


def transcript_info():
    """(call_id, dispatch_epoch, transcript_seconds) for each real scenario transcript."""
    rows = []
    for p in sorted(Path("transcripts").glob("*.txt")):
        m = re.match(r"^(?P<sid>.+)-(?P<ts>\d{10})$", p.stem)
        if not m or m["sid"] == "selftest":
            continue
        stamps = re.findall(r"\[(\d\d):(\d\d)\]", p.read_text(encoding="utf-8"))
        secs = int(stamps[-1][0]) * 60 + int(stamps[-1][1]) if stamps else 0
        rows.append((p.stem, int(m["ts"]), secs))
    return sorted(rows, key=lambda r: r[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="ISO time, e.g. 2026-10-28T10:00:00Z (default: last 24h)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    key = os.getenv("TELNYX_API_KEY")
    if not key:
        sys.exit("TELNYX_API_KEY not set (check your .env)")
    since = args.since or (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")

    recs = [r for r in list_recordings(key, since) if r.get("download_urls", {}).get("mp3")]
    recs.sort(key=lambda r: parse_ts(r["recording_started_at"]))
    print(f"{len(recs)} recordings since {since}")
    OUT.mkdir(exist_ok=True)

    used, unmatched = set(), []
    for call_id, dispatched, t_secs in transcript_info():
        pick = None
        for i, r in enumerate(recs):
            lag = parse_ts(r["recording_started_at"]) - dispatched
            if i not in used and -EARLY_SLACK <= lag <= MAX_LAG:
                pick, pick_lag = i, lag
                break
        if pick is None:
            unmatched.append(call_id)
            print(f"NO MATCH  {call_id}")
            continue
        used.add(pick)
        r = recs[pick]
        r_secs = round(r.get("duration_millis", 0) / 1000)
        print(f"{call_id}: lag {pick_lag:.0f}s, audio {r_secs}s vs transcript {t_secs}s")
        if not args.dry_run:
            # pre-signed URL: no auth header
            urllib.request.urlretrieve(r["download_urls"]["mp3"], OUT / f"{call_id}.mp3")

    if unmatched:
        print(f"\nNo recording found for: {', '.join(unmatched)}")
        print("Check the Telnyx portal; if recording was off for those calls, they need a rerun.")


if __name__ == "__main__":
    main()