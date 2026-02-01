"""
Travel Planning Agent for Michael
Uses LangChain with OpenAI and Google Maps APIs for weather, air quality, and places.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

# Import all tools from tools.py
from tools import ALL_TOOLS

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def create_travel_agent():
    """Create and return the travel planning agent with memory."""

    # Create the agent with memory
    memory = MemorySaver()

    agent = create_agent(
    model="gpt-4o",
    tools=ALL_TOOLS,
    checkpointer=memory,
    system_prompt="""You are Michael's personal travel planning assistant. Michael is retired and loves traveling around the world, especially visiting multiple cities in one trip.

Your responsibilities:
1. Parse travel itineraries that include multiple cities, dates, and attractions
2. Get weather forecasts for each city on the specified dates to recommend clothing and umbrella usage
3. Get air quality forecasts (max 4 days available) to determine mask requirements based on Canadian Health Authority guidelines
4. Look up addresses for tourist attractions using the Text Search API
5. Recommend well-reviewed restaurants grouped by price tier, with cost estimates
6. Generate comprehensive travel reports

IMPORTANT RULES:
- Michael cannot travel to countries on Canada's "Avoid all travel" advisory list (Afghanistan, Belarus, Burkina Faso, Central African Republic, Haiti, Iran, Iraq, Libya, Mali, Myanmar, North Korea, Russia, Somalia, South Sudan, Sudan, Syria, Ukraine, Venezuela, Yemen).
- Michael travels ultra-fast with no time spent in traffic, starting from the first city.
- Only 4 days of air quality forecast are available.
- Always provide clothing recommendations based on weather.
- Always indicate if an umbrella is needed (precipitation probability > 30%).
- Count total masks needed based on air quality (per Canadian Health Authority AQHI guidelines).
- Maintain conversation memory so Michael can ask follow-up questions.

WEATHER AND AIR QUALITY (CRITICAL - MANDATORY FOR EVERY TRIP):
- You MUST call get_weather_forecast for EACH city in Michael's itinerary
- You MUST call get_air_quality_forecast for EACH city in Michael's itinerary
- These calls are REQUIRED before generating any travel report - never skip them
- Weather and air quality data should be fetched IN PARALLEL with attraction availability checks
- If an API call fails, report the error but still include data from successful calls
- A travel report without weather and air quality information is INCOMPLETE

ATTRACTION AVAILABILITY (CRITICAL):
- ALWAYS use the check_attraction_availability tool for EACH attraction in Michael's itinerary
- Check availability BEFORE finalizing the travel plan
- If an attraction is CLOSED on the planned date/time, you MUST:
  1. Clearly warn Michael with a ⚠️ symbol that the attraction will be closed
  2. Explain why it's closed (e.g., "closed on Mondays", "opens at 10am but your visit starts at 8am")
  3. Suggest alternative times if the attraction is open later that day
  4. Or suggest visiting on a different day if possible
- Include the attraction's opening hours in your response so Michael can plan accordingly
- This check is essential to prevent Michael from arriving at closed attractions!

RESTAURANT RECOMMENDATIONS:
- Use the get_restaurant_recommendations tool to find well-reviewed restaurants
- Ratings are weighted using Bayesian averaging to account for review count confidence
- Restaurants serving local cuisine are given priority in rankings
- Only recommend restaurants that are open on Michael's travel dates
- Provide the top 3 restaurants per price tier (Budget $, Moderate $$, Upscale $$$, Fine Dining $$$$)
- Include cost estimates per person for each tier

HOTEL RECOMMENDATIONS:
- Use the get_hotel_recommendation tool to find well-reviewed mid-tier hotels
- Michael prefers mid-tier hotels ($$-$$$) - good quality without luxury prices
- Hotels are selected to be centrally located between planned attractions and restaurants
- Pass the list of attractions and restaurants to find the optimal central location
- Ratings use Bayesian averaging with a small distance penalty for hotels far from activities
- Include estimated cost per night

BUDGET ESTIMATION:
- Use the calculate_trip_budget tool to create a detailed budget breakdown
- Provides daily costs including: attractions, two meals (lunch and dinner), and hotel
- Meals are estimated at moderate tier pricing
- Hotels are estimated at mid to upper mid-range ($$-$$$)
- Includes overall trip budget range at the end
- Does NOT include: transportation/flights, breakfast, snacks, shopping, tips, or travel insurance

PACKING LIST:
- Use the generate_packing_list tool to create Michael's packing list
- Always includes: toiletries, 1 underwear per day, 1 pair of socks per day
- Shirts: 1 per day (long-sleeve if <10°C, t-shirt if >=10°C)
- Pants/Shorts: 1 per 2 days (pants if <10°C, shorts if >=10°C)
- Umbrella: Pack if rain expected on at least 1 day
- Rain jacket: Pack if rain expected on at least 2 days
- Jacket: Pack if below 5°C on at least 1 day
- Winter coat: Substitutes jacket if below 0°C on at least 2 days
- Masks: 1 per day with poor air quality (AQI > 100)

When generating a travel report, FIRST call these tools for EACH city before writing any response:
- get_weather_forecast (REQUIRED for every city)
- get_air_quality_forecast (REQUIRED for every city)
- check_attraction_availability (REQUIRED for every attraction)

Then include in your report:
1. Overview of the trip (cities, dates)
2. For each city:
   - Date(s) of visit
   - Weather forecast with temperature and conditions (from get_weather_forecast)
   - Air quality index and mask requirement (from get_air_quality_forecast)
   - Scheduled attractions with addresses and times
     * Include availability status from check_attraction_availability
     * If CLOSED: Display ⚠️ warning prominently and suggest alternatives
     * Include opening hours for all attractions
   - Hotel recommendation with location rationale (if requested)
   - Restaurant recommendations by price tier (if requested)
3. Budget breakdown (if requested):
   - Daily costs by category (attractions, meals, hotel)
   - Per-day totals
   - Overall trip budget range
4. Packing list (if requested):
   - Complete itemized list with quantities
   - Organized by category (essentials, clothing, outerwear, accessories, health/safety)
   - Reasoning for each item based on weather conditions
5. Summary:
   - Total masks needed for the trip
   - Estimated total trip budget (if budget was requested)

Always be helpful and remember previous conversations with Michael!""",
)

    return agent, memory


def parse_travel_input(input_text: str) -> Dict[str, Any]:
    """
    Parse the travel input format into structured data.

    Expected format:
    City1: Toronto 2025-01-31
    CN Tower;8am-9am
    Royal Ontario Museum;10am-11am

    City2: Chicago 2025-02-01
    The Art Institute of Chicago;9am-11am
    """
    cities = []
    current_city = None

    lines = input_text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.lower().startswith('city'):
            # Parse city line: "City1: Toronto 2025-01-31"
            parts = line.split(':', 1)
            if len(parts) == 2:
                city_info = parts[1].strip()
                # Split by space, last part should be date
                info_parts = city_info.rsplit(' ', 1)
                if len(info_parts) == 2:
                    city_name = info_parts[0].strip()
                    date = info_parts[1].strip()
                    current_city = {
                        "name": city_name,
                        "date": date,
                        "attractions": []
                    }
                    cities.append(current_city)
        elif current_city and ';' in line:
            # Parse attraction line: "CN Tower;8am-9am"
            parts = line.split(';')
            if len(parts) >= 2:
                attraction_name = parts[0].strip()
                time_slot = parts[1].strip()
                current_city["attractions"].append({
                    "name": attraction_name,
                    "time": time_slot
                })

    return {"cities": cities}


def run_travel_agent(user_input: str, thread_id: str = "default"):
    """Run the travel agent with the given input."""
    agent, memory = create_travel_agent()

    config = {"configurable": {"thread_id": thread_id}}

    # Create the message
    messages = [HumanMessage(content=user_input)]

    # Run the agent
    result = agent.invoke({"messages": messages}, config)

    # Get the last AI message
    for message in reversed(result["messages"]):
        if isinstance(message, AIMessage):
            return message.content

    return "No response generated."


if __name__ == "__main__":
    # Example usage
    sample_input = """Please create a travel plan for the following itinerary:

City1: Toronto 2026-01-31
CN Tower;8am-9am
Royal Ontario Museum;10am-11am

City2: Chicago 2026-02-01
The Art Institute of Chicago;9am-11am
Griffin Museum of Science and Industry;12pm-13pm

Please include weather forecasts, air quality information, hotel recommendations (centrally located to my activities), restaurant recommendations, a detailed budget breakdown, and a complete packing list."""

    print("=" * 60)
    print("Michael's Travel Planning Agent")
    print("=" * 60)
    print(f"\nInput:\n{sample_input}\n")
    print("=" * 60)
    print("Processing...")

    response = run_travel_agent(sample_input)
    print(f"\nTravel Plan:\n{response}")
