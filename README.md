# Patient Caller Bot

A Python voice bot built on LiveKit Agents (pipeline mode) that phones a test line, plays a realistic patient, records the call, and produces transcripts for bug hunting.

Pipeline: Deepgram (speech-to-text) -> OpenAI chat model (LLM) -> Cartesia (text-to-speech). No realtime or speech-to-speech models and no hosted voice-agent platforms are used.

## Requirements

- Python 3.10+
- A LiveKit Cloud project (URL, API key, API secret)
- An outbound SIP trunk configured in LiveKit (`outbound-trunk.json`) and a phone number from your SIP carrier
- API keys for Deepgram, OpenAI and Cartesia

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then fill in real values
```

Create the LiveKit outbound trunk once (CLI or dashboard) and put its ID in `.env` as `SIP_OUTBOUND_TRUNK_ID`.

## Run

Terminal 1 (leave running):

```powershell
python agent.py download-files   # first time only: fetches VAD and turn-detector models
python agent.py dev
```

Terminal 2:

```powershell
python dispatch.py <scenario-name>
```

Example: `python dispatch.py hours-location`

After the call finishes, wait about a minute for the carrier to finalize the recording, then:

```powershell
python fetch_recordings.py
```

Recordings are saved to `recordings/` (MP3) and transcripts to `transcripts/`.

## Project layout

| File | Purpose |
|---|---|
| `agent.py` | The caller agent: speech pipeline, patient persona, outbound dial, transcript logging |
| `dispatch.py` | Starts one call for a named scenario by dispatching a job to the agent |
| `fetch_recordings.py` | Downloads call recordings from the carrier |
| `scenarios` (in `dispatch.py`) | The list of patient scenarios (scheduling, refills, hours, insurance, edge cases) |
| `BUG_REPORT.md` | Issues found in the agent under test |
| `ARCHITECTURE.md` | How it works and why |

## Scenarios covered

[FILL IN after you finish your calls. Example list:]

1. Simple appointment scheduling
2. Rescheduling an appointment
3. Cancelling an appointment
4. Medication refill request
5. Office hours and location questions
6. Insurance questions
7. Interruptions and barge-in
8. Unclear or rambling request
9. Request outside normal hours (for example a weekend)
10. [your own edge case]

## Notes

- Secrets live only in `.env`, which is git-ignored. Never commit it.
- All test calls were placed from one phone number: [FILL IN, E.164 format].
- Call the assessment number only. Do not point this bot at any other number.
