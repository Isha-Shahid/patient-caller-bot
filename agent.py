import asyncio, json, logging, os, time
from pathlib import Path
from dotenv import load_dotenv
from livekit import api
from livekit.agents import (Agent, AgentSession, JobContext, RunContext,
                            WorkerOptions, cli, function_tool)
from livekit.plugins import cartesia, deepgram, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv()
log = logging.getLogger("caller")

MIN_CALL_SECONDS = 60      # end_call refuses before this
WRAP_UP_SECONDS = 150      # start wrapping up
HARD_LIMIT_SECONDS = 185   # hang up regardless
CALLER_PHONE = os.getenv("CALLER_PHONE_SPOKEN", "eight six four, seven one three, three two seven one")
Path("transcripts").mkdir(exist_ok=True)
Path("failed_dials").mkdir(exist_ok=True)

PERSONA = """You are a real patient phoning a clinic. You are not an assistant.
Talk like a normal person on the phone: short, casual, a little hesitant. Usually under 15 words.
Use fillers like 'um' or 'okay' only occasionally. No exclamation marks, no 'Thanks for that information',
no 'Have a great day', no 'How can I assist'. Say things like 'okay, thanks' or 'great, bye'.
Answer only what is asked, one thing at a time. Ask only ONE question at a time, never a list of questions.
If you did not catch something, say 'sorry, can you repeat that?'.

Your details, to give ONLY when the other side asks for them:
- Name: {name}
- Date of birth: {dob}
- Phone number: {phone}
When the clinic asks for any of these, give it, then calmly return to your goal, for example 'okay, and about my question...'.

Goal for this call: {goal}

Keep a mental checklist of every part of your goal. Before you say goodbye, make sure each part was answered.
If something was skipped, ask for it once, naturally, for example 'sorry, what was the address again?'.
Wait for the other side to speak first. Stay on the goal and push politely for a clear outcome.
Never accept a vague answer: if you are told something confusing or wrong, ask once to confirm it.
Do not end the call early. If your goal is met quickly, ask one natural follow-up question
related to it (what to bring, how early to arrive, parking, cost) before you finish.
When you are finished, say 'okay, thanks, bye' in a few words out loud first, then call end_call in the next step."""


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    meta = json.loads(ctx.job.metadata)
    call_id = meta["call_id"]
    t0 = time.time()
    state = {"answered": None}
    transcript_path = Path("transcripts") / f"{call_id}.txt"
    out = open(transcript_path, "w", encoding="utf-8")

    async def _close_file():
        out.close()

    ctx.add_shutdown_callback(_close_file)

    def write(role, text):
        s = int(time.time() - t0)
        out.write(f"[{s//60:02d}:{s%60:02d}] {role}: {text}\n")
        out.flush()

    async def hang_up():
        try:
            await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))
        except Exception:
            pass

    @function_tool
    async def end_call(context: RunContext):
        """Hang up the phone. Only use after saying goodbye out loud, when the goal is done or the call is stuck."""
        answered = state["answered"]
        if answered and time.time() - answered < MIN_CALL_SECONDS:
            return "Too early to hang up. Ask one more natural follow-up question related to your goal first."
        await context.wait_for_playout()
        await hang_up()

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3", language="en-US"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=cartesia.TTS(),
        turn_detection=MultilingualModel(),
    )

    heard = asyncio.Event()
    closed = asyncio.Event()

    @session.on("user_input_transcribed")
    def _heard(ev):
        heard.set()

    @session.on("close")
    def _closed(ev):
        closed.set()

    @session.on("conversation_item_added")
    def _on_item(ev):
        text = getattr(ev.item, "text_content", None)
        if text:
            write("PATIENT_BOT" if ev.item.role == "assistant" else "CLINIC_AGENT", text)

    persona = PERSONA.format(name=meta["name"], dob=meta["dob"], goal=meta["goal"], phone=CALLER_PHONE)
    started = asyncio.create_task(
        session.start(agent=Agent(instructions=persona, tools=[end_call]), room=ctx.room)
    )
    try:
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=os.environ["SIP_OUTBOUND_TRUNK_ID"],
                sip_call_to=meta["phone_number"],
                participant_identity="callee",
                wait_until_answered=True,
            )
        )
    except Exception as e:
        log.error("dial failed: %s", e)
        write("SYSTEM", f"dial failed: {e}")
        out.close()
        try:
            os.replace(transcript_path, Path("failed_dials") / transcript_path.name)
        except Exception:
            pass
        await hang_up()
        return

    await started
    state["answered"] = time.time()
    write("SYSTEM", "call answered")

    # If the other side stays silent after answering, say hello once.
    try:
        await asyncio.wait_for(heard.wait(), timeout=8)
    except asyncio.TimeoutError:
        session.generate_reply(instructions="The line is quiet. Say a short 'Hello?' once.")

    # Let the call run; wrap up politely, then hard stop.
    try:
        await asyncio.wait_for(closed.wait(), timeout=WRAP_UP_SECONDS)
    except asyncio.TimeoutError:
        write("SYSTEM", "wrap-up time reached")
        try:
            handle = session.generate_reply(
                instructions="Time is nearly up. Say one short polite closing sentence and goodbye."
            )
            await handle.wait_for_playout()
        except Exception as e:
            log.warning("wrap-up failed: %s", e)
        try:
            await asyncio.wait_for(closed.wait(), timeout=HARD_LIMIT_SECONDS - WRAP_UP_SECONDS)
        except asyncio.TimeoutError:
            write("SYSTEM", "hard limit reached, hanging up")
    write("SYSTEM", "call ended")
    await hang_up()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="caller"))