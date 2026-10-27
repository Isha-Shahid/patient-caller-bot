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
MAX_CALL_SECONDS = 240
Path("transcripts").mkdir(exist_ok=True)

PERSONA = """You are a real patient phoning a clinic. You are not an assistant.
Talk like a normal person on the phone: short, casual, a little hesitant. Often under 12 words.
Use plain fillers like 'um' or 'okay' only occasionally. No exclamation marks, no 'Thanks for that information',
no 'Have a great day', no 'How can I assist'. Say things like 'okay, thanks' or 'great, bye'.
Answer only what is asked, one thing at a time. Do not volunteer extra details until asked.
If you did not catch something, say 'sorry, can you repeat that?'.
Your name is {name}, date of birth {dob}.
Goal for this call: {goal}
Wait for the other side to speak first. Stay on the goal and push politely for a clear outcome.
Never accept a vague answer: if you are told something confusing or wrong, ask once to confirm it.
When the goal is done, or the call is going in circles, say a very short goodbye out loud first,
then call end_call in the next step."""


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    meta = json.loads(ctx.job.metadata)
    call_id = meta["call_id"]
    t0 = time.time()
    out = open(f"transcripts/{call_id}.txt", "w", encoding="utf-8")
    ctx.add_shutdown_callback(lambda: out.close())

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
        """Hang up the phone. Use after saying goodbye, when the goal is done or the call is stuck."""
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

    @session.on("user_input_transcribed")
    def _heard(ev):
        heard.set()

    @session.on("conversation_item_added")
    def _on_item(ev):
        text = getattr(ev.item, "text_content", None)
        if text:
            write("PATIENT_BOT" if ev.item.role == "assistant" else "CLINIC_AGENT", text)

    persona = PERSONA.format(name=meta["name"], dob=meta["dob"], goal=meta["goal"])
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
        await hang_up()
        return

    await started
    write("SYSTEM", "call answered")

    # If the other side stays silent after answering, say hello once.
    try:
        await asyncio.wait_for(heard.wait(), timeout=8)
    except asyncio.TimeoutError:
        session.generate_reply(instructions="The line is quiet. Say a short 'Hello?' once.")

    await asyncio.sleep(MAX_CALL_SECONDS)
    write("SYSTEM", "max duration reached, hanging up")
    await hang_up()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="caller"))