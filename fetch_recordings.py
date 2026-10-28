import os, re, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
KEY = os.environ["TELNYX_API_KEY"]
ASSESSMENT_NUMBER = "+18054398008"
# Ignore recordings from before the first real call (UTC, YYYYMMDDHHMMSS).
CUTOFF = "20261028103000"
HEAD = {"Authorization": f"Bearer {KEY}"}
Path("recordings").mkdir(exist_ok=True)

page = 1
while True:
    r = requests.get("https://api.telnyx.com/v2/recordings", headers=HEAD,
                     params={"page[number]": page, "page[size]": 50}, timeout=30)
    r.raise_for_status()
    body = r.json()
    for rec in body.get("data", []):
        to = rec.get("to")
        if to and to != ASSESSMENT_NUMBER:
            continue
        url = (rec.get("download_urls") or {}).get("mp3")
        if not url:
            continue
        stamp = re.sub(r"[^0-9]", "", rec.get("created_at", ""))[:14]
        if stamp < CUTOFF:
            continue
        path = Path("recordings") / f"{stamp}_{rec['id']}.mp3"
        if path.exists():
            continue
        path.write_bytes(requests.get(url, timeout=60).content)
        print("saved", path, rec.get("duration_millis", 0) // 1000, "s", rec.get("channels"))
    if page >= body.get("meta", {}).get("total_pages", 1):
        break
    page += 1
print("done")