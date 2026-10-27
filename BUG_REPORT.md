# Bug Report

Issues found in the agent under test, based on the recorded calls in `recordings/` and `transcripts/`.

Only list things that actually happened in a call. Link each one to the transcript and a timestamp so it can be checked. A few well-described, important bugs beat a long list of small ones.

## Summary

| # | Bug | Severity | Call |
|---|-----|----------|------|
| 1 | [FILL IN] | High / Medium / Low | transcript-XX.txt at M:SS |

## Entry format

### Bug 1: [short title]

- **Severity:** High / Medium / Low
- **Call:** `transcript-XX.txt` at M:SS (audio: `recording-XX.mp3`)
- **What I said:** [the patient's line]
- **What the agent said or did:** [quote the transcript]
- **Why it's a problem:** [for example: wrong information, unsafe, confusing, ignores a request]
- **Expected behavior:** [what a correct agent should have done]

## What to listen for

- Wrong or invented information (hours, locations, insurance, appointment times)
- Booking something that should not be possible (closed days, past dates)
- Failing to confirm or repeat key details back (name, date of birth, date, time)
- Ignoring or mishandling an interruption
- Loops, repeated questions, or getting stuck
- Not handling an unclear or off-topic request
- Unsafe medical handling, for example giving advice it shouldn't or missing urgency
- Long silences, cutting the caller off, or hanging up too early
