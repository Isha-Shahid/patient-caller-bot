# Architecture

## How it works

A LiveKit agent worker (`agent.py`) registers under the name `caller`. `dispatch.py` creates a LiveKit room and dispatches a job to that worker, passing the scenario goal and phone number as job metadata. When the job starts, the agent builds an `AgentSession` with a separate speech-to-text, LLM and text-to-speech component, starts the session in the room, and then places an outbound SIP call into the same room through the LiveKit SIP API (`create_sip_participant`). When the callee answers, the pipeline listens to the other agent, transcribes it, asks the LLM for the patient's next line, and speaks it back. The carrier records the call and `fetch_recordings.py` downloads the audio. Transcripts are written per call so each conversation can be reviewed alongside its audio.

## Key choices and trade-offs

**Pipeline mode, as required.** Separate STT, LLM and TTS gives control over each stage and makes latency easy to measure per stage.

**STT: Deepgram Nova-3.** Low streaming latency and good accuracy on telephone-quality audio, which matters because the other side arrives over a phone line. Alternatives considered: [FILL IN, for example AssemblyAI, Whisper-based services] - chose Deepgram for [FILL IN reason after your testing].

**LLM: GPT-4o-mini.** A small, fast model keeps response time low, and the persona prompt is short and constrained, so a larger model was not needed. The trade-off is weaker handling of very long or tricky conversations. [FILL IN: any model you tried and what changed.]

**TTS: Cartesia.** Chosen for fast time-to-first-audio and natural-sounding voices, which directly affects how human the caller feels. [FILL IN: voice choice and why.]

**Turn detection and interruptions.** Silero VAD detects speech, and the LiveKit multilingual turn-detector model decides when the other side has finished a turn, so the bot does not cut in during pauses. The bot waits for the other side to speak first, as a real caller would. For barge-in tests the same pipeline lets the bot be interrupted, and scenarios that test interruption are marked as such. [FILL IN: any tuning of endpointing delay you did.]

**Persona prompt.** The persona keeps replies short, uses plain spoken language and stays on one goal per call, then ends the call politely. Short turns reduce latency and keep the conversation realistic.

**Phone connection.** LiveKit's SIP integration connects the room to a carrier trunk. [FILL IN: the carrier you actually used for your real calls and why.]

**Latency.** Streaming STT and TTS, a small LLM, and a single process close to the LiveKit region keep response time low. [FILL IN: measured delay between the other side finishing and the bot speaking, from your calls.]

## What I iterated on

[FILL IN after your calls. Examples: early calls where the bot talked over the agent, how you changed turn detection, persona wording changes, a bug you fixed in the dial flow. Reviewers want evidence you listened and improved.]
