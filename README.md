# Patient Caller Bot

A voice bot that phones a clinic's AI receptionist, plays a realistic patient, records and transcribes the call, and helps surface bugs in the agent under test. It is built in Python with LiveKit Agents in pipeline mode (separate speech-to-text, LLM and text-to-speech stages) and places calls through a Telnyx SIP trunk.

- **Findings:** [BUG_REPORT.md](BUG_REPORT.md)
- **Design and tradeoffs:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Evidence:** `transcripts/` (both sides of each call) and `recordings/` (audio, same file names)

## How it works

1. `run_batch.py` (or `dispatch.py` for a single call) dispatches the `caller` agent to a new LiveKit room with the scenario as job metadata: persona name, date of birth and goal.
2. The agent worker dials the test number through the Telnyx trunk and holds the conversation: speech-to-text on the agent's voice, an LLM that plays the patient and steers toward the scenario goal, and text-to-speech back out.
3. Each call writes a timestamped transcript to `transcripts/`. A failed dial writes to `failed_dials/`.
4. Telnyx records the call, and `fetch_recordings.py` downloads the audio and names each file after its transcript.

All test calls go to a single number, set as `ASSESSMENT_NUMBER` in `run_batch.py`.

## Requirements

- Python 3.10 or newer
- Accounts and keys for LiveKit Cloud, Telnyx (a number and a SIP connection), Deepgram, OpenAI and Cartesia
- Call recording turned on for your Telnyx SIP connection (needed for audio)

## Setup

```powershell
git clone <this repo>
cd patient-caller-bot
python -m venv .venv
.venv\Scripts\Activate.ps1        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
```

Fill in `.env`. Every variable the code reads is listed in `.env.example`, which holds placeholders only. Never commit `.env`.

Create a LiveKit outbound SIP trunk that points at your Telnyx SIP connection, and put its ID in `.env`. The trunk config file is kept out of git (see `.gitignore`).

## Run

You need two terminals with the virtual environment active.

**Terminal 1: start the agent worker** (leave it running):

```powershell
python agent.py dev
```

**Terminal 2: place calls.**

Run the full batch of 10 scenarios, one command:

```powershell
python run_batch.py
```

Other ways to run it:

```powershell
python dispatch.py hours-location          # a single scenario
python run_batch.py cancel refill          # specific scenarios, in that order
python run_batch.py --resume               # skip scenarios that already have a finished call of 60s or longer
python run_batch.py --start-from wrong-dob # skip everything before this scenario
python run_batch.py --pause 120 --retries 2
```

The batch runner pauses between calls (default 90s). If a dial fails (for example a SIP 408), it retries with backoff (60s, 120s, 240s) before stopping. A call that is still running after the wait limit is not retried, so the clinic is never double-called. Any call under 60s is flagged for a redo, and the run ends by printing a ready-to-paste rerun command.

**Download the audio** after a batch:

```powershell
python fetch_recordings.py --since 2026-10-28T10:00:00Z --dry-run   # check the matches first
python fetch_recordings.py --since 2026-10-28T10:00:00Z
```

This pulls the Telnyx recordings and saves each one as `recordings/<scenario>-<timestamp>.mp3`, paired with its transcript by start time.

## Scenarios

Defined in `scenarios.json`:

| Scenario | What the patient does |
|----------|-----------------------|
| `hours-location` | Asks about office hours, address, parking and what to bring |
| `schedule-knee` | Books an appointment for knee pain next week |
| `reschedule` | Moves an existing appointment |
| `cancel` | Cancels an upcoming appointment and asks about a fee |
| `refill` | Requests an ibuprofen 600mg refill |
| `insurance` | Asks whether Blue Cross Blue Shield is accepted and the copay |
| `sunday-request` | Asks for a Sunday 10 AM appointment (outside office hours) |
| `wrong-dob` | Gives a date of birth that does not match the record |
| `medical-advice` | Asks a medication safety question the agent should not answer |
| `changes-mind` | Starts a booking request and changes course partway |

## Results

The 10 calls submitted for review, each with a transcript and a matching MP3:

| Scenario | File | Length (transcript) |
|----------|------|---------------------|
| hours-location | `hours-location-1793184141` | 98s |
| schedule-knee | `schedule-knee-1793184291` | 169s |
| reschedule | `reschedule-1793186459` | 152s |
| cancel | `cancel-1793184614` | 147s |
| refill | `refill-1793184812` | 166s |
| insurance | `insurance-1793185028` | 136s |
| sunday-request | `sunday-request-1793185213` | 197s |
| wrong-dob | `wrong-dob-1793186713` | 199s |
| medical-advice | `medical-advice-1793187458` | 160s |
| changes-mind | `changes-mind-1793187160` | 128s |

Other files in `transcripts/` and `recordings/` are earlier attempts that I kept as evidence of iteration and that are not part of the 10 above:

- `reschedule-1793184509` and `medical-advice-1793187008` were cut short (about 55s each), so I reran both scenarios.
- `hours-location-1793183337` was a manual run before the batch runner existed.

`docs/early-tests/` holds logs from development, including the self-tests (some were calls to my own phone, not the test line) and the Twilio 403 failure that led me to switch to Telnyx.

## Repo layout

```
agent.py              the caller agent (STT -> LLM -> TTS pipeline, dialing, transcript writing)
dispatch.py           dispatch one scenario or a self-test
run_batch.py          run scenarios in sequence with retries, resume and reporting
fetch_recordings.py   download Telnyx recordings and pair them with transcripts
scenarios.json        patient personas and goals
transcripts/          call transcripts (both sides)
recordings/           call audio (MP3), matching the transcript names
failed_dials/         records of calls that failed to connect
docs/early-tests/     development logs
BUG_REPORT.md         bugs found in the agent under test
ARCHITECTURE.md       design decisions and tradeoffs
```

## Notes

- The `CLINIC_AGENT` lines in transcripts are my bot's speech-to-text of the agent's voice, so occasional garbled words are transcription errors, not agent errors. `BUG_REPORT.md` lists the ones that need audio to settle.
- Cost for the full set of calls was within the $20 budget. Receipts are submitted separately.
