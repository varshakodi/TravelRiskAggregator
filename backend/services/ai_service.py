import os
from openai import OpenAI

# It will look for OPENAI_API_KEY in your environment. If not found, it uses a mock key.
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "mock_key"))

def generate_threat_briefing(origin: str, dest: str, standard_route: list, safe_route: list, is_rerouted: bool):
    """
    Generates an executive AI briefing explaining the routing logic.
    """
    if not is_rerouted:
        prompt = f"Write a 2-sentence safe travel briefing for a direct flight from {origin} to {dest}. Mention clear skies and stable airspace."
    else:
        prompt = f"Write a 3-sentence high-stakes security briefing for a flight from {origin} to {dest}. The direct route ({' -> '.join(standard_route)}) is BLOCKED due to an active geopolitical conflict zone or severe weather. The flight has been autonomously rerouted via ({' -> '.join(safe_route)}). Maintain a professional, military-intel tone."

    # Fallback if you haven't set up your API key yet
    if client.api_key == "mock_key":
        if is_rerouted:
            return f"[SIMULATED AI]: Direct vector {origin}-{dest} intercepted active threat airspace. Autonomous reroute authorized via {', '.join(safe_route)}. Threat exposure minimized; expect a slight increase in fuel burn and flight time."
        return f"[SIMULATED AI]: Airspace between {origin} and {dest} is currently stable. No active NOTAMs or conflict zones detected on the direct vector."

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