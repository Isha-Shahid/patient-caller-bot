import argparse, asyncio, json, re, time
from pathlib import Path
from dotenv import load_dotenv
from livekit import api

load_dotenv()
ASSESSMENT_NUMBER = "+18054398008"
ORDER = ["hours-location", "schedule-knee", "reschedule", "cancel", "refill",
         "insurance", "sunday-request", "wrong-dob", "medical-advice", "changes-mind"]
PAUSE_BETWEEN = 90          # seconds between calls (was 45)
MAX_WAIT = 260              # give up on one call after this many seconds
MIN_OK_SECONDS = 60         # calls shorter than this are flagged / not counted on --resume
DIAL_RETRIES = 3            # extra attempts after a failed dial
BACKOFF = [60, 120, 240]    # seconds to wait before retry 1, 2, 3


def status(call_id):
    if (Path("failed_dials") / f"{call_id}.txt").exists():
        return "failed"
    p = Path("transcripts") / f"{call_id}.txt"
    if p.exists() and "call ended" in p.read_text(encoding="utf-8"):
        return "done"
    return None


def length_seconds(path):
    text = Path(path).read_text(encoding="utf-8")
    stamps = re.findall(r"\[(\d\d):(\d\d)\]", text)
    return int(stamps[-1][0]) * 60 + int(stamps[-1][1]) if stamps else 0


def already_done(sid):
    """True if a finished, non-short transcript for this scenario already exists."""
    pat = re.compile(rf"^{re.escape(sid)}-\d+$")
    for p in Path("transcripts").glob(f"{sid}-*.txt"):
        if not pat.match(p.stem):
            continue
        if "call ended" in p.read_text(encoding="utf-8") and length_seconds(p) >= MIN_OK_SECONDS:
            return True
    return False


async def run_one(lk, scenarios, sid):
    s = scenarios[sid]
    call_id = f"{sid}-{int(time.time())}"
    await lk.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
            agent_name="caller", room=call_id,
            metadata=json.dumps({"call_id": call_id, "phone_number": ASSESSMENT_NUMBER,
                                 "name": s["name"], "dob": s["dob"], "goal": s["goal"]}),
        )
    )
    print(f"-> {sid}: dispatched {call_id}")
    start = time.time()
    while time.time() - start < MAX_WAIT:
        await asyncio.sleep(3)
        st = status(call_id)
        if st:
            return call_id, st
    return call_id, "timeout"


async def run_with_retries(lk, scenarios, sid, retries):
    """Retry only when the dial itself failed (status 'failed').
    A 'timeout' is NOT retried: the call may still be live, and redialing could double-call."""
    for attempt in range(retries + 1):
        call_id, st = await run_one(lk, scenarios, sid)
        if st != "failed":
            return call_id, st
        if attempt < retries:
            wait = BACKOFF[min(attempt, len(BACKOFF) - 1)]
            print(f"dial failed for {sid} (attempt {attempt + 1}/{retries + 1}); "
                  f"retrying in {wait}s...")
            await asyncio.sleep(wait)
    return call_id, "failed"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenarios", nargs="*", help="scenario ids (default: full ORDER)")
    ap.add_argument("--resume", action="store_true",
                    help="skip scenarios that already have a finished, non-short transcript")
    ap.add_argument("--start-from", help="skip everything before this scenario id")
    ap.add_argument("--pause", type=int, default=PAUSE_BETWEEN)
    ap.add_argument("--retries", type=int, default=DIAL_RETRIES)
    args = ap.parse_args()

    scenarios = json.load(open("scenarios.json", encoding="utf-8"))
    order = args.scenarios or ORDER
    if args.start_from:
        order = order[order.index(args.start_from):]
    if args.resume:
        skipped = [s for s in order if already_done(s)]
        order = [s for s in order if s not in skipped]
        if skipped:
            print(f"resume: skipping already completed: {', '.join(skipped)}")

    lk = api.LiveKitAPI()
    results, short, remaining = [], [], []
    try:
        for i, sid in enumerate(order, 1):
            print(f"\n[{i}/{len(order)}] {sid}")
            call_id, st = await run_with_retries(lk, scenarios, sid, args.retries)
            if st != "done":
                print(f"STOPPED: {sid} ended with status '{st}'. Check Terminal 1 and failed_dials/.")
                remaining = order[i - 1:]
                break
            secs = length_seconds(Path("transcripts") / f"{call_id}.txt")
            flag = "" if secs >= MIN_OK_SECONDS else "  <-- SHORT, redo this one later"
            print(f"done: {sid} ({secs}s){flag}")
            results.append((sid, secs))
            if secs < MIN_OK_SECONDS:
                short.append(sid)
            if i < len(order):
                print(f"waiting {args.pause}s...")
                await asyncio.sleep(args.pause)
    finally:
        await lk.aclose()

    print("\nSummary:")
    for sid, secs in results:
        print(f"  {sid}: {secs}s")
    if short:
        print(f"\nShort calls to redo: {', '.join(short)}")
    if remaining:
        print(f"Not completed: {', '.join(remaining)}")
    todo = short + remaining
    if todo:
        print("\nRerun with:\n  python run_batch.py " + " ".join(dict.fromkeys(todo)))


if __name__ == "__main__":
    asyncio.run(main())