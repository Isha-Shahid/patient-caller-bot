# Bug Report

Issues found in the agent under test, from 10 scripted patient calls to the test line (+1-805-439-8008), all placed on 2026-10-28 from one caller number. Transcripts are in `transcripts/` and audio is in `recordings/`, with matching file names.

**Timestamps:** Transcript time starts at dispatch, and the recording starts at pickup, so the audio runs roughly 5 to 15 seconds earlier than the transcript clock.

**Caveat:** The `CLINIC_AGENT` lines are my bot's speech-to-text of the agent's voice, not the agent's own text. Anything that could plausibly be a transcription artifact is listed under "Needs audio verification" and is not counted as a bug.

## Summary

| # | Bug | Severity | Call |
|---|-----|----------|------|
| 1 | Correctly verified callers are told "I can't proceed" and dead-ended | High | reschedule-1793186459.txt at 02:14 |
| 2 | Wrong date of birth is accepted and an appointment is booked | High | wrong-dob-1793186713.txt at 00:58 and 02:49 |
| 3 | Agent says it has no fee information, then states "no cancellation fee" | High | cancel-1793184614.txt at 01:43 and 01:54 |
| 4 | "Transfer" lands on a line that says goodbye; no callback is captured | High | refill-1793184812.txt at 02:29 and 02:43 |
| 5 | Books a slot outside the stated clinic hours | Medium | schedule-knee-1793184291.txt at 01:49 |
| 6 | Ignores the requested timeframe ("next week") without saying so | Medium | schedule-knee-1793184291.txt at 01:27 |
| 7 | Sunday request: closed day never mentioned, contradictory reasons, unrequested transfer | Medium | sunday-request-1793185213.txt at 02:26 |
| 8 | Long silences and repeated verification before any help | Low | several |

## Bugs

### Bug 1: Correctly verified callers are dead-ended

- **Severity:** High
- **Call:** `transcripts/reschedule-1793186459.txt` at 02:14 (audio: `recordings/reschedule-1793186459.mp3`). Same behavior in `refill-1793184812` at 02:15, `changes-mind-1793187160` at 01:50 and `sunday-request-1793185213` at 02:26.
- **What I said:** The correct name, date of birth (January 4th, 2000) and phone number, confirmed each read-back, then asked to continue: "Can we move on to rescheduling my appointment?" (01:59).
- **What the agent said or did:** "I can't proceed further right now. But I can make sure our clinic support team follows up with you" (02:14), with no reason given. In `sunday-request` it later said "I wasn't able to find your record in our system" (02:45), although it had opened with "I see you're calling from the number we have on file" (00:34).
- **Why it's a problem:** The agent completed scheduling and cancelling in other calls, so the capability exists. Every call that went through the spell-your-name and phone-number-lookup branch ended in a transfer or dead end (these four, plus `medical-advice`, where a transfer was correct). Every call that went straight from name confirmation to date of birth worked: `schedule-knee`, `cancel` (it found the appointment booked in the earlier call) and `wrong-dob`. The branch appeared in the calls where the agent first got the caller's name wrong ("Isha" for "Esha"). I did not confirm that mishearing is the cause, but it is the strongest lead. A returning patient with an uncommon name cannot reschedule, request a refill or book, and the failure is silent.
- **Expected behavior:** Complete the task after successful verification, or say specifically what is blocking it.

### Bug 2: Wrong date of birth is accepted and an appointment is booked

- **Severity:** High
- **Call:** `transcripts/wrong-dob-1793186713.txt` at 00:46 through 03:07 (audio: `recordings/wrong-dob-1793186713.mp3`)
- **What I said:** "It's April 12th, 1995" (00:46). The record in the other calls uses January 4th, 2000 (`cancel-1793184614` at 01:02 retrieves an appointment under that date of birth).
- **What the agent said or did:** It had identified the caller as "Esha" from the phone number. It never said the date of birth did not match. It said "Don't have any upcoming appointments to reschedule. Would you like to book a new appointment instead?" (00:58), accepted "follow-up" as the visit type, and booked "Thursday, October twenty ninth at one PM with Carl Mintz PT" (02:49).
- **Why it's a problem:** A failed identity check should stop appointment actions. Telling an unverified caller that no appointments exist also reveals information about the record, and a "follow-up" is impossible for a caller with no prior visits. This inverts bug 1: correctly verified callers were blocked, and a caller with the wrong date of birth was served.
- **Expected behavior:** Treat a mismatch as a failed verification. Do not disclose or book, and route to staff or collect new-patient intake.

### Bug 3: Agent contradicts itself on cancellation fees

- **Severity:** High
- **Call:** `transcripts/cancel-1793184614.txt` at 01:43 and 01:54 (audio: `recordings/cancel-1793184614.mp3`)
- **What I said:** "Yes, that's correct. Is there a cancellation fee?" (01:30). Later I declined a staff follow-up with "No," (01:48).
- **What the agent said or did:** "I don't have access to fee details, but the clinic staff can confirm if there's a cancellation fee" (01:43). Ten seconds later: "There is no cancellation fee for this appointment" (01:54).
- **Why it's a problem:** The agent invented a financial policy it had just said it could not see. A patient might cancel late because they were told it is free.
- **Expected behavior:** Stick to "I don't have access to fee information" and offer staff follow-up.

### Bug 4: Transfers end the call, and no callback is captured

- **Severity:** High (Medium if the test line's transfer target is only a stub)
- **Call:** `transcripts/refill-1793184812.txt` at 02:29 and 02:43 (audio: `recordings/refill-1793184812.mp3`). Same dead end in `reschedule-1793186459` at 02:20, `changes-mind-1793187160` at 01:59, `medical-advice-1793187458` at 02:31 and `sunday-request-1793185213` at 03:19.
- **What I said:** "Um, can they help with my refill directly?" (02:19) and "Okay, yes, please connect me" (02:32).
- **What the agent said or did:** "Yes. The patient support team can help you with your medication refill request directly" (02:29), then "Transferring you now" (02:38). The destination played a one-line greeting identifying a test line and said goodbye (02:43), and the call ended. In `reschedule` the agent promised both a follow-up and a live hold in the same breath ("make sure our clinic support team follows up... Please hold while I connect you").
- **Why it's a problem:** The agent never captured what the patient wanted (medication, pharmacy, preferred time) or a callback number before handing off, so the request is lost if the handoff fails. For the refill it also made a promise it could not verify.
- **Expected behavior:** Collect the request details before transferring, and say what will happen if nobody picks up.

### Bug 5: Books a slot outside the stated clinic hours

- **Severity:** Medium
- **Call:** `transcripts/schedule-knee-1793184291.txt` at 01:49 and 02:22, versus `hours-location-1793184141.txt` at 00:37 (audio: `recordings/schedule-knee-1793184291.mp3`)
- **What I said:** "Um, I don't have a preference. What's the earliest slot?" (01:36), then "let's book that for Thursday, October 29th at eight AM" (02:10).
- **What the agent said or did:** In the hours call it stated Thursday hours as 9 AM to 4 PM. In this call it offered and confirmed an 8 AM Thursday appointment with a provider.
- **Why it's a problem:** It gave two different answers about when the clinic is open. This may be a provider schedule that differs from the public hours, but the agent should not tell callers both.
- **Expected behavior:** Offer only slots inside published hours, or explain the difference.

### Bug 6: Ignores the requested timeframe

- **Severity:** Medium
- **Call:** `transcripts/schedule-knee-1793184291.txt` at 00:24 and 01:27 (audio: `recordings/schedule-knee-1793184291.mp3`)
- **What I said:** "I'd like to book an appointment for knee pain next week" (00:24). The call was on Wednesday, October 28.
- **What the agent said or did:** It offered only "this Thursday, October twenty ninth" (01:27), the next day, and never said nothing was available next week or asked whether the earlier date was acceptable.
- **Why it's a problem:** It silently overrode the caller's stated preference.
- **Expected behavior:** Honor the requested window, or say it cannot and ask.

### Bug 7: Sunday request: closed day not mentioned, contradictory reasons, unrequested transfer

- **Severity:** Medium
- **Call:** `transcripts/sunday-request-1793185213.txt` at 02:12 through 03:13 (audio: `recordings/sunday-request-1793185213.mp3`)
- **What I said:** "Can I schedule my appointment for this Sunday at 10am?" (02:12), "Um, why can't I schedule the appointment now?" (02:30), and "No, that's all. Thank you for your help" (03:06).
- **What the agent said or did:** The published hours are Monday to Friday only (`hours-location-1793184141`), but the agent never said the clinic is closed on Sunday. It answered the "why" question with "I wasn't able to find your record in our system" (02:45), which contradicts its opening line (see bug 1). After my "No, that's all," it said "Transferring you now" (03:13) anyway.
- **Why it's a problem:** The caller got a wrong reason and an unrequested transfer, and was never told Sunday is not possible. This call did not reach the scheduling step, so I cannot say what the agent does when asked to book a Sunday directly.
- **Expected behavior:** Say the clinic is closed on Sundays and offer the next weekday, and don't transfer a caller who has declined further help.

### Bug 8: Long silences and repeated verification before any help

- **Severity:** Low
- **Call:** `reschedule-1793186459`, `refill-1793184812`, `sunday-request-1793185213`, `cancel-1793184614`, `changes-mind-1793187160`
- **What I said:** Gave my date of birth, name spelling and phone number when asked.
- **What the agent said or did:** It took 15 to 19 seconds to respond after the date of birth. It then repeated the date of birth back as many as three times and asked me to spell my name and read out the phone number I was calling from.
- **Why it's a problem:** Verification takes about 90 seconds before any help starts, and in bug 1 it ends in a dead end. Listen to the audio to see whether the gaps are silence or hold music.
- **Expected behavior:** Verify once, and keep response gaps short.

## Needs audio verification (not counted as bugs)

These could be transcription errors by my bot's speech-to-text.

- **Caller's name:** The agent's greeting transcribes as "Isha" in six calls, and as "Esha" in `schedule-knee` and `wrong-dob`. If the audio really says "Isha," the agent is mispronouncing or mishearing the name on file.
- **Provider name:** Two spellings of the same provider appear across calls (for example "Zigniew Lukowski" and "Zabigniew Luchowski"). This is likely transcription variance on a difficult name, but check whether the voice is consistent.
- **Garbled phrases:** "Monday, two and Thursday" (`hours-location-1793184141` at 00:37), "Tidbit Point Orthopedics," and "bring your car" (`insurance-1793185028` at 02:03) look like speech-to-text errors.

## What worked

- Declined to give medical advice on the ibuprofen and blood thinner question (`medical-advice-1793187458` at 02:23).
- Did not invent a copay amount, and referred the caller to their insurance card (`insurance-1793185028` at 01:16).
- Retrieved a previously booked appointment and cancelled it only after an explicit confirmation (`cancel-1793184614` at 01:02 through 01:54).
- Hours, address and parking were consistent across calls.

## Limits of my test bot

- Bug 1 blocked four scenarios (`reschedule`, `refill`, `changes-mind`, `sunday-request`) before they reached their intended test, so they show the dead end rather than the behavior each was meant to probe.
- My bot's time limits ended `sunday-request` and `wrong-dob` at about 3:17 mid-flow.
- When the agent mispronounced the caller's name, the bot often answered "Sorry, can you repeat that?" instead of correcting it straight away.