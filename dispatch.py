import asyncio, json, sys, time
from dotenv import load_dotenv
from livekit import api

load_dotenv()
ASSESSMENT_NUMBER = "+18054398008"

async def main(scenario_id: str, phone: str):
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
    print("dispatched", call_id, "->", phone)

if __name__ == "__main__":
    # usage: python dispatch.py <scenario_id> [--self-test +92XXXXXXXXXX]
    phone = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--self-test" else ASSESSMENT_NUMBER
    asyncio.run(main(sys.argv[1], phone))