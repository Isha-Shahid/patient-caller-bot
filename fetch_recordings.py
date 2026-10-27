import os, requests
from pathlib import Path
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()
sid, token = os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]
client = Client(sid, token)
Path("recordings").mkdir(exist_ok=True)

for call in client.calls.list(from_="+16402133638", limit=50):
    for rec in client.recordings.list(call_sid=call.sid):
        path = Path("recordings") / f"{call.start_time:%Y%m%d-%H%M%S}_{call.to}_{call.sid}.mp3"
        if path.exists():
            continue
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Recordings/{rec.sid}.mp3"
        r = requests.get(url, auth=(sid, token))
        path.write_bytes(r.content)
        print("saved", path, f"{call.duration}s")