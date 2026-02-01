# Michael's Travel Planning Agent

A LangChain-powered travel planning agent with a Streamlit chat interface. This agent helps plan multi-city trips around the world with weather forecasts, air quality monitoring, and clothing recommendations.

## Features

- **Multi-City Trip Planning**: Plan trips across multiple cities with specific dates and attractions
- **Weather Forecasts**: Get detailed weather predictions with temperature and conditions
- **Clothing Recommendations**: Automatic suggestions based on weather conditions
- **Umbrella Alerts**: Know when to pack an umbrella based on precipitation probability
- **Air Quality Monitoring**: AQI forecasts with mask recommendations based on Canadian Health Authority guidelines
- **Tourist Attractions**: Look up attraction addresses using Google Places API
- **Conversation Memory**: Follow-up questions remember your travel context
- **Beautiful Chat UI**: User-friendly Streamlit interface

## Setup

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure API Keys

Create a `.env` file in the project root and add your API keys:
- `OPENAI_API_KEY`: Required - Get from https://platform.openai.com/api-keys
- `GOOGLE_MAPS_API_KEY`: Optional but recommended - Get from https://console.cloud.google.com/

For Google Maps API, enable these services:
- Geocoding API
- Places API (New)
- Air Quality API

### 3. Run the Application

**Option A: Streamlit Chat UI (Recommended)**
```bash
streamlit run app.py
```

**Option B: Command Line**
```bash
python travel_agent.py
```

## Usage

### Input Format

```
City1: [City Name] [Date YYYY-MM-DD]
[Attraction];[Time Range]
[Attraction];[Time Range]

City2: [City Name] [Date YYYY-MM-DD]
[Attraction];[Time Range]
```

### Example Input

```
City1: Toronto 2025-01-31
CN Tower;8am-9am
Royal Ontario Museum;10am-11am

City2: Chicago 2025-02-01
The Art Institute of Chicago;9am-11am
Griffin Museum of Science and Industry;12pm-13pm
```

## Tools Available

| Tool | Description |
|------|-------------|
| `get_weather_forecast` | Get weather forecast for a city with temperature and conditions |
| `get_air_quality_forecast` | Get AQI forecast (max 4 days) with mask recommendations |
| `get_tourist_attractions` | List popular tourist attractions in a city |
| `get_place_address` | Look up the address of a specific place |
| `calculate_total_masks` | Calculate total masks needed based on air quality |

## Air Quality & Mask Guidelines

Based on Canadian Health Authority (Health Canada) AQHI Guidelines:

| AQI Range | Risk Level | Mask Needed |
|-----------|------------|-------------|
| 0-50 | Good | No |
| 51-100 | Moderate | No (sensitive individuals may consider) |
| 101-150 | Unhealthy for Sensitive Groups | Yes |
| 151-200 | Unhealthy | Yes |
| 201-300 | Very Unhealthy | Yes (N95) |
| 301+ | Hazardous | Yes (N95, stay indoors) |

## Restrictions

- **Canada Travel Advisory**: Travel to countries on Canada's "Avoid all travel" list is not permitted (Afghanistan, Belarus, Burkina Faso, Central African Republic, Haiti, Iran, Iraq, Libya, Mali, Myanmar, North Korea, Russia, Somalia, South Sudan, Sudan, Syria, Ukraine, Venezuela, Yemen)
- **4-Day AQI Limit**: Air quality forecasts are limited to 4 days
- **Ultra-Fast Travel**: Assumes no transit time between locations

## Project Structure

```
LangchainProj1/
├── app.py              # Streamlit chat UI
├── travel_agent.py     # LangChain agent and tools
├── pyproject.toml      # Python dependencies (uv)
├── .env                # Environment variables (create this)
└── README.md           # This file
```

## Follow-up Questions

The agent maintains conversation memory, so you can ask follow-up questions like:

- "What clothes should I pack for the entire trip?"
- "Do I need an umbrella in Toronto?"
- "How many masks should I bring?"
- "Can you suggest more attractions in Chicago?"
- "What's the air quality like in my second city?"

## License

MIT License
