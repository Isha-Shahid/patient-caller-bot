# Architecture

patient-caller-bot places an outbound phone call to a clinic's voice agent, plays a simulated patient following one scenario, and writes a timestamped transcript of the conversation for review.

## Call flow

```
dispatch.py <scenario>
   |  reads scenarios.json, creates a LiveKit room "<scenario>-<unix time>",
   |  dispatches agent "caller" with metadata {call_id, phone_number, name, dob, goal}
   v
agent.py (LiveKit worker, `python agent.py dev`)
   |  starts the AgentSession and dials at the same time
   |  create_sip_participant(outbound trunk, wait_until_answered=True)
   v
Clinic line  <--- SIP trunk ---> LiveKit room <---> STT -> LLM -> TTS
   |
   v
transcripts/<call_id>.txt   (or failed_dials/ if the dial failed)
```

1. **Dispatch.** `dispatch.py` picks a scenario, builds a unique room name, and sends an explicit agent dispatch. The scenario's patient name, date of birth and goal travel in the job metadata, so the worker needs no other state.
2. **Session start.** The worker connects, parses the metadata, builds the persona prompt, and starts the `AgentSession` as a background task while the dial is in progress, so no audio is missed once the clinic answers.
3. **Dial.** The call goes out through a LiveKit SIP outbound trunk and blocks until it is answered. If dialing fails, the error is logged, the partial transcript is moved to `failed_dials/`, and the room is deleted.
4. **Greeting.** The persona is told to let the other side speak first. If nothing is heard for 8 seconds after the call is answered, the bot says a single short "Hello?".
5. **Conversation.** Runs until the bot calls `end_call`, the session closes, or the time limits below are hit.
6. **Teardown.** The room is deleted, which ends the call, and the transcript file is flushed and closed.

## Voice pipeline

| Stage | Choice |
|---|---|
| Voice activity detection | Silero VAD |
| Speech to text | Deepgram `nova-3`, `en-US` |
| LLM | OpenAI `gpt-4o-mini` |
| Text to speech | Cartesia (plugin defaults) |
| End-of-turn detection | LiveKit `MultilingualModel` turn detector, layered on VAD |

The choices favor low latency and low cost, which matter more on a phone call than model size. Short patient utterances keep the LLM and TTS stages fast. Interruption handling uses the LiveKit Agents defaults (VAD plus the turn detector); nothing is custom-tuned.

## Persona prompt

The prompt in `agent.py` makes the model behave like a patient instead of an assistant:

- **Register.** Short, casual, usually under 15 words, with sparing fillers. It avoids assistant phrases such as "How can I assist" and "Have a great day".
- **One thing at a time.** It answers only what is asked and asks one question at a time.
- **Details on demand.** Name, date of birth and callback number are given only when the clinic asks, after which the bot returns to its goal.
- **Goal checklist.** The bot tracks every part of its goal, asks again once for anything skipped, and confirms anything vague or confusing.
- **No early exit.** If the goal is met quickly, it asks one related follow-up (what to bring, arrival time, parking, cost) before finishing.
- **Clean ending.** It says goodbye out loud first, then calls `end_call` in a separate step.

## Call control and safety

- **Fixed target.** `dispatch.py` hardcodes the assessment number. The only override is `--self-test <number>`, so the bot cannot be pointed at an arbitrary number by accident.
- **Cooldown.** A 240-second cooldown between dispatches is enforced through a local `.last_dispatch` file.
- **`end_call` guard.** The tool refuses to hang up in the first 60 seconds after the call is answered and tells the model to ask another follow-up instead.
- **Time limits.** The bot wraps up politely at about 150 seconds and hangs up regardless at about 185 seconds. Both timers start after the greeting check, so they are approximate relative to the moment of answer.
- **Failed dials** are isolated in `failed_dials/` so they do not mix with real transcripts.

## Output

Each call writes `transcripts/<call_id>.txt`, one line per turn:

```
[mm:ss] ROLE: text
```

Roles are `PATIENT_BOT` (this bot), `CLINIC_AGENT` (the other side, as heard by STT) and `SYSTEM` (call answered, wrap-up, hard limit, dial failure, call ended).

## Configuration

Environment variables, loaded from `.env` (see `.env.example`):

- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- `SIP_OUTBOUND_TRUNK_ID`
- `DEEPGRAM_API_KEY`, `OPENAI_API_KEY`, `CARTESIA_API_KEY`
- `CALLER_PHONE_SPOKEN` (optional): the callback number as the bot says it aloud

## Known limitations

- Transcripts come from speech-to-text, so clinic-side wording can contain recognition errors. No audio is recorded.
- Role labels assume the clinic is the only other speaker in the room.
- The cooldown is a local file, so it does not protect against dispatching from two machines.
- STT is set to English only, although the turn detector is multilingual.
- Time limits are approximate, as noted above.
