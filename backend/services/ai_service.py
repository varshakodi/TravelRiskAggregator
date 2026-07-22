"""
AI route briefing — hardened.

Trust boundary: this module receives ONLY server-derived facts. The API
layer recomputes the route itself and passes the result here; nothing a
client sends can reach the LLM prompt. (Previously the client posted the
route arrays back and we prompted with them verbatim — a prompt-injection
door: any curl user could put arbitrary instructions in "standard_route".)

Also hardened:
  - model name from env (OPENAI_MODEL), not hardcoded to a retired model
  - 10s timeout so a hung LLM call can't hang the endpoint
  - exceptions are logged server-side, never leaked into the UI
  - briefings TTL-cached 10 min per (route, verdict, zones) — identical
    state produces an identical briefing; don't pay for the same tokens twice
"""
import os

from openai import OpenAI

from services.cache import ttl_cache

# It will look for OPENAI_API_KEY in your environment. If not found, it uses a mock key.
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "mock_key"), timeout=10.0)
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def briefing_from_comparison(origin: str, dest: str, comparison: dict) -> str:
    """Build a briefing from a calculate_route_comparison() result (server-owned)."""
    # For REROUTED the safe path's crossings are empty by definition —
    # what blocked the corridor lives on the standard route.
    zones = (comparison["standard_route"]["zones_crossed"]
             if comparison["status"] == "REROUTED"
             else comparison["zones_crossed"])
    return _generate(
        origin,
        dest,
        comparison["status"],
        tuple(comparison["standard_route"]["path"]),
        tuple(comparison["safe_route"]["path"]),
        # descriptions only: human-readable for the prompt, hashable for the cache key
        tuple(z["description"] for z in zones),
    )


@ttl_cache(seconds=600)
def _generate(origin: str, dest: str, status: str,
              standard_route: tuple, safe_route: tuple, zones: tuple) -> str:
    zones_text = "; ".join(zones) if zones else "unspecified active airspace"

    if status == "CLEAR":
        prompt = (
            f"Write a 2-sentence safe travel briefing for a direct flight from {origin} "
            f"to {dest}. Mention clear skies and stable airspace."
        )
    elif status == "REROUTED":
        prompt = (
            f"Write a 3-sentence high-stakes security briefing for a flight from {origin} to {dest}. "
            f"The direct route ({' -> '.join(standard_route)}) is BLOCKED due to: {zones_text}. "
            f"The flight has been autonomously rerouted via ({' -> '.join(safe_route)}), which is clear. "
            f"Maintain a professional, military-intel tone."
        )
    else:  # NO_SAFE_PATH
        prompt = (
            f"Write a 3-sentence urgent briefing for a flight from {origin} to {dest}. "
            f"No fully clear route exists between these airports right now — every viable path crosses "
            f"active threat airspace. The lowest-risk option ({' -> '.join(safe_route)}) still crosses: "
            f"{zones_text}. Recommend proceeding only under heightened caution or holding for conditions "
            f"to change. Maintain a professional, military-intel tone."
        )

    # Deterministic offline fallback when no API key is configured.
    if client.api_key == "mock_key":
        if status == "CLEAR":
            return f"[SIMULATED AI]: Airspace between {origin} and {dest} is currently stable. No active NOTAMs or conflict zones detected on the direct vector."
        elif status == "REROUTED":
            return f"[SIMULATED AI]: Direct vector {origin}-{dest} intercepted active threat airspace ({zones_text}). Autonomous reroute authorized via {', '.join(safe_route)}. Threat exposure minimized; expect a slight increase in fuel burn and flight time."
        return f"[SIMULATED AI]: WARNING — no fully clear corridor exists between {origin} and {dest}. Lowest-risk option via {', '.join(safe_route)} still crosses active threat airspace ({zones_text}). Proceed only under heightened alert or hold for conditions to clear."

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a global aviation security analyst."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=150,
        )
        return response.choices[0].message.content
    except Exception as e:
        # Log the real error for the operator; never leak internals to the UI.
        print(f"[AI] Briefing generation failed: {e}")
        return "AI briefing temporarily unavailable — routing verdict above is authoritative."
