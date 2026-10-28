import asyncio, json, sys, time
from pathlib import Path
from dotenv import load_dotenv
from livekit import api

load_dotenv()
ASSESSMENT_NUMBER = "+18054398008"
COOLDOWN_SECONDS = 240
LOCK = Path(".last_dispatch")


async def send(scenario_id: str, phone: str):
    scenarios = json.load(open("scenarios.json", encoding="utf-8"))
    s = scenarios[scenario_id]
    call_id = f"{scenario_id}-{int(time.time())}"
    lk = api.LiveKitAPI()
    await lk.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
            agent_name="caller",
            room=call_id,
            metadata=json.dumps({"call_id": call_id, "phone_number": phone,
                                 "name": s["name"], "dob": s["dob"], "goal": s["goal"]}),
        )
    )
    await lk.aclose()
    LOCK.write_text(str(time.time()))
    print("dispatched", call_id, "->", phone)


def main():
    args = sys.argv[1:]
    scenarios = json.load(open("scenarios.json", encoding="utf-8"))
    if not args or args[0] == "--list":
        print("\n".join(scenarios))
        return
    if args[0] not in scenarios:
        print("unknown scenario. options:", ", ".join(scenarios))
        return
    phone = ASSESSMENT_NUMBER
    if "--self-test" in args:
        phone = args[args.index("--self-test") + 1]
    if LOCK.exists():
        age = time.time() - float(LOCK.read_text())
        if age < COOLDOWN_SECONDS:
            print(f"blocked: last dispatch was {int(age)}s ago. Wait {int(COOLDOWN_SECONDS - age)}s.")
            return
    asyncio.run(send(args[0], phone))


if __name__ == "__main__":
    main()