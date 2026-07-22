import os
from openai import OpenAI

# It will look for OPENAI_API_KEY in your environment. If not found, it uses a mock key.
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "mock_key"))


def generate_threat_briefing(origin: str, dest: str, standard_route: list, safe_route: list,
                              status: str, zones_crossed: list):
    """
    Generates an executive AI briefing explaining the routing verdict.
    status is one of CLEAR / REROUTED / NO_SAFE_PATH (see pathfinder.calculate_route_comparison).
    """
    zones_text = "; ".join(zones_crossed) if zones_crossed else "unspecified active airspace"

    if status == "CLEAR":
        prompt = f"Write a 2-sentence safe travel briefing for a direct flight from {origin} to {dest}. Mention clear skies and stable airspace."
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

    # Fallback if you haven't set up your API key yet
    if client.api_key == "mock_key":
        if status == "CLEAR":
            return f"[SIMULATED AI]: Airspace between {origin} and {dest} is currently stable. No active NOTAMs or conflict zones detected on the direct vector."
        elif status == "REROUTED":
            return f"[SIMULATED AI]: Direct vector {origin}-{dest} intercepted active threat airspace ({zones_text}). Autonomous reroute authorized via {', '.join(safe_route)}. Threat exposure minimized; expect a slight increase in fuel burn and flight time."
        else:
            return f"[SIMULATED AI]: WARNING — no fully clear corridor exists between {origin} and {dest}. Lowest-risk option via {', '.join(safe_route)} still crosses active threat airspace ({zones_text}). Proceed only under heightened alert or hold for conditions to clear."

    # The Real AI Call
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a global aviation security analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Copilot offline: {str(e)}"
