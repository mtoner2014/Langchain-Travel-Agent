"""
Tools for the Travel Planning Agent
Contains all @tool decorated functions and their helper functions.
"""

import os
import json
import math
import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

from langchain_core.tools import tool
from pydantic import BaseModel, Field

load_dotenv()

# API Keys
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Canadian Health Authority Air Quality Guidelines for mask usage
# Based on AQHI (Air Quality Health Index) from Health Canada
# AQHI 1-3: Low risk - no mask needed
# AQHI 4-6: Moderate risk - sensitive individuals may need mask
# AQHI 7-10: High risk - mask recommended
# AQHI 10+: Very high risk - mask required
AIR_QUALITY_MASK_THRESHOLDS = {
    "good": {"aqi_max": 50, "mask_needed": False, "description": "Air quality is good. No mask needed."},
    "moderate": {"aqi_max": 100, "mask_needed": False, "description": "Air quality is moderate. Sensitive individuals may consider a mask."},
    "unhealthy_sensitive": {"aqi_max": 150, "mask_needed": True, "description": "Unhealthy for sensitive groups. Mask recommended."},
    "unhealthy": {"aqi_max": 200, "mask_needed": True, "description": "Unhealthy. Mask required."},
    "very_unhealthy": {"aqi_max": 300, "mask_needed": True, "description": "Very unhealthy. N95 mask required."},
    "hazardous": {"aqi_max": 500, "mask_needed": True, "description": "Hazardous. Stay indoors or use N95 mask."},
}

# Restricted countries per Canadian Government's Travel Advisories (Avoid all travel)
# Source: https://travel.gc.ca/travelling/advisories
RESTRICTED_COUNTRIES = [
    # Afghanistan
    "Afghanistan",
    # Belarus
    "Belarus",
    # Burkina Faso
    "Burkina Faso",
    # Central African Republic
    "Central African Republic", "CAR",
    # Haiti
    "Haiti",
    # Iran
    "Iran",
    # Iraq
    "Iraq",
    # Libya
    "Libya",
    # Mali
    "Mali",
    # Myanmar (Burma)
    "Myanmar", "Burma",
    # North Korea
    "North Korea", "DPRK", "Democratic People's Republic of Korea",
    # Russia
    "Russia", "Russian Federation",
    # Somalia
    "Somalia",
    # South Sudan
    "South Sudan",
    # Sudan
    "Sudan",
    # Syria
    "Syria",
    # Ukraine
    "Ukraine",
    # Venezuela
    "Venezuela",
    # Yemen
    "Yemen",
]

# Local cuisine mapping for North American cities
# Used to boost restaurants that exemplify local food culture
LOCAL_CUISINE_MAPPING = {
    "toronto": ["canadian", "poutine", "peameal bacon", "multicultural", "chinese", "italian", "portuguese"],
    "montreal": ["french", "quebecois", "poutine", "smoked meat", "bagels", "french canadian"],
    "vancouver": ["asian fusion", "sushi", "seafood", "chinese", "japanese", "pacific northwest"],
    "chicago": ["deep dish pizza", "chicago style", "hot dog", "italian beef", "steakhouse", "american"],
    "new york": ["pizza", "bagels", "deli", "jewish deli", "italian", "diverse", "american"],
    "los angeles": ["mexican", "tacos", "korean", "fusion", "california cuisine", "american"],
    "san francisco": ["seafood", "sourdough", "chinese", "california cuisine", "farm to table", "asian fusion"],
    "new orleans": ["cajun", "creole", "southern", "seafood", "gumbo", "po boy", "louisiana"],
    "miami": ["cuban", "latin", "caribbean", "seafood", "colombian", "peruvian"],
    "boston": ["seafood", "new england", "clam chowder", "lobster", "irish", "american"],
    "philadelphia": ["cheesesteak", "hoagies", "american", "italian", "pretzels"],
    "austin": ["barbecue", "tex-mex", "mexican", "southern", "american"],
    "seattle": ["seafood", "pacific northwest", "coffee", "asian fusion", "vietnamese"],
    "denver": ["rocky mountain", "steakhouse", "american", "craft", "mexican"],
    "nashville": ["hot chicken", "southern", "barbecue", "american", "soul food"],
    "portland": ["pacific northwest", "farm to table", "food truck", "asian", "american"],
    "san diego": ["mexican", "seafood", "california cuisine", "tacos", "american"],
    "las vegas": ["buffet", "steakhouse", "american", "diverse", "international"],
    "atlanta": ["southern", "soul food", "barbecue", "american", "international"],
    "washington": ["international", "american", "ethiopian", "vietnamese", "diverse"],
    "mexico city": ["mexican", "tacos", "mole", "street food", "traditional mexican"],
    "cancun": ["mexican", "seafood", "yucatecan", "caribbean", "mayan"],
}

# Price tier descriptions for cost estimation
PRICE_TIER_INFO = {
    1: {"label": "Budget", "symbol": "$", "estimate_per_person": "$10-20 USD"},
    2: {"label": "Moderate", "symbol": "$$", "estimate_per_person": "$20-40 USD"},
    3: {"label": "Upscale", "symbol": "$$$", "estimate_per_person": "$40-80 USD"},
    4: {"label": "Fine Dining", "symbol": "$$$$", "estimate_per_person": "$80+ USD"},
}

# Hotel price tier info (Michael prefers mid-tier: levels 2-3)
HOTEL_PRICE_TIER_INFO = {
    1: {"label": "Budget", "symbol": "$", "estimate_per_night": "$50-100 USD", "min": 50, "max": 100},
    2: {"label": "Mid-Range", "symbol": "$$", "estimate_per_night": "$100-200 USD", "min": 100, "max": 200},
    3: {"label": "Upper Mid-Range", "symbol": "$$$", "estimate_per_night": "$200-350 USD", "min": 200, "max": 350},
    4: {"label": "Luxury", "symbol": "$$$$", "estimate_per_night": "$350+ USD", "min": 350, "max": 500},
}

# Attraction cost estimates by type
ATTRACTION_COST_ESTIMATES = {
    # Museums and cultural
    "museum": {"min": 15, "max": 30, "avg": 22},
    "art_gallery": {"min": 15, "max": 25, "avg": 20},
    "science_museum": {"min": 20, "max": 35, "avg": 27},
    "aquarium": {"min": 30, "max": 45, "avg": 37},
    "zoo": {"min": 20, "max": 35, "avg": 27},
    # Landmarks and towers
    "observation_deck": {"min": 25, "max": 45, "avg": 35},
    "tower": {"min": 25, "max": 45, "avg": 35},
    "landmark": {"min": 0, "max": 20, "avg": 10},
    # Parks and outdoor
    "park": {"min": 0, "max": 5, "avg": 0},
    "garden": {"min": 10, "max": 20, "avg": 15},
    "beach": {"min": 0, "max": 5, "avg": 0},
    "national_park": {"min": 15, "max": 35, "avg": 25},
    # Entertainment
    "theme_park": {"min": 80, "max": 150, "avg": 115},
    "theater": {"min": 50, "max": 150, "avg": 100},
    "concert_hall": {"min": 40, "max": 120, "avg": 80},
    "sports_venue": {"min": 30, "max": 200, "avg": 75},
    # Historical
    "historic_site": {"min": 10, "max": 25, "avg": 17},
    "castle": {"min": 15, "max": 30, "avg": 22},
    "monument": {"min": 0, "max": 10, "avg": 5},
    # Default
    "default": {"min": 15, "max": 30, "avg": 22},
}

# Known attraction costs for accuracy
KNOWN_ATTRACTION_COSTS = {
    # Toronto
    "cn tower": {"min": 40, "max": 55, "name": "CN Tower"},
    "royal ontario museum": {"min": 20, "max": 26, "name": "Royal Ontario Museum"},
    "ripley's aquarium": {"min": 40, "max": 50, "name": "Ripley's Aquarium of Canada"},
    "art gallery of ontario": {"min": 22, "max": 30, "name": "Art Gallery of Ontario"},
    "casa loma": {"min": 30, "max": 40, "name": "Casa Loma"},
    # Chicago
    "art institute of chicago": {"min": 25, "max": 35, "name": "The Art Institute of Chicago"},
    "the art institute of chicago": {"min": 25, "max": 35, "name": "The Art Institute of Chicago"},
    "willis tower": {"min": 25, "max": 35, "name": "Willis Tower Skydeck"},
    "skydeck chicago": {"min": 25, "max": 35, "name": "Skydeck Chicago"},
    "field museum": {"min": 26, "max": 38, "name": "Field Museum"},
    "shedd aquarium": {"min": 35, "max": 45, "name": "Shedd Aquarium"},
    "museum of science and industry": {"min": 22, "max": 30, "name": "Museum of Science and Industry"},
    "griffin museum of science and industry": {"min": 22, "max": 30, "name": "Griffin Museum of Science and Industry"},
    "millennium park": {"min": 0, "max": 0, "name": "Millennium Park"},
    "navy pier": {"min": 0, "max": 20, "name": "Navy Pier"},
    # New York
    "statue of liberty": {"min": 24, "max": 75, "name": "Statue of Liberty"},
    "empire state building": {"min": 44, "max": 80, "name": "Empire State Building"},
    "metropolitan museum of art": {"min": 25, "max": 30, "name": "Metropolitan Museum of Art"},
    "met": {"min": 25, "max": 30, "name": "Metropolitan Museum of Art"},
    "central park": {"min": 0, "max": 0, "name": "Central Park"},
    "times square": {"min": 0, "max": 0, "name": "Times Square"},
    "one world observatory": {"min": 40, "max": 60, "name": "One World Observatory"},
    "moma": {"min": 25, "max": 30, "name": "Museum of Modern Art"},
    "museum of modern art": {"min": 25, "max": 30, "name": "Museum of Modern Art"},
    # Miami
    "south beach": {"min": 0, "max": 0, "name": "South Beach"},
    "vizcaya museum": {"min": 22, "max": 28, "name": "Vizcaya Museum and Gardens"},
    "wynwood walls": {"min": 0, "max": 12, "name": "Wynwood Walls"},
    "pérez art museum miami": {"min": 16, "max": 20, "name": "Pérez Art Museum Miami"},
    "perez art museum": {"min": 16, "max": 20, "name": "Pérez Art Museum Miami"},
    "everglades national park": {"min": 15, "max": 30, "name": "Everglades National Park"},
}

# Meal cost estimates (per person)
MEAL_COST_ESTIMATES = {
    "lunch": {
        "budget": {"min": 12, "max": 20, "label": "Budget lunch"},
        "moderate": {"min": 20, "max": 35, "label": "Moderate lunch"},
        "upscale": {"min": 35, "max": 55, "label": "Upscale lunch"},
    },
    "dinner": {
        "budget": {"min": 15, "max": 25, "label": "Budget dinner"},
        "moderate": {"min": 30, "max": 50, "label": "Moderate dinner"},
        "upscale": {"min": 50, "max": 80, "label": "Upscale dinner"},
    }
}


class TouristAttraction(BaseModel):
    """A tourist attraction with name and address."""
    name: str = Field(description="Name of the tourist attraction")
    address: str = Field(description="Full geographical address")
    rating: Optional[float] = Field(default=None, description="Rating if available")


class TouristAttractionsList(BaseModel):
    """List of tourist attractions in a city."""
    city: str = Field(description="City name")
    attractions: List[TouristAttraction] = Field(description="List of tourist attractions")


def check_location_allowed(city: str) -> bool:
    """Check if the location is not on Canada's travel advisory restricted list."""
    for restricted in RESTRICTED_COUNTRIES:
        if restricted.lower() in city.lower():
            return False
    return True


def get_coordinates(place_name: str) -> Optional[Dict[str, float]]:
    """Get coordinates for a place using Google Geocoding API."""
    if not GOOGLE_MAPS_API_KEY:
        return {"lat": 43.6532, "lng": -79.3832}  # Default to Toronto for demo

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": place_name,
        "key": GOOGLE_MAPS_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if data.get("status") == "OK" and data.get("results"):
            location = data["results"][0]["geometry"]["location"]
            return {"lat": location["lat"], "lng": location["lng"]}
    except Exception as e:
        print(f"Geocoding error: {e}")

    return None


def is_past_date(date_str: str) -> bool:
    """
    Check if a date is in the past.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        True if the date is before today, False otherwise
    """
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    return target_date < today


def validate_date_range(date_str: str) -> tuple[bool, str]:
    """
    Validate that a date is within acceptable range:
    - Not more than 24 hours in the past
    - Not more than 7 days in the future

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return False, f"Invalid date format: '{date_str}'. Please use YYYY-MM-DD format."

    now = datetime.now()

    # Check if more than 24 hours in the past
    past_limit = now - timedelta(hours=24)
    if target_date < past_limit:
        return False, f"Date '{date_str}' is more than 24 hours in the past. Please provide a more recent date."

    # Check if more than 10 days in the future
    future_limit = now + timedelta(days=10)
    if target_date > future_limit:
        max_date = future_limit.strftime("%Y-%m-%d")
        return False, f"Date '{date_str}' is more than 10 days in the future. Please provide a date on or before {max_date}."

    return True, ""


def calculate_bayesian_rating(rating: float, num_reviews: int, prior_mean: float = 3.5, prior_weight: int = 10) -> float:
    """
    Calculate Bayesian weighted rating to account for review count uncertainty.

    Uses the IMDB formula (Bayesian average):
    weighted_rating = (v * R + m * C) / (v + m)

    Where:
    - v = number of votes/reviews for this restaurant
    - R = average rating of this restaurant
    - m = minimum reviews needed for statistical confidence (prior weight)
    - C = mean rating across all restaurants (prior mean)

    This ensures restaurants with few reviews are pulled toward the average,
    while restaurants with many reviews reflect their true rating.

    Args:
        rating: The restaurant's average rating (1-5 scale)
        num_reviews: Number of reviews the restaurant has
        prior_mean: The assumed average rating for all restaurants (default 3.5)
        prior_weight: How many reviews needed before we trust the rating (default 10)

    Returns:
        Bayesian weighted rating
    """
    if num_reviews == 0:
        return prior_mean

    weighted = (num_reviews * rating + prior_weight * prior_mean) / (num_reviews + prior_weight)
    return round(weighted, 2)


def check_restaurant_open_on_date(opening_hours: Dict[str, Any], target_date: str) -> bool:
    """
    Check if a restaurant is open on a specific date.

    Args:
        opening_hours: Opening hours data from Google Places API
        target_date: Date string in YYYY-MM-DD format

    Returns:
        True if restaurant is open, False otherwise
    """
    if not opening_hours:
        # If no hours data, assume open (conservative approach)
        return True

    try:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        day_of_week = target_dt.weekday()  # Monday=0, Sunday=6

        # Check weekday_text or periods
        weekday_text = opening_hours.get("weekdayDescriptions", [])

        if weekday_text:
            # Days in Google's format are 0=Sunday, 1=Monday, etc.
            # We need to convert Python's weekday (Monday=0) to match
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            target_day_name = day_names[day_of_week]

            for day_text in weekday_text:
                if target_day_name.lower() in day_text.lower():
                    if "closed" in day_text.lower():
                        return False
                    return True

        # Check periods if available
        periods = opening_hours.get("periods", [])
        if periods:
            # Google uses 0=Sunday, we use Monday=0
            google_day = (day_of_week + 1) % 7
            for period in periods:
                if period.get("open", {}).get("day") == google_day:
                    return True
            return False

        # Default to open if we can't determine
        return True

    except Exception:
        return True


def parse_time_string(time_str: str) -> Optional[int]:
    """
    Parse a time string like "8am", "9:30am", "14:00", "2pm" to minutes since midnight.

    Args:
        time_str: Time string in various formats

    Returns:
        Minutes since midnight, or None if parsing fails
    """
    time_str = time_str.lower().strip()

    try:
        # Handle formats like "8am", "9pm", "10:30am"
        if 'am' in time_str or 'pm' in time_str:
            is_pm = 'pm' in time_str
            time_str = time_str.replace('am', '').replace('pm', '').strip()

            if ':' in time_str:
                parts = time_str.split(':')
                hours = int(parts[0])
                minutes = int(parts[1]) if len(parts) > 1 else 0
            else:
                hours = int(time_str)
                minutes = 0

            if is_pm and hours != 12:
                hours += 12
            elif not is_pm and hours == 12:
                hours = 0

            return hours * 60 + minutes

        # Handle 24-hour format like "14:00", "09:30"
        elif ':' in time_str:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            return hours * 60 + minutes

        # Handle plain numbers (assume hours)
        else:
            hours = int(time_str)
            return hours * 60

    except (ValueError, IndexError):
        return None


def check_attraction_open_at_time(opening_hours: Dict[str, Any], target_date: str, time_range: str) -> Dict[str, Any]:
    """
    Check if an attraction is open on a specific date and time.

    Args:
        opening_hours: Opening hours data from Google Places API
        target_date: Date string in YYYY-MM-DD format
        time_range: Time range like "8am-9am" or "10:00-12:00"

    Returns:
        Dict with 'is_open', 'reason', and 'hours' keys
    """
    result = {
        "is_open": True,
        "reason": "Opening hours not available - assuming open",
        "hours_on_date": "Unknown"
    }

    if not opening_hours:
        return result

    try:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        day_of_week = target_dt.weekday()  # Monday=0, Sunday=6
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        target_day_name = day_names[day_of_week]

        # Parse the user's planned visit time range
        visit_start = None
        visit_end = None
        if time_range and '-' in time_range:
            time_parts = time_range.split('-')
            visit_start = parse_time_string(time_parts[0])
            visit_end = parse_time_string(time_parts[1])

        # Check weekday_text first (e.g., "Monday: 9:00 AM – 5:00 PM")
        weekday_text = opening_hours.get("weekdayDescriptions", [])

        if weekday_text:
            for day_text in weekday_text:
                if target_day_name.lower() in day_text.lower():
                    result["hours_on_date"] = day_text

                    # Check if explicitly closed
                    if "closed" in day_text.lower():
                        result["is_open"] = False
                        result["reason"] = f"Attraction is closed on {target_day_name}s"
                        return result

                    # Try to parse opening hours from text to check time overlap
                    # Format is usually "Monday: 9:00 AM – 5:00 PM"
                    if ':' in day_text and ('am' in day_text.lower() or 'pm' in day_text.lower()):
                        try:
                            # Extract hours portion after the day name
                            hours_portion = day_text.split(':', 1)[1].strip() if ':' in day_text else day_text

                            # Handle "9:00 AM – 5:00 PM" or similar
                            if '–' in hours_portion or '-' in hours_portion:
                                separator = '–' if '–' in hours_portion else '-'
                                open_close = hours_portion.split(separator)
                                if len(open_close) == 2:
                                    open_time = parse_time_string(open_close[0].strip())
                                    close_time = parse_time_string(open_close[1].strip())

                                    if open_time is not None and close_time is not None:
                                        # Check if user's visit time overlaps with opening hours
                                        if visit_start is not None and visit_end is not None:
                                            if visit_start < open_time:
                                                result["is_open"] = False
                                                open_formatted = f"{open_time // 60}:{open_time % 60:02d}"
                                                result["reason"] = f"Attraction opens at {open_formatted}, but your visit starts earlier at {time_range.split('-')[0]}"
                                                return result
                                            if visit_end > close_time:
                                                result["is_open"] = False
                                                close_formatted = f"{close_time // 60}:{close_time % 60:02d}"
                                                result["reason"] = f"Attraction closes at {close_formatted}, but your visit extends until {time_range.split('-')[1]}"
                                                return result
                        except Exception:
                            pass  # If parsing fails, continue with default assumption

                    result["is_open"] = True
                    result["reason"] = f"Open on {target_day_name}"
                    return result

        # Check periods if available
        periods = opening_hours.get("periods", [])
        if periods:
            # Google uses 0=Sunday, we use Monday=0
            google_day = (day_of_week + 1) % 7

            day_found = False
            for period in periods:
                if period.get("open", {}).get("day") == google_day:
                    day_found = True
                    open_hour = period.get("open", {}).get("hour", 0)
                    open_minute = period.get("open", {}).get("minute", 0)
                    close_hour = period.get("close", {}).get("hour", 23)
                    close_minute = period.get("close", {}).get("minute", 59)

                    open_time = open_hour * 60 + open_minute
                    close_time = close_hour * 60 + close_minute

                    result["hours_on_date"] = f"{open_hour}:{open_minute:02d} - {close_hour}:{close_minute:02d}"

                    if visit_start is not None and visit_end is not None:
                        if visit_start < open_time:
                            result["is_open"] = False
                            result["reason"] = f"Attraction opens at {open_hour}:{open_minute:02d}, but your visit starts earlier"
                            return result
                        if visit_end > close_time:
                            result["is_open"] = False
                            result["reason"] = f"Attraction closes at {close_hour}:{close_minute:02d}, but your visit extends past closing"
                            return result

                    result["is_open"] = True
                    result["reason"] = f"Open on {target_day_name}"
                    return result

            if not day_found:
                result["is_open"] = False
                result["reason"] = f"Attraction appears to be closed on {target_day_name}s"
                return result

        return result

    except Exception as e:
        result["reason"] = f"Could not verify hours: {str(e)}"
        return result


def get_local_cuisine_boost(restaurant_types: List[str], city: str) -> float:
    """
    Calculate a score boost for restaurants serving local cuisine.

    Args:
        restaurant_types: List of cuisine/restaurant types from the API
        city: The city being searched

    Returns:
        Boost value (0.0 to 0.5) to add to the weighted rating
    """
    city_lower = city.lower()

    # Find matching local cuisines
    local_cuisines = []
    for known_city, cuisines in LOCAL_CUISINE_MAPPING.items():
        if known_city in city_lower or city_lower in known_city:
            local_cuisines = cuisines
            break

    if not local_cuisines:
        return 0.0

    # Check for matches
    types_lower = [t.lower().replace("_", " ") for t in restaurant_types]
    types_text = " ".join(types_lower)

    match_count = 0
    for cuisine in local_cuisines:
        if cuisine.lower() in types_text:
            match_count += 1

    # Return boost: 0.25 for one match, 0.5 for multiple matches
    if match_count >= 2:
        return 0.5
    elif match_count == 1:
        return 0.25
    return 0.0


def calculate_centroid(locations: List[Dict[str, float]]) -> Dict[str, float]:
    """
    Calculate the geographic centroid (center point) of multiple locations.

    Uses simple arithmetic mean for latitude/longitude which is accurate
    for locations within a city (small geographic area).

    Args:
        locations: List of dicts with 'lat' and 'lng' keys

    Returns:
        Dict with 'lat' and 'lng' of the centroid
    """
    if not locations:
        return None

    avg_lat = sum(loc["lat"] for loc in locations) / len(locations)
    avg_lng = sum(loc["lng"] for loc in locations) / len(locations)

    return {"lat": round(avg_lat, 6), "lng": round(avg_lng, 6)}


def get_place_coordinates(place_name: str, city: str) -> Optional[Dict[str, float]]:
    """
    Get coordinates for a specific place within a city.

    Args:
        place_name: Name of the place (e.g., "CN Tower")
        city: City context (e.g., "Toronto")

    Returns:
        Dict with 'lat' and 'lng' or None if not found
    """
    if GOOGLE_MAPS_API_KEY:
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
            "X-Goog-FieldMask": "places.location"
        }

        body = {
            "textQuery": f"{place_name} in {city}",
            "maxResultCount": 1
        }

        try:
            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if "places" in data and data["places"]:
                location = data["places"][0].get("location", {})
                if location:
                    return {
                        "lat": location.get("latitude"),
                        "lng": location.get("longitude")
                    }
        except Exception as e:
            print(f"Error getting place coordinates: {e}")

    # Return city center as fallback
    return get_coordinates(city)


def calculate_distance_km(coord1: Dict[str, float], coord2: Dict[str, float]) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.

    Args:
        coord1: First coordinate with 'lat' and 'lng'
        coord2: Second coordinate with 'lat' and 'lng'

    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers

    lat1 = math.radians(coord1["lat"])
    lat2 = math.radians(coord2["lat"])
    delta_lat = math.radians(coord2["lat"] - coord1["lat"])
    delta_lng = math.radians(coord2["lng"] - coord1["lng"])

    a = math.sin(delta_lat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def estimate_attraction_cost(attraction_name: str) -> Dict[str, Any]:
    """
    Estimate the cost of visiting an attraction.

    Args:
        attraction_name: Name of the attraction

    Returns:
        Dict with min, max costs and attraction details
    """
    attraction_lower = attraction_name.lower()

    # Check known attractions first
    for known_name, costs in KNOWN_ATTRACTION_COSTS.items():
        if known_name in attraction_lower or attraction_lower in known_name:
            return {
                "name": costs.get("name", attraction_name),
                "min": costs["min"],
                "max": costs["max"],
                "source": "known_attraction"
            }

    # Estimate based on type keywords
    type_keywords = {
        "museum": ["museum"],
        "art_gallery": ["art gallery", "gallery of art"],
        "science_museum": ["science", "discovery"],
        "aquarium": ["aquarium", "sea life"],
        "zoo": ["zoo", "wildlife"],
        "observation_deck": ["observation", "skydeck", "observatory"],
        "tower": ["tower"],
        "park": ["park", "gardens", "garden"],
        "beach": ["beach"],
        "national_park": ["national park"],
        "theme_park": ["theme park", "amusement", "disney", "universal"],
        "theater": ["theater", "theatre", "broadway"],
        "historic_site": ["historic", "heritage", "memorial"],
        "monument": ["monument", "statue"],
    }

    for attraction_type, keywords in type_keywords.items():
        for keyword in keywords:
            if keyword in attraction_lower:
                costs = ATTRACTION_COST_ESTIMATES[attraction_type]
                return {
                    "name": attraction_name,
                    "min": costs["min"],
                    "max": costs["max"],
                    "source": f"estimated_{attraction_type}"
                }

    # Default estimate
    default = ATTRACTION_COST_ESTIMATES["default"]
    return {
        "name": attraction_name,
        "min": default["min"],
        "max": default["max"],
        "source": "default_estimate"
    }


def get_weather_data_for_packing(city: str, date: str) -> Dict[str, Any]:
    """
    Get weather data for a specific city and date for packing decisions.
    Uses Google Weather API with automatic history/forecast routing.

    Returns temperature and precipitation info.
    """
    coords = get_coordinates(city)
    if not coords:
        return {"error": f"Could not find coordinates for {city}"}

    if not GOOGLE_MAPS_API_KEY:
        return {
            "city": city,
            "date": date,
            "error": "Google Maps API key not configured",
            "temp_max": 10,
            "temp_min": 5,
            "avg_temp": 7.5,
            "precipitation_probability": 30,
            "will_rain": False
        }

    # Determine if we need history or forecast endpoint
    use_history = is_past_date(date)
    endpoint = "history/days:lookup" if use_history else "forecast/days:lookup"

    # Build URL with query parameters
    url = f"https://weather.googleapis.com/v1/{endpoint}?key={GOOGLE_MAPS_API_KEY}&location.latitude={coords['lat']}&location.longitude={coords['lng']}"

    try:
        response = requests.get(url)
        data = response.json()

        # Parse the response - structure may vary between history and forecast
        if "forecastDays" in data or "historyDays" in data:
            days_data = data.get("forecastDays", data.get("historyDays", []))
            if days_data:
                day_data = days_data[0]
                day_info = day_data.get("daytimeForecast", day_data.get("daytimeConditions", {}))
                night_info = day_data.get("nighttimeForecast", day_data.get("nighttimeConditions", {}))

                # Temperatures are at day level, not inside daytime/nighttime
                temp_max = day_data.get("maxTemperature", {}).get("degrees", 10)
                temp_min = day_data.get("minTemperature", {}).get("degrees", 5)
                # Precipitation is nested under precipitation.probability.percent
                precip_prob = day_info.get("precipitation", {}).get("probability", {}).get("percent", 0)
                avg_temp = (temp_max + temp_min) / 2

                return {
                    "city": city,
                    "date": date,
                    "temp_max": temp_max,
                    "temp_min": temp_min,
                    "avg_temp": avg_temp,
                    "precipitation_probability": precip_prob,
                    "will_rain": precip_prob > 30,
                    "source": "Google Weather API (history)" if use_history else "Google Weather API (forecast)"
                }

        # Check for error in response
        if "error" in data:
            print(f"Google Weather API error: {data['error']}")

    except Exception as e:
        print(f"Weather API error: {e}")

    # Return error with defaults if API fails
    return {
        "city": city,
        "date": date,
        "temp_max": 10,
        "temp_min": 5,
        "avg_temp": 7.5,
        "precipitation_probability": 30,
        "will_rain": False,
        "error": "Could not retrieve weather data from Google API"
    }


def get_air_quality_for_packing(city: str, date: str) -> Dict[str, Any]:
    """
    Get air quality data for a specific city and date for mask packing decisions.
    Uses Google Air Quality API with automatic history/forecast routing.

    Returns AQI and whether a mask is needed.
    """
    coords = get_coordinates(city)
    if not coords:
        return {"error": f"Could not find coordinates for {city}", "mask_needed": False}

    if not GOOGLE_MAPS_API_KEY:
        return {
            "city": city,
            "date": date,
            "avg_aqi": 50,
            "mask_needed": False,
            "error": "Google Maps API key not configured"
        }

    # Determine if we need history or forecast endpoint
    use_history = is_past_date(date)
    endpoint = "history:lookup" if use_history else "forecast:lookup"
    url = f"https://airquality.googleapis.com/v1/{endpoint}"

    headers = {"Content-Type": "application/json"}

    body = {
        "location": {
            "latitude": coords["lat"],
            "longitude": coords["lng"]
        }
    }

    if use_history:
        # For history endpoint
        body["period"] = {
            "startTime": f"{date}T00:00:00Z",
            "endTime": f"{date}T23:59:59Z"
        }
    else:
        # For forecast endpoint - use dateTime instead of period
        body["dateTime"] = f"{date}T12:00:00Z"
        body["pageSize"] = 24

    try:
        response = requests.post(
            f"{url}?key={GOOGLE_MAPS_API_KEY}",
            headers=headers,
            json=body
        )
        data = response.json()

        # Parse response - look for hourly data to calculate daily average
        hourly_data = data.get("hourlyForecasts", data.get("hoursInfo", []))
        if hourly_data:
            aqis = []
            for hour in hourly_data:
                indexes = hour.get("indexes", [])
                if indexes:
                    aqi = indexes[0].get("aqi", indexes[0].get("aqiDisplay"))
                    if aqi is not None:
                        aqis.append(int(aqi) if isinstance(aqi, str) else aqi)

            avg_aqi = sum(aqis) / len(aqis) if aqis else 50
            mask_needed = avg_aqi > 100

            return {
                "city": city,
                "date": date,
                "avg_aqi": round(avg_aqi),
                "mask_needed": mask_needed,
                "source": "Google Air Quality API (history)" if use_history else "Google Air Quality API (forecast)"
            }

        # Check for error in response
        if "error" in data:
            print(f"Google Air Quality API error: {data['error']}")

    except Exception as e:
        print(f"Air quality API error: {e}")

    # Return error with defaults if API fails
    return {
        "city": city,
        "date": date,
        "avg_aqi": 50,
        "mask_needed": False,
        "error": "Could not retrieve air quality data from Google API"
    }


# =============================================================================
# TOOL FUNCTIONS
# =============================================================================

@tool
def get_weather_forecast(city: str, date: str, num_days: int = 1) -> str:
    """
    Get weather forecast or historical weather for a city for specified number of days.
    Uses Google Weather API with automatic history/forecast routing based on date.

    Args:
        city: Name of the city (e.g., "Toronto, Canada")
        date: Start date in YYYY-MM-DD format
        num_days: Number of days to retrieve (1-7)

    Returns:
        Weather data including temperature, conditions, and clothing recommendations.
    """
    print(f"[DEBUG] get_weather_forecast called with: city={city}, date={date}, num_days={num_days}", flush=True)

    # Validate date range
    is_valid, error_msg = validate_date_range(date)
    if not is_valid:
        return f"Error: {error_msg}"

    if not check_location_allowed(city):
        print(f"[DEBUG] Location not allowed: {city}", flush=True)
        return f"Error: Travel to {city} is not allowed. This destination is on Canada's travel advisory restricted list."

    coords = get_coordinates(city)
    if not coords:
        print(f"[DEBUG] Could not get coordinates for: {city}", flush=True)
        return f"Error: Could not find coordinates for {city}"

    if not GOOGLE_MAPS_API_KEY:
        print("[DEBUG] GOOGLE_MAPS_API_KEY not set", flush=True)
        return f"Error: Google Maps API key not configured. Please set GOOGLE_MAPS_API_KEY."

    # Determine if we need history or forecast endpoint
    use_history = is_past_date(date)
    endpoint = "history/days:lookup" if use_history else "forecast/days:lookup"

    # Build URL with query parameters
    url = f"https://weather.googleapis.com/v1/{endpoint}?key={GOOGLE_MAPS_API_KEY}&location.latitude={coords['lat']}&location.longitude={coords['lng']}"

    try:
        response = requests.get(url)

        # DEBUG: Print Weather API response for troubleshooting
        print(f"[DEBUG] Weather API URL: {url}", flush=True)
        print(f"[DEBUG] Weather API response status: {response.status_code}", flush=True)
        print(f"[DEBUG] Weather API response text: {response.text[:500] if response.text else 'EMPTY'}", flush=True)

        # Check for empty response
        if not response.text:
            return f"Error: Google Weather API returned an empty response (status {response.status_code}). Check your API key and ensure the Weather API is enabled."

        # Check for non-200 status
        if response.status_code != 200:
            return f"Error: Google Weather API returned status {response.status_code}: {response.text[:200]}"

        data = response.json()

        # Check for API error
        if "error" in data:
            error_msg = data["error"].get("message", "Unknown error")
            return f"Error: Google Weather API error - {error_msg}"

        # Parse response
        days_data = data.get("forecastDays", data.get("historyDays", []))
        if not days_data:
            return f"Error: Could not retrieve weather data for {city}. The Google Weather API may not have data for the requested dates."

        forecasts = []

        for day_data in days_data[:num_days]:
            # Extract date - API uses "displayDate" not "date"
            date_info = day_data.get("displayDate", {})
            forecast_date = f"{date_info.get('year', '')}-{str(date_info.get('month', '')).zfill(2)}-{str(date_info.get('day', '')).zfill(2)}"

            # Get daytime and nighttime conditions
            daytime = day_data.get("daytimeForecast", day_data.get("daytimeConditions", {}))
            nighttime = day_data.get("nighttimeForecast", day_data.get("nighttimeConditions", {}))

            # Extract temperatures (in Celsius) - at day level, not inside daytime/nighttime
            temp_max = day_data.get("maxTemperature", {}).get("degrees", 15)
            temp_min = day_data.get("minTemperature", {}).get("degrees", 5)

            # Extract precipitation probability - nested under precipitation.probability.percent
            precip_prob = daytime.get("precipitation", {}).get("probability", {}).get("percent", 0)

            # Extract weather condition - nested under weatherCondition.description.text
            weather_cond = daytime.get("weatherCondition", {})
            condition = weather_cond.get("description", {}).get("text", weather_cond.get("type", "Unknown"))

            # Clothing recommendations based on temperature
            avg_temp = (temp_max + temp_min) / 2
            if avg_temp < 0:
                clothing = "Heavy winter coat, thermal layers, winter boots, gloves, scarf, warm hat"
            elif avg_temp < 10:
                clothing = "Warm jacket, layers, long pants, closed shoes"
            elif avg_temp < 20:
                clothing = "Light jacket or sweater, long pants or jeans"
            elif avg_temp < 30:
                clothing = "T-shirt, shorts or light pants, comfortable shoes"
            else:
                clothing = "Light, breathable clothing, hat, sunglasses, sunscreen"

            # Umbrella recommendation
            umbrella = "Yes, bring an umbrella" if precip_prob > 30 else "No umbrella needed"

            forecasts.append({
                "date": forecast_date,
                "temperature_high": f"{temp_max}°C",
                "temperature_low": f"{temp_min}°C",
                "condition": condition,
                "precipitation_probability": f"{precip_prob}%",
                "clothing_recommendation": clothing,
                "umbrella": umbrella
            })

        return json.dumps({
            "city": city,
            "forecasts": forecasts,
            "source": "Google Weather API (history)" if use_history else "Google Weather API (forecast)",
            "currentTime": datetime.now().isoformat()
        }, indent=2)

    except Exception as e:
        print(f"[DEBUG] Exception in get_weather_forecast: {type(e).__name__}: {e}", flush=True)
        return f"Error fetching weather data: {str(e)}"


@tool
def get_air_quality_forecast(city: str, date: str, num_days: int = 1) -> str:
    """
    Get air quality forecast or historical data for a city for specified number of days.
    Uses Google Air Quality API with automatic history/forecast routing based on date.
    Based on Canadian Health Authority guidelines for mask usage.

    Args:
        city: Name of the city (e.g., "Toronto, Canada")
        date: Start date in YYYY-MM-DD format
        num_days: Number of days to retrieve (1-4 for forecast, more available for history)

    Returns:
        Air quality index, health recommendations, and mask requirements.
    """
    print(f"[DEBUG] get_air_quality_forecast called with: city={city}, date={date}, num_days={num_days}", flush=True)

    # Validate date range
    is_valid, error_msg = validate_date_range(date)
    if not is_valid:
        return f"Error: {error_msg}"

    if not check_location_allowed(city):
        print(f"[DEBUG] Location not allowed: {city}", flush=True)
        return f"Error: Travel to {city} is not allowed. This destination is on Canada's travel advisory restricted list."

    coords = get_coordinates(city)
    if not coords:
        print(f"[DEBUG] Could not get coordinates for: {city}", flush=True)
        return f"Error: Could not find coordinates for {city}"

    if not GOOGLE_MAPS_API_KEY:
        print("[DEBUG] GOOGLE_MAPS_API_KEY not set", flush=True)
        return f"Error: Google Maps API key not configured. Please set GOOGLE_MAPS_API_KEY."

    # Limit to 4 days for forecast as per API requirements
    use_history = is_past_date(date)
    if not use_history:
        num_days = min(num_days, 4)
    else:
        # History data is only available for the past 720 hours (30 days)
        request_date = datetime.strptime(date, "%Y-%m-%d")
        days_ago = (datetime.now() - request_date).days
        if days_ago > 30:
            return f"Error: Historical air quality data is only available for the past 30 days. The requested date ({date}) is {days_ago} days ago."

    # Determine endpoint based on date
    endpoint = "history:lookup" if use_history else "forecast:lookup"
    url = f"https://airquality.googleapis.com/v1/{endpoint}"

    headers = {"Content-Type": "application/json"}

    if use_history:
        # History endpoint requires a period with date range
        end_date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=num_days)).strftime("%Y-%m-%d")
        body = {
            "location": {
                "latitude": coords["lat"],
                "longitude": coords["lng"]
            },
            "period": {
                "startTime": f"{date}T00:00:00Z",
                "endTime": f"{end_date}T00:00:00Z"
            },
            "extraComputations": ["HEALTH_RECOMMENDATIONS"]
        }
    else:
        # Forecast endpoint requires dateTime parameter
        # pageSize is in hours, not days. Max pageSize per request is 24.
        # For more than 24 hours, pagination via nextPageToken would be required.
        page_size_hours = min(num_days * 24, 24)

        # For today's date, use current time to avoid "time period not supported" errors
        # The API rejects times that have already passed in UTC
        request_date = datetime.strptime(date, "%Y-%m-%d").date()
        today = datetime.now().date()

        if request_date == today:
            # Use current time rounded up to next hour for today
            now = datetime.utcnow()
            forecast_datetime = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            date_time_str = forecast_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            # For future dates, use noon
            date_time_str = f"{date}T12:00:00Z"

        body = {
            "location": {
                "latitude": coords["lat"],
                "longitude": coords["lng"]
            },
            "dateTime": date_time_str,
            "pageSize": page_size_hours,
            "universalAqi": True,
            "extraComputations": ["HEALTH_RECOMMENDATIONS"]
        }

    try:
        full_url = f"{url}?key={GOOGLE_MAPS_API_KEY}"
        response = requests.post(
            full_url,
            headers=headers,
            json=body
        )

        # DEBUG: Print Air Quality API response for troubleshooting
        print(f"[DEBUG] Air Quality API URL: {url}", flush=True)
        print(f"[DEBUG] Air Quality API request body: {json.dumps(body)}", flush=True)
        print(f"[DEBUG] Air Quality API response status: {response.status_code}", flush=True)
        print(f"[DEBUG] Air Quality API response text: {response.text[:500] if response.text else 'EMPTY'}", flush=True)

        # Check for empty response
        if not response.text:
            return f"Error: Google Air Quality API returned an empty response (status {response.status_code}). Check your API key and ensure the Air Quality API is enabled."

        # Check for non-200 status
        if response.status_code != 200:
            return f"Error: Google Air Quality API returned status {response.status_code}: {response.text[:200]}"

        data = response.json()

        # Check for API error
        if "error" in data:
            error_msg = data["error"].get("message", "Unknown error")
            return f"Error: Google Air Quality API error - {error_msg}"

        # Parse response - handle both hourly and daily data formats
        hourly_data = data.get("hourlyForecasts", data.get("hoursInfo", []))

        if hourly_data:
            # Group hourly data by day using 24-hour chunks from the first data point
            # This avoids issues when forecast starts mid-day (e.g., requesting at 10 PM)
            daily_forecasts = []
            current_date = datetime.strptime(date, "%Y-%m-%d")

            for day in range(num_days):
                day_date = current_date + timedelta(days=day)
                day_str = day_date.strftime("%Y-%m-%d")

                # Use 24-hour chunks: Day 1 = hours 0-23, Day 2 = hours 24-47, etc.
                start_idx = day * 24
                end_idx = start_idx + 24
                day_hours = hourly_data[start_idx:end_idx]

                # Extract AQI values, preferring Universal AQI (uaqi) for consistency
                day_aqis = []
                for hour in day_hours:
                    indexes = hour.get("indexes", [])
                    if indexes:
                        # Look for Universal AQI first for consistent results across regions
                        uaqi_index = next((idx for idx in indexes if idx.get("code") == "uaqi"), None)
                        target_index = uaqi_index if uaqi_index else indexes[0]
                        aqi = target_index.get("aqi", target_index.get("aqiDisplay"))
                        if aqi is not None:
                            day_aqis.append(int(aqi) if isinstance(aqi, str) else aqi)

                avg_aqi = sum(day_aqis) / len(day_aqis) if day_aqis else 50

                # Determine mask requirement based on Canadian Health Authority guidelines
                if avg_aqi <= 50:
                    mask_needed = False
                    category = "Good"
                    mask_description = "Air quality is good (AQHI 1-3). No mask needed per Health Canada guidelines."
                elif avg_aqi <= 100:
                    mask_needed = False
                    category = "Moderate"
                    mask_description = "Air quality is moderate (AQHI 4-6). Sensitive individuals may consider a mask."
                elif avg_aqi <= 150:
                    mask_needed = True
                    category = "Unhealthy for Sensitive Groups"
                    mask_description = "Unhealthy for sensitive groups (AQHI 7). Mask recommended per Health Canada."
                elif avg_aqi <= 200:
                    mask_needed = True
                    category = "Unhealthy"
                    mask_description = "Unhealthy (AQHI 8-10). Mask required per Health Canada guidelines."
                elif avg_aqi <= 300:
                    mask_needed = True
                    category = "Very Unhealthy"
                    mask_description = "Very unhealthy (AQHI 10+). N95 mask required."
                else:
                    mask_needed = True
                    category = "Hazardous"
                    mask_description = "Hazardous. N95 mask required. Consider staying indoors."

                daily_forecasts.append({
                    "date": day_str,
                    "aqi": round(avg_aqi),
                    "category": category,
                    "mask_needed": mask_needed,
                    "health_recommendation": mask_description
                })

            total_masks = sum(1 for f in daily_forecasts if f["mask_needed"])

            return json.dumps({
                "city": city,
                "forecasts": daily_forecasts,
                "total_masks_needed": total_masks,
                "source": f"Google Air Quality API ({'history' if use_history else 'forecast'}) - Health Canada AQHI Guidelines",
                "currentTime": datetime.now().isoformat()
            }, indent=2)

        return f"Error: Could not retrieve air quality data for {city}. The Google Air Quality API may not have data for the requested dates."

    except Exception as e:
        print(f"[DEBUG] Exception in get_air_quality_forecast: {type(e).__name__}: {e}", flush=True)
        return f"Error fetching air quality data: {str(e)}"


@tool
def get_tourist_attractions(city: str, num_attractions: int = 5) -> str:
    """
    Get a list of popular tourist attractions in a city with their addresses.
    Uses Google Places Text Search API.

    Args:
        city: Name of the city (e.g., "Toronto, Canada")
        num_attractions: Number of attractions to retrieve (default 5)

    Returns:
        List of tourist attractions with names, addresses, and ratings.
    """
    if not check_location_allowed(city):
        return f"Error: Travel to {city} is not allowed. This destination is on Canada's travel advisory restricted list."

    if GOOGLE_MAPS_API_KEY:
        # Use Google Places Text Search API
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.types"
        }

        body = {
            "textQuery": f"tourist attractions in {city}",
            "maxResultCount": num_attractions
        }

        try:
            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if "places" in data:
                attractions = []
                for place in data["places"][:num_attractions]:
                    attractions.append({
                        "name": place.get("displayName", {}).get("text", "Unknown"),
                        "address": place.get("formattedAddress", "Address not available"),
                        "rating": place.get("rating")
                    })

                return json.dumps({
                    "city": city,
                    "attractions": attractions,
                    "currentTime": datetime.now().isoformat()
                }, indent=2)

        except Exception as e:
            print(f"Google Places API error: {e}")

    # Fallback: Return common attractions for known cities
    known_attractions = {
        "toronto": [
            {"name": "CN Tower", "address": "290 Bremner Blvd, Toronto, ON M5V 3L9, Canada", "rating": 4.6},
            {"name": "Royal Ontario Museum", "address": "100 Queens Park, Toronto, ON M5S 2C6, Canada", "rating": 4.5},
            {"name": "Ripley's Aquarium of Canada", "address": "288 Bremner Blvd, Toronto, ON M5V 3L9, Canada", "rating": 4.5},
            {"name": "Art Gallery of Ontario", "address": "317 Dundas St W, Toronto, ON M5T 1G4, Canada", "rating": 4.6},
            {"name": "Casa Loma", "address": "1 Austin Terrace, Toronto, ON M5R 1X8, Canada", "rating": 4.4}
        ],
        "chicago": [
            {"name": "The Art Institute of Chicago", "address": "111 S Michigan Ave, Chicago, IL 60603, USA", "rating": 4.8},
            {"name": "Millennium Park", "address": "201 E Randolph St, Chicago, IL 60602, USA", "rating": 4.8},
            {"name": "Willis Tower Skydeck", "address": "233 S Wacker Dr, Chicago, IL 60606, USA", "rating": 4.6},
            {"name": "Navy Pier", "address": "600 E Grand Ave, Chicago, IL 60611, USA", "rating": 4.4},
            {"name": "Field Museum", "address": "1400 S Lake Shore Dr, Chicago, IL 60605, USA", "rating": 4.7}
        ],
        "new york": [
            {"name": "Statue of Liberty", "address": "Liberty Island, New York, NY 10004, USA", "rating": 4.7},
            {"name": "Central Park", "address": "New York, NY 10024, USA", "rating": 4.8},
            {"name": "Empire State Building", "address": "20 W 34th St, New York, NY 10001, USA", "rating": 4.7},
            {"name": "Times Square", "address": "Manhattan, NY 10036, USA", "rating": 4.6},
            {"name": "Metropolitan Museum of Art", "address": "1000 5th Ave, New York, NY 10028, USA", "rating": 4.8}
        ],
        "miami": [
            {"name": "South Beach", "address": "Ocean Dr, Miami Beach, FL 33139, USA", "rating": 4.7},
            {"name": "Vizcaya Museum and Gardens", "address": "3251 S Miami Ave, Miami, FL 33129, USA", "rating": 4.7},
            {"name": "Wynwood Walls", "address": "2516 NW 2nd Ave, Miami, FL 33127, USA", "rating": 4.6},
            {"name": "Pérez Art Museum Miami", "address": "1103 Biscayne Blvd, Miami, FL 33132, USA", "rating": 4.5},
            {"name": "Little Havana", "address": "SW 8th St, Miami, FL 33135, USA", "rating": 4.5}
        ]
    }

    city_lower = city.lower()
    for known_city, attractions in known_attractions.items():
        if known_city in city_lower:
            return json.dumps({
                "city": city,
                "attractions": attractions[:num_attractions],
                "currentTime": datetime.now().isoformat()
            }, indent=2)

    return json.dumps({
        "city": city,
        "attractions": [],
        "message": f"No attractions data available for {city}. Please try a major city.",
        "currentTime": datetime.now().isoformat()
    }, indent=2)


@tool
def get_place_address(place_name: str, city: str) -> str:
    """
    Get the geographical address of a specific place using Google Places Text Search API.

    Args:
        place_name: Name of the place (e.g., "CN Tower")
        city: City where the place is located (e.g., "Toronto")

    Returns:
        Full geographical address of the place.
    """
    if not check_location_allowed(city):
        return f"Error: Travel to {city} is not allowed. This destination is on Canada's travel advisory restricted list."

    if GOOGLE_MAPS_API_KEY:
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
        }

        body = {
            "textQuery": f"{place_name} in {city}",
            "maxResultCount": 1
        }

        try:
            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if "places" in data and data["places"]:
                place = data["places"][0]
                return json.dumps({
                    "place_name": place.get("displayName", {}).get("text", place_name),
                    "address": place.get("formattedAddress", "Address not found"),
                    "location": place.get("location", {}),
                    "currentTime": datetime.now().isoformat()
                }, indent=2)

        except Exception as e:
            print(f"Google Places API error: {e}")

    # Fallback for known places
    known_places = {
        "cn tower": "290 Bremner Blvd, Toronto, ON M5V 3L9, Canada",
        "royal ontario museum": "100 Queens Park, Toronto, ON M5S 2C6, Canada",
        "the art institute of chicago": "111 S Michigan Ave, Chicago, IL 60603, USA",
        "griffin museum of science and industry": "5700 S DuSable Lake Shore Dr, Chicago, IL 60637, USA",
        "museum of science and industry": "5700 S DuSable Lake Shore Dr, Chicago, IL 60637, USA"
    }

    place_lower = place_name.lower()
    if place_lower in known_places:
        return json.dumps({
            "place_name": place_name,
            "address": known_places[place_lower],
            "currentTime": datetime.now().isoformat()
        }, indent=2)

    return json.dumps({
        "place_name": place_name,
        "address": f"Address not found for {place_name} in {city}",
        "currentTime": datetime.now().isoformat()
    }, indent=2)


@tool
def check_attraction_availability(attraction_name: str, city: str, date: str, time_range: str) -> str:
    """
    Check if a tourist attraction is open on a specific date and time.
    IMPORTANT: Always use this tool to verify attraction availability before including
    an attraction in the travel plan. This helps avoid scheduling visits when attractions
    are closed.

    Args:
        attraction_name: Name of the attraction (e.g., "CN Tower", "Royal Ontario Museum")
        city: City where the attraction is located (e.g., "Toronto")
        date: Date of planned visit in YYYY-MM-DD format
        time_range: Planned visit time range (e.g., "8am-9am", "10:00-12:00")

    Returns:
        JSON with availability status, opening hours, and any warnings.
    """
    if not check_location_allowed(city):
        return json.dumps({
            "error": f"Travel to {city} is not allowed. This destination is on Canada's travel advisory restricted list.",
            "currentTime": datetime.now().isoformat()
        }, indent=2)

    # Validate date
    is_valid, error_msg = validate_date_range(date)
    if not is_valid:
        return json.dumps({
            "error": error_msg,
            "currentTime": datetime.now().isoformat()
        }, indent=2)

    result = {
        "attraction": attraction_name,
        "city": city,
        "date": date,
        "planned_visit_time": time_range,
        "is_available": True,
        "warning": None,
        "opening_hours": "Unknown",
        "address": "Address not available"
    }

    if GOOGLE_MAPS_API_KEY:
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.regularOpeningHours,places.currentOpeningHours"
        }

        body = {
            "textQuery": f"{attraction_name} in {city}",
            "maxResultCount": 1
        }

        try:
            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if "places" in data and data["places"]:
                place = data["places"][0]
                result["attraction"] = place.get("displayName", {}).get("text", attraction_name)
                result["address"] = place.get("formattedAddress", "Address not available")

                # Check opening hours
                opening_hours = place.get("regularOpeningHours", {})
                current_hours = place.get("currentOpeningHours", {})

                # Use current hours if available (more accurate), otherwise regular hours
                hours_to_check = current_hours if current_hours else opening_hours

                if hours_to_check:
                    availability = check_attraction_open_at_time(hours_to_check, date, time_range)
                    result["is_available"] = availability["is_open"]
                    result["opening_hours"] = availability["hours_on_date"]

                    if not availability["is_open"]:
                        result["warning"] = f"⚠️ CLOSED: {availability['reason']}"
                    else:
                        result["status_message"] = availability["reason"]
                else:
                    result["opening_hours"] = "Hours not available from Google Places"
                    result["status_message"] = "Opening hours not available - please verify directly with the attraction"

        except Exception as e:
            print(f"Google Places API error: {e}")
            result["status_message"] = f"Could not verify hours: {str(e)}"

    else:
        # Fallback: provide known hours for popular attractions
        known_hours = {
            "cn tower": {
                "hours": "9:00 AM - 10:30 PM daily",
                "closed_days": []
            },
            "royal ontario museum": {
                "hours": "10:00 AM - 5:30 PM (closed Mondays except holidays)",
                "closed_days": [0]  # Monday
            },
            "art gallery of ontario": {
                "hours": "10:30 AM - 5:00 PM (closed Mondays)",
                "closed_days": [0]  # Monday
            },
            "the art institute of chicago": {
                "hours": "11:00 AM - 5:00 PM (closed Tuesdays)",
                "closed_days": [1]  # Tuesday
            },
            "art institute of chicago": {
                "hours": "11:00 AM - 5:00 PM (closed Tuesdays)",
                "closed_days": [1]  # Tuesday
            },
            "griffin museum of science and industry": {
                "hours": "9:30 AM - 4:00 PM (closed some Tuesdays)",
                "closed_days": []
            },
            "museum of science and industry": {
                "hours": "9:30 AM - 4:00 PM (closed some Tuesdays)",
                "closed_days": []
            },
            "field museum": {
                "hours": "9:00 AM - 5:00 PM daily",
                "closed_days": []
            },
            "metropolitan museum of art": {
                "hours": "10:00 AM - 5:00 PM (closed Wednesdays)",
                "closed_days": [2]  # Wednesday
            }
        }

        attraction_lower = attraction_name.lower()
        for known_name, hours_info in known_hours.items():
            if known_name in attraction_lower or attraction_lower in known_name:
                result["opening_hours"] = hours_info["hours"]

                # Check if closed on the target day
                try:
                    target_dt = datetime.strptime(date, "%Y-%m-%d")
                    day_of_week = target_dt.weekday()
                    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

                    if day_of_week in hours_info["closed_days"]:
                        result["is_available"] = False
                        result["warning"] = f"⚠️ CLOSED: {attraction_name} is typically closed on {day_names[day_of_week]}s"
                except Exception:
                    pass
                break

    result["currentTime"] = datetime.now().isoformat()
    return json.dumps(result, indent=2)


@tool
def calculate_total_masks(air_quality_results: str) -> str:
    """
    Calculate the total number of masks Michael needs for his entire trip.
    Based on Canadian Health Authority guidelines.

    Args:
        air_quality_results: JSON string containing air quality data for all cities

    Returns:
        Total mask count and breakdown by city.
    """
    try:
        data = json.loads(air_quality_results) if isinstance(air_quality_results, str) else air_quality_results

        total_masks = 0
        breakdown = []

        if isinstance(data, list):
            for city_data in data:
                city = city_data.get("city", "Unknown")
                masks = city_data.get("total_masks_needed", 0)
                total_masks += masks
                breakdown.append({"city": city, "masks_needed": masks})
        else:
            city = data.get("city", "Unknown")
            masks = data.get("total_masks_needed", 0)
            total_masks = masks
            breakdown.append({"city": city, "masks_needed": masks})

        return json.dumps({
            "total_masks_for_trip": total_masks,
            "breakdown_by_city": breakdown,
            "recommendation": f"Michael should pack {total_masks} mask(s) for this trip." if total_masks > 0 else "No masks needed for this trip based on current air quality forecasts.",
            "source": "Canadian Health Authority (Health Canada) AQHI Guidelines",
            "currentTime": datetime.now().isoformat()
        }, indent=2)

    except Exception as e:
        return f"Error calculating masks: {str(e)}"


@tool
def get_restaurant_recommendations(city: str, date: str, cuisine_preference: Optional[str] = None) -> str:
    """
    Get well-reviewed restaurant recommendations for a city, grouped by price tier.
    Uses Bayesian rating to weight review scores by number of reviews for statistical confidence.
    Prioritizes restaurants serving local cuisine and filters by opening hours.

    Args:
        city: Name of the city (e.g., "Toronto, Canada")
        date: Date of visit in YYYY-MM-DD format (used to check if restaurants are open)
        cuisine_preference: Optional specific cuisine type to search for

    Returns:
        Top 3 restaurants per price tier with ratings, cost estimates, and local cuisine indicators.
    """
    # Validate date range
    is_valid, error_msg = validate_date_range(date)
    if not is_valid:
        return f"Error: {error_msg}"

    if not check_location_allowed(city):
        return f"Error: Travel to {city} is not allowed. This destination is on Canada's travel advisory restricted list."

    coords = get_coordinates(city)
    if not coords:
        return f"Error: Could not find coordinates for {city}"

    all_restaurants = []

    # Build search query
    search_query = f"restaurants in {city}"
    if cuisine_preference:
        search_query = f"{cuisine_preference} restaurants in {city}"

    if GOOGLE_MAPS_API_KEY:
        # Use Google Places Text Search API with restaurant-specific fields
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.priceLevel,places.types,places.regularOpeningHours,places.primaryType,places.editorialSummary"
        }

        body = {
            "textQuery": search_query,
            "maxResultCount": 40,  # Fetch more to filter and rank
            "locationBias": {
                "circle": {
                    "center": {"latitude": coords["lat"], "longitude": coords["lng"]},
                    "radius": 10000.0  # 10km radius
                }
            }
        }

        try:
            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if "places" in data:
                for place in data["places"]:
                    # Extract data
                    name = place.get("displayName", {}).get("text", "Unknown")
                    address = place.get("formattedAddress", "Address not available")
                    rating = place.get("rating", 0)
                    num_reviews = place.get("userRatingCount", 0)
                    price_level_str = place.get("priceLevel", "PRICE_LEVEL_UNSPECIFIED")
                    types = place.get("types", [])
                    opening_hours = place.get("regularOpeningHours", {})
                    primary_type = place.get("primaryType", "restaurant")
                    summary = place.get("editorialSummary", {}).get("text", "")

                    # Convert price level string to numeric
                    price_level_map = {
                        "PRICE_LEVEL_FREE": 0,
                        "PRICE_LEVEL_INEXPENSIVE": 1,
                        "PRICE_LEVEL_MODERATE": 2,
                        "PRICE_LEVEL_EXPENSIVE": 3,
                        "PRICE_LEVEL_VERY_EXPENSIVE": 4,
                        "PRICE_LEVEL_UNSPECIFIED": 2  # Default to moderate
                    }
                    price_level = price_level_map.get(price_level_str, 2)

                    # Skip if closed on the travel date
                    if not check_restaurant_open_on_date(opening_hours, date):
                        continue

                    # Skip if no rating
                    if rating == 0:
                        continue

                    # Calculate Bayesian weighted rating
                    bayesian_rating = calculate_bayesian_rating(rating, num_reviews)

                    # Add local cuisine boost
                    local_boost = get_local_cuisine_boost(types, city)
                    final_score = bayesian_rating + local_boost

                    # Determine if this is local cuisine
                    is_local_cuisine = local_boost > 0

                    all_restaurants.append({
                        "name": name,
                        "address": address,
                        "raw_rating": rating,
                        "num_reviews": num_reviews,
                        "bayesian_rating": bayesian_rating,
                        "local_cuisine_boost": local_boost,
                        "final_score": round(final_score, 2),
                        "price_level": price_level,
                        "types": types[:5],  # Limit types for readability
                        "primary_type": primary_type,
                        "is_local_cuisine": is_local_cuisine,
                        "summary": summary
                    })

        except Exception as e:
            print(f"Google Places API error: {e}")

    # Fallback data for known cities
    if not all_restaurants:
        fallback_restaurants = {
            "toronto": [
                {"name": "Canoe", "address": "66 Wellington St W, Toronto, ON", "raw_rating": 4.5, "num_reviews": 2847, "price_level": 4, "types": ["canadian", "fine dining"], "is_local_cuisine": True, "summary": "Upscale Canadian cuisine with city views"},
                {"name": "Pai Northern Thai Kitchen", "address": "18 Duncan St, Toronto, ON", "raw_rating": 4.6, "num_reviews": 5234, "price_level": 2, "types": ["thai"], "is_local_cuisine": False, "summary": "Popular Thai restaurant"},
                {"name": "St. Lawrence Market Kitchen", "address": "93 Front St E, Toronto, ON", "raw_rating": 4.4, "num_reviews": 1523, "price_level": 1, "types": ["canadian", "market"], "is_local_cuisine": True, "summary": "Iconic market with peameal bacon sandwiches"},
                {"name": "Alo Restaurant", "address": "163 Spadina Ave, Toronto, ON", "raw_rating": 4.8, "num_reviews": 892, "price_level": 4, "types": ["french", "fine dining"], "is_local_cuisine": False, "summary": "Acclaimed French tasting menu"},
                {"name": "Banh Mi Boys", "address": "392 Queen St W, Toronto, ON", "raw_rating": 4.3, "num_reviews": 3421, "price_level": 1, "types": ["vietnamese", "fusion"], "is_local_cuisine": True, "summary": "Creative Vietnamese fusion"},
                {"name": "Richmond Station", "address": "1 Richmond St W, Toronto, ON", "raw_rating": 4.4, "num_reviews": 1876, "price_level": 3, "types": ["canadian", "farm to table"], "is_local_cuisine": True, "summary": "Farm-to-table Canadian fare"},
            ],
            "chicago": [
                {"name": "Lou Malnati's Pizzeria", "address": "439 N Wells St, Chicago, IL", "raw_rating": 4.5, "num_reviews": 8932, "price_level": 2, "types": ["pizza", "deep dish", "chicago style"], "is_local_cuisine": True, "summary": "Famous Chicago deep dish pizza"},
                {"name": "Alinea", "address": "1723 N Halsted St, Chicago, IL", "raw_rating": 4.7, "num_reviews": 2341, "price_level": 4, "types": ["american", "fine dining", "molecular gastronomy"], "is_local_cuisine": True, "summary": "Three-Michelin-star molecular gastronomy"},
                {"name": "Portillo's", "address": "100 W Ontario St, Chicago, IL", "raw_rating": 4.4, "num_reviews": 12453, "price_level": 1, "types": ["hot dog", "italian beef", "chicago style"], "is_local_cuisine": True, "summary": "Iconic Chicago hot dogs and Italian beef"},
                {"name": "Girl & The Goat", "address": "809 W Randolph St, Chicago, IL", "raw_rating": 4.5, "num_reviews": 4521, "price_level": 3, "types": ["american", "small plates"], "is_local_cuisine": True, "summary": "Celebrity chef restaurant with bold flavors"},
                {"name": "Al's Beef", "address": "169 W Ontario St, Chicago, IL", "raw_rating": 4.2, "num_reviews": 2156, "price_level": 1, "types": ["italian beef", "chicago style"], "is_local_cuisine": True, "summary": "Classic Chicago Italian beef since 1938"},
                {"name": "Gibsons Bar & Steakhouse", "address": "1028 N Rush St, Chicago, IL", "raw_rating": 4.6, "num_reviews": 3892, "price_level": 4, "types": ["steakhouse", "american"], "is_local_cuisine": True, "summary": "Legendary Chicago steakhouse"},
            ],
            "new york": [
                {"name": "Joe's Pizza", "address": "7 Carmine St, New York, NY", "raw_rating": 4.5, "num_reviews": 9823, "price_level": 1, "types": ["pizza", "new york style"], "is_local_cuisine": True, "summary": "Classic NYC slice joint"},
                {"name": "Katz's Delicatessen", "address": "205 E Houston St, New York, NY", "raw_rating": 4.5, "num_reviews": 15234, "price_level": 2, "types": ["deli", "jewish deli", "pastrami"], "is_local_cuisine": True, "summary": "Legendary Jewish deli since 1888"},
                {"name": "Le Bernardin", "address": "155 W 51st St, New York, NY", "raw_rating": 4.7, "num_reviews": 3421, "price_level": 4, "types": ["french", "seafood", "fine dining"], "is_local_cuisine": False, "summary": "Three-Michelin-star seafood temple"},
                {"name": "Russ & Daughters Cafe", "address": "127 Orchard St, New York, NY", "raw_rating": 4.6, "num_reviews": 4532, "price_level": 2, "types": ["jewish deli", "bagels", "appetizing"], "is_local_cuisine": True, "summary": "Iconic bagels and smoked fish"},
                {"name": "Peter Luger Steak House", "address": "178 Broadway, Brooklyn, NY", "raw_rating": 4.4, "num_reviews": 7823, "price_level": 4, "types": ["steakhouse", "american"], "is_local_cuisine": True, "summary": "Brooklyn's legendary steakhouse since 1887"},
                {"name": "Xi'an Famous Foods", "address": "81 St Marks Pl, New York, NY", "raw_rating": 4.4, "num_reviews": 5621, "price_level": 1, "types": ["chinese", "noodles"], "is_local_cuisine": True, "summary": "Hand-pulled noodles and cumin lamb"},
            ],
            "miami": [
                {"name": "Versailles Restaurant", "address": "3555 SW 8th St, Miami, FL", "raw_rating": 4.3, "num_reviews": 11234, "price_level": 2, "types": ["cuban", "latin"], "is_local_cuisine": True, "summary": "Miami's most famous Cuban restaurant"},
                {"name": "Joe's Stone Crab", "address": "11 Washington Ave, Miami Beach, FL", "raw_rating": 4.5, "num_reviews": 6543, "price_level": 4, "types": ["seafood", "stone crab"], "is_local_cuisine": True, "summary": "Legendary stone crabs since 1913"},
                {"name": "La Carreta", "address": "3632 SW 8th St, Miami, FL", "raw_rating": 4.2, "num_reviews": 4521, "price_level": 1, "types": ["cuban", "latin"], "is_local_cuisine": True, "summary": "24-hour Cuban comfort food"},
                {"name": "Mandolin Aegean Bistro", "address": "4312 NE 2nd Ave, Miami, FL", "raw_rating": 4.6, "num_reviews": 2341, "price_level": 3, "types": ["greek", "turkish", "mediterranean"], "is_local_cuisine": False, "summary": "Charming Greek-Turkish garden dining"},
                {"name": "Cvi.che 105", "address": "105 NE 3rd Ave, Miami, FL", "raw_rating": 4.5, "num_reviews": 3892, "price_level": 3, "types": ["peruvian", "ceviche", "latin"], "is_local_cuisine": True, "summary": "Acclaimed Peruvian ceviche"},
                {"name": "El Rey de las Fritas", "address": "1821 SW 8th St, Miami, FL", "raw_rating": 4.4, "num_reviews": 1892, "price_level": 1, "types": ["cuban", "fritas", "burgers"], "is_local_cuisine": True, "summary": "Best Cuban fritas in town"},
            ],
        }

        city_lower = city.lower()
        for known_city, restaurants in fallback_restaurants.items():
            if known_city in city_lower:
                for r in restaurants:
                    r["bayesian_rating"] = calculate_bayesian_rating(r["raw_rating"], r["num_reviews"])
                    local_boost = 0.25 if r.get("is_local_cuisine") else 0
                    r["local_cuisine_boost"] = local_boost
                    r["final_score"] = round(r["bayesian_rating"] + local_boost, 2)
                all_restaurants = restaurants
                break

    if not all_restaurants:
        return json.dumps({
            "city": city,
            "date": date,
            "restaurants_by_tier": {},
            "message": f"No restaurant data available for {city}. Please try a major city.",
            "currentTime": datetime.now().isoformat()
        }, indent=2)

    # Group by price tier and sort by final score
    tiers = {1: [], 2: [], 3: [], 4: []}
    for restaurant in all_restaurants:
        tier = restaurant.get("price_level", 2)
        if tier == 0:
            tier = 1  # Free places go to budget tier
        if tier in tiers:
            tiers[tier].append(restaurant)

    # Sort each tier by final_score and take top 3
    result_tiers = {}
    for tier_num, restaurants in tiers.items():
        if restaurants:
            sorted_restaurants = sorted(restaurants, key=lambda x: x["final_score"], reverse=True)[:3]
            tier_info = PRICE_TIER_INFO.get(tier_num, PRICE_TIER_INFO[2])

            result_tiers[tier_info["label"]] = {
                "price_symbol": tier_info["symbol"],
                "estimated_cost_per_person": tier_info["estimate_per_person"],
                "restaurants": [
                    {
                        "name": r["name"],
                        "address": r["address"],
                        "displayed_rating": r["raw_rating"],
                        "review_count": r["num_reviews"],
                        "confidence_adjusted_rating": r["bayesian_rating"],
                        "is_local_cuisine": r.get("is_local_cuisine", False),
                        "local_cuisine_bonus": f"+{r['local_cuisine_boost']}" if r.get("local_cuisine_boost", 0) > 0 else "N/A",
                        "final_ranking_score": r["final_score"],
                        "cuisine_types": r.get("types", []),
                        "description": r.get("summary", "")
                    }
                    for r in sorted_restaurants
                ]
            }

    # Calculate total estimated cost for visiting one restaurant per tier
    return json.dumps({
        "city": city,
        "date": date,
        "note": "Restaurants filtered to those open on travel date. Ratings use Bayesian averaging to account for review count confidence.",
        "local_cuisine_note": f"Restaurants serving local {city.split(',')[0].strip()} cuisine receive a ranking boost.",
        "restaurants_by_tier": result_tiers,
        "rating_methodology": {
            "method": "Bayesian Average (IMDB Formula)",
            "formula": "weighted_rating = (reviews × rating + prior_weight × prior_mean) / (reviews + prior_weight)",
            "prior_mean": 3.5,
            "prior_weight": 10,
            "explanation": "Restaurants with few reviews are pulled toward the average (3.5), while restaurants with many reviews reflect their true rating. This prevents a 5-star restaurant with 2 reviews from ranking above a 4.8-star restaurant with 1000 reviews."
        },
        "currentTime": datetime.now().isoformat()
    }, indent=2)


@tool
def get_hotel_recommendation(city: str, date: str, attractions: Optional[List[str]] = None, restaurants: Optional[List[str]] = None) -> str:
    """
    Get a well-reviewed mid-tier hotel recommendation that is centrally located
    between the planned attractions and restaurants.

    Michael prefers mid-tier hotels (not budget, not luxury) that are well-reviewed.
    Uses Bayesian rating to weight reviews by count for statistical confidence.

    Args:
        city: Name of the city (e.g., "Toronto, Canada")
        date: Check-in date in YYYY-MM-DD format
        attractions: Optional list of attraction names to consider for central location
        restaurants: Optional list of restaurant names to consider for central location

    Returns:
        Top 3 mid-tier hotel recommendations with ratings, location info, and cost estimates.
    """
    # Validate date range
    is_valid, error_msg = validate_date_range(date)
    if not is_valid:
        return f"Error: {error_msg}"

    if not check_location_allowed(city):
        return f"Error: Travel to {city} is not allowed. This destination is on Canada's travel advisory restricted list."

    city_coords = get_coordinates(city)
    if not city_coords:
        return f"Error: Could not find coordinates for {city}"

    # Collect coordinates of all points of interest
    poi_coordinates = []
    poi_names = []

    # Get coordinates for attractions
    if attractions:
        for attraction in attractions:
            coords = get_place_coordinates(attraction, city)
            if coords:
                poi_coordinates.append(coords)
                poi_names.append(attraction)

    # Get coordinates for restaurants
    if restaurants:
        for restaurant in restaurants:
            coords = get_place_coordinates(restaurant, city)
            if coords:
                poi_coordinates.append(coords)
                poi_names.append(restaurant)

    # Calculate centroid of all POIs, or use city center if none provided
    if poi_coordinates:
        search_center = calculate_centroid(poi_coordinates)
        location_strategy = f"Centrally located between {len(poi_coordinates)} points of interest"
    else:
        search_center = city_coords
        location_strategy = "Located in city center (no specific attractions/restaurants provided)"

    all_hotels = []

    if GOOGLE_MAPS_API_KEY:
        # Search for mid-tier hotels near the centroid
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.priceLevel,places.types,places.location,places.editorialSummary"
        }

        body = {
            "textQuery": f"hotels in {city}",
            "maxResultCount": 30,
            "locationBias": {
                "circle": {
                    "center": {"latitude": search_center["lat"], "longitude": search_center["lng"]},
                    "radius": 5000.0  # 5km radius from centroid
                }
            }
        }

        try:
            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if "places" in data:
                for place in data["places"]:
                    name = place.get("displayName", {}).get("text", "Unknown")
                    address = place.get("formattedAddress", "Address not available")
                    rating = place.get("rating", 0)
                    num_reviews = place.get("userRatingCount", 0)
                    price_level_str = place.get("priceLevel", "PRICE_LEVEL_UNSPECIFIED")
                    types = place.get("types", [])
                    location = place.get("location", {})
                    summary = place.get("editorialSummary", {}).get("text", "")

                    # Convert price level
                    price_level_map = {
                        "PRICE_LEVEL_FREE": 1,
                        "PRICE_LEVEL_INEXPENSIVE": 1,
                        "PRICE_LEVEL_MODERATE": 2,
                        "PRICE_LEVEL_EXPENSIVE": 3,
                        "PRICE_LEVEL_VERY_EXPENSIVE": 4,
                        "PRICE_LEVEL_UNSPECIFIED": 2
                    }
                    price_level = price_level_map.get(price_level_str, 2)

                    # Filter to mid-tier only (levels 2-3)
                    if price_level not in [2, 3]:
                        continue

                    # Skip if no rating or very few reviews
                    if rating == 0 or num_reviews < 5:
                        continue

                    # Calculate Bayesian weighted rating
                    bayesian_rating = calculate_bayesian_rating(rating, num_reviews)

                    # Calculate distance from centroid
                    hotel_coords = {
                        "lat": location.get("latitude", search_center["lat"]),
                        "lng": location.get("longitude", search_center["lng"])
                    }
                    distance_from_center = calculate_distance_km(search_center, hotel_coords)

                    # Calculate average distance to all POIs
                    if poi_coordinates:
                        distances_to_pois = [calculate_distance_km(hotel_coords, poi) for poi in poi_coordinates]
                        avg_distance_to_pois = sum(distances_to_pois) / len(distances_to_pois)
                        max_distance_to_poi = max(distances_to_pois)
                    else:
                        avg_distance_to_pois = distance_from_center
                        max_distance_to_poi = distance_from_center

                    # Score: prioritize rating but penalize distance slightly
                    # Distance penalty: -0.1 per km from centroid (max -0.5)
                    distance_penalty = min(distance_from_center * 0.1, 0.5)
                    final_score = bayesian_rating - distance_penalty

                    all_hotels.append({
                        "name": name,
                        "address": address,
                        "raw_rating": rating,
                        "num_reviews": num_reviews,
                        "bayesian_rating": bayesian_rating,
                        "price_level": price_level,
                        "distance_from_centroid_km": round(distance_from_center, 2),
                        "avg_distance_to_attractions_km": round(avg_distance_to_pois, 2),
                        "max_distance_to_attraction_km": round(max_distance_to_poi, 2),
                        "distance_penalty": round(distance_penalty, 2),
                        "final_score": round(final_score, 2),
                        "coordinates": hotel_coords,
                        "summary": summary
                    })

        except Exception as e:
            print(f"Google Places API error: {e}")

    # Fallback data for known cities
    if not all_hotels:
        fallback_hotels = {
            "toronto": [
                {"name": "The Strathcona Hotel", "address": "60 York St, Toronto, ON", "raw_rating": 4.2, "num_reviews": 2341, "price_level": 2, "summary": "Downtown hotel near Union Station"},
                {"name": "Chelsea Hotel Toronto", "address": "33 Gerrard St W, Toronto, ON", "raw_rating": 4.1, "num_reviews": 5678, "price_level": 2, "summary": "Family-friendly hotel with pool"},
                {"name": "The Saint James Hotel", "address": "26 Gerrard St E, Toronto, ON", "raw_rating": 4.4, "num_reviews": 1234, "price_level": 3, "summary": "Boutique hotel in downtown core"},
                {"name": "One King West Hotel", "address": "1 King St W, Toronto, ON", "raw_rating": 4.3, "num_reviews": 3456, "price_level": 3, "summary": "Historic building with modern suites"},
                {"name": "Delta Hotels Toronto", "address": "75 Lower Simcoe St, Toronto, ON", "raw_rating": 4.2, "num_reviews": 2890, "price_level": 3, "summary": "Waterfront hotel near CN Tower"},
            ],
            "chicago": [
                {"name": "Hampton Inn Chicago Downtown", "address": "68 E Wacker Pl, Chicago, IL", "raw_rating": 4.3, "num_reviews": 3421, "price_level": 2, "summary": "Riverfront hotel with great views"},
                {"name": "Hilton Garden Inn Chicago Downtown", "address": "10 E Grand Ave, Chicago, IL", "raw_rating": 4.2, "num_reviews": 2156, "price_level": 2, "summary": "Near Magnificent Mile shopping"},
                {"name": "Hotel Felix Chicago", "address": "111 W Huron St, Chicago, IL", "raw_rating": 4.1, "num_reviews": 1892, "price_level": 3, "summary": "Eco-friendly boutique hotel"},
                {"name": "Kinzie Hotel", "address": "20 W Kinzie St, Chicago, IL", "raw_rating": 4.4, "num_reviews": 2341, "price_level": 3, "summary": "Stylish hotel in River North"},
                {"name": "The Godfrey Hotel Chicago", "address": "127 W Huron St, Chicago, IL", "raw_rating": 4.3, "num_reviews": 4123, "price_level": 3, "summary": "Modern hotel with rooftop lounge"},
            ],
            "new york": [
                {"name": "Pod 51 Hotel", "address": "230 E 51st St, New York, NY", "raw_rating": 4.1, "num_reviews": 5678, "price_level": 2, "summary": "Compact rooms in Midtown"},
                {"name": "The Paul Hotel NYC", "address": "32 W 29th St, New York, NY", "raw_rating": 4.3, "num_reviews": 2341, "price_level": 3, "summary": "Trendy NoMad neighborhood hotel"},
                {"name": "Arlo NoMad", "address": "11 E 31st St, New York, NY", "raw_rating": 4.2, "num_reviews": 3892, "price_level": 3, "summary": "Modern hotel with rooftop bar"},
                {"name": "citizenM New York Times Square", "address": "218 W 50th St, New York, NY", "raw_rating": 4.4, "num_reviews": 4521, "price_level": 3, "summary": "Tech-forward hotel near Broadway"},
                {"name": "The Gallivant Times Square", "address": "234 W 48th St, New York, NY", "raw_rating": 4.1, "num_reviews": 2678, "price_level": 2, "summary": "Theater District location"},
            ],
            "miami": [
                {"name": "Generator Miami", "address": "3120 Collins Ave, Miami Beach, FL", "raw_rating": 4.2, "num_reviews": 2341, "price_level": 2, "summary": "Social hotel on Collins Avenue"},
                {"name": "Circa 39 Hotel", "address": "3900 Collins Ave, Miami Beach, FL", "raw_rating": 4.3, "num_reviews": 1892, "price_level": 3, "summary": "Retro-chic Miami Beach hotel"},
                {"name": "The Plymouth Hotel", "address": "336 21st St, Miami Beach, FL", "raw_rating": 4.1, "num_reviews": 1234, "price_level": 3, "summary": "Art Deco boutique hotel"},
                {"name": "Kimpton Surfcomber Hotel", "address": "1717 Collins Ave, Miami Beach, FL", "raw_rating": 4.2, "num_reviews": 3456, "price_level": 3, "summary": "Beachfront with ocean views"},
                {"name": "Freehand Miami", "address": "2727 Indian Creek Dr, Miami Beach, FL", "raw_rating": 4.3, "num_reviews": 2890, "price_level": 2, "summary": "Hip hotel with great bar"},
            ],
        }

        city_lower = city.lower()
        for known_city, hotels in fallback_hotels.items():
            if known_city in city_lower:
                for h in hotels:
                    h["bayesian_rating"] = calculate_bayesian_rating(h["raw_rating"], h["num_reviews"])
                    h["distance_from_centroid_km"] = 1.5  # Approximate for fallback
                    h["avg_distance_to_attractions_km"] = 2.0
                    h["max_distance_to_attraction_km"] = 3.0
                    h["distance_penalty"] = 0.15
                    h["final_score"] = round(h["bayesian_rating"] - 0.15, 2)
                    h["coordinates"] = city_coords
                all_hotels = hotels
                break

    if not all_hotels:
        return json.dumps({
            "city": city,
            "date": date,
            "hotels": [],
            "message": f"No hotel data available for {city}. Please try a major city.",
            "currentTime": datetime.now().isoformat()
        }, indent=2)

    # Sort by final score and take top 3
    sorted_hotels = sorted(all_hotels, key=lambda x: x["final_score"], reverse=True)[:3]

    # Format results
    hotel_results = []
    for h in sorted_hotels:
        tier_info = HOTEL_PRICE_TIER_INFO.get(h["price_level"], HOTEL_PRICE_TIER_INFO[2])
        hotel_results.append({
            "name": h["name"],
            "address": h["address"],
            "displayed_rating": h["raw_rating"],
            "review_count": h["num_reviews"],
            "confidence_adjusted_rating": h["bayesian_rating"],
            "price_tier": tier_info["label"],
            "price_symbol": tier_info["symbol"],
            "estimated_cost_per_night": tier_info["estimate_per_night"],
            "distance_from_ideal_center_km": h["distance_from_centroid_km"],
            "avg_distance_to_activities_km": h["avg_distance_to_attractions_km"],
            "max_distance_to_any_activity_km": h["max_distance_to_attraction_km"],
            "final_ranking_score": h["final_score"],
            "description": h.get("summary", "")
        })

    return json.dumps({
        "city": city,
        "check_in_date": date,
        "location_strategy": location_strategy,
        "search_center": search_center,
        "points_of_interest_considered": poi_names if poi_names else ["City center (default)"],
        "hotel_preference": "Mid-tier ($$-$$$) - well-reviewed, good value",
        "top_recommendations": hotel_results,
        "rating_methodology": {
            "method": "Bayesian Average with Distance Penalty",
            "rating_formula": "weighted_rating = (reviews × rating + 10 × 3.5) / (reviews + 10)",
            "distance_penalty": "-0.1 per km from centroid (max -0.5)",
            "explanation": "Hotels are ranked by confidence-adjusted rating with a small penalty for distance from the central point of all planned activities."
        },
        "currentTime": datetime.now().isoformat()
    }, indent=2)


@tool
def calculate_trip_budget(itinerary: str) -> str:
    """
    Calculate a detailed budget estimate for the entire trip.

    Provides daily breakdowns including:
    - Attraction/activity costs
    - Two meals per day (lunch and dinner at moderate prices)
    - Hotel accommodation (mid to upper mid-range)

    Also provides an overall trip budget range.

    Args:
        itinerary: JSON string or description of the trip itinerary with format:
                  {"cities": [{"name": "Toronto", "date": "2025-01-31",
                   "attractions": [{"name": "CN Tower"}, {"name": "ROM"}]}]}

                  Or natural language like:
                  "Toronto on 2025-01-31: CN Tower, Royal Ontario Museum
                   Chicago on 2025-02-01: Art Institute, Millennium Park"

    Returns:
        Detailed budget breakdown by day and overall trip total.
    """
    import re

    # Parse the itinerary
    daily_budgets = []
    total_min = 0
    total_max = 0

    try:
        # Try to parse as JSON first
        if itinerary.strip().startswith("{"):
            data = json.loads(itinerary)
            cities = data.get("cities", [])
        else:
            # Parse natural language format
            cities = []
            lines = itinerary.strip().split("\n")
            current_city = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Check for city line patterns
                if ":" in line and any(char.isdigit() for char in line):
                    # Format: "City on DATE: attractions" or "City DATE: attractions"
                    parts = line.split(":")
                    city_date_part = parts[0].strip()

                    # Extract date (YYYY-MM-DD pattern)
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', city_date_part)
                    if date_match:
                        date = date_match.group(1)
                        city_name = city_date_part.replace(date, "").replace(" on ", " ").strip()
                    else:
                        # Try to find date at end
                        words = city_date_part.split()
                        date = words[-1] if words else "unknown"
                        city_name = " ".join(words[:-1])

                    # Parse attractions from after the colon
                    attractions_str = ":".join(parts[1:]).strip() if len(parts) > 1 else ""
                    attractions = [{"name": a.strip()} for a in attractions_str.split(",") if a.strip()]

                    current_city = {
                        "name": city_name,
                        "date": date,
                        "attractions": attractions
                    }
                    cities.append(current_city)

                elif line.lower().startswith("city"):
                    # Format: "City1: Toronto 2025-01-31"
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        city_info = parts[1].strip()
                        info_parts = city_info.rsplit(" ", 1)
                        if len(info_parts) == 2:
                            current_city = {
                                "name": info_parts[0].strip(),
                                "date": info_parts[1].strip(),
                                "attractions": []
                            }
                            cities.append(current_city)

                elif current_city and (";" in line or line):
                    # Attraction line
                    if ";" in line:
                        attraction_name = line.split(";")[0].strip()
                    else:
                        attraction_name = line.strip()
                    if attraction_name and not attraction_name.lower().startswith("city"):
                        current_city["attractions"].append({"name": attraction_name})

        if not cities:
            return json.dumps({
                "error": "Could not parse itinerary. Please provide in format: City DATE: Attraction1, Attraction2",
                "example": "Toronto 2025-01-31: CN Tower, Royal Ontario Museum",
                "currentTime": datetime.now().isoformat()
            }, indent=2)

        # Calculate budget for each day
        num_nights = len(cities) - 1 if len(cities) > 1 else 1

        for i, city_data in enumerate(cities):
            city_name = city_data.get("name", "Unknown")
            date = city_data.get("date", "Unknown")
            attractions = city_data.get("attractions", [])

            day_budget = {
                "day": i + 1,
                "city": city_name,
                "date": date,
                "attractions": [],
                "meals": {},
                "accommodation": None,
                "daily_total": {"min": 0, "max": 0}
            }

            # Calculate attraction costs
            attractions_min = 0
            attractions_max = 0

            for attraction in attractions:
                attr_name = attraction.get("name", "Unknown attraction")
                cost = estimate_attraction_cost(attr_name)
                day_budget["attractions"].append({
                    "name": cost["name"],
                    "cost_range": f"${cost['min']}-${cost['max']} USD" if cost["max"] > 0 else "Free",
                    "min": cost["min"],
                    "max": cost["max"]
                })
                attractions_min += cost["min"]
                attractions_max += cost["max"]

            # Add meal costs (moderate tier for Michael)
            lunch = MEAL_COST_ESTIMATES["lunch"]["moderate"]
            dinner = MEAL_COST_ESTIMATES["dinner"]["moderate"]

            day_budget["meals"] = {
                "lunch": {
                    "description": lunch["label"],
                    "cost_range": f"${lunch['min']}-${lunch['max']} USD",
                    "min": lunch["min"],
                    "max": lunch["max"]
                },
                "dinner": {
                    "description": dinner["label"],
                    "cost_range": f"${dinner['min']}-${dinner['max']} USD",
                    "min": dinner["min"],
                    "max": dinner["max"]
                },
                "meals_subtotal": {
                    "min": lunch["min"] + dinner["min"],
                    "max": lunch["max"] + dinner["max"]
                }
            }

            meals_min = lunch["min"] + dinner["min"]
            meals_max = lunch["max"] + dinner["max"]

            # Add hotel cost (only if not the last day, since you check out)
            # Or if it's a single-day trip
            hotel_min = 0
            hotel_max = 0

            if i < len(cities) - 1 or len(cities) == 1:
                # Use mid-range to upper mid-range for Michael
                mid_tier = HOTEL_PRICE_TIER_INFO[2]  # Mid-range
                upper_tier = HOTEL_PRICE_TIER_INFO[3]  # Upper mid-range

                hotel_min = mid_tier["min"]
                hotel_max = upper_tier["max"]

                day_budget["accommodation"] = {
                    "description": "Mid to Upper Mid-Range Hotel ($$-$$$)",
                    "cost_range": f"${hotel_min}-${hotel_max} USD per night",
                    "min": hotel_min,
                    "max": hotel_max,
                    "note": "Michael's preferred tier: quality without luxury prices"
                }
            else:
                day_budget["accommodation"] = {
                    "description": "Check-out day (no hotel charge)",
                    "cost_range": "$0",
                    "min": 0,
                    "max": 0
                }

            # Calculate daily total
            day_min = attractions_min + meals_min + hotel_min
            day_max = attractions_max + meals_max + hotel_max

            day_budget["daily_total"] = {
                "min": day_min,
                "max": day_max,
                "formatted": f"${day_min}-${day_max} USD"
            }

            day_budget["breakdown"] = {
                "attractions": f"${attractions_min}-${attractions_max} USD",
                "meals": f"${meals_min}-${meals_max} USD",
                "hotel": f"${hotel_min}-${hotel_max} USD" if hotel_max > 0 else "N/A (check-out day)"
            }

            daily_budgets.append(day_budget)
            total_min += day_min
            total_max += day_max

        # Create summary
        num_days = len(cities)
        hotel_nights = num_nights if num_nights > 0 else 1

        summary = {
            "trip_duration": f"{num_days} day(s)",
            "hotel_nights": hotel_nights,
            "total_attractions_visited": sum(len(c.get("attractions", [])) for c in cities),
            "total_meals": num_days * 2,
            "budget_breakdown": {
                "attractions_total": {
                    "min": sum(a["min"] for d in daily_budgets for a in d["attractions"]),
                    "max": sum(a["max"] for d in daily_budgets for a in d["attractions"])
                },
                "meals_total": {
                    "min": sum(d["meals"]["meals_subtotal"]["min"] for d in daily_budgets),
                    "max": sum(d["meals"]["meals_subtotal"]["max"] for d in daily_budgets)
                },
                "accommodation_total": {
                    "min": sum(d["accommodation"]["min"] for d in daily_budgets),
                    "max": sum(d["accommodation"]["max"] for d in daily_budgets)
                }
            },
            "overall_budget_range": {
                "minimum": total_min,
                "maximum": total_max,
                "formatted": f"${total_min}-${total_max} USD"
            },
            "average_daily_cost": {
                "min": round(total_min / num_days),
                "max": round(total_max / num_days),
                "formatted": f"${round(total_min / num_days)}-${round(total_max / num_days)} USD per day"
            }
        }

        return json.dumps({
            "trip_budget_estimate": {
                "title": "Detailed Trip Budget Breakdown",
                "note": "All costs in USD. Meals estimated at moderate tier. Hotels at mid to upper mid-range.",
                "daily_breakdown": daily_budgets,
                "summary": summary
            },
            "assumptions": {
                "meals": "2 per day (lunch and dinner) at moderate restaurants ($20-35 lunch, $30-50 dinner)",
                "hotel": "Mid to Upper Mid-Range ($$-$$$): $100-350 per night",
                "attractions": "Entry fees based on known prices or category estimates",
                "not_included": ["Transportation/flights", "Breakfast", "Snacks", "Shopping", "Tips", "Travel insurance"]
            },
            "currentTime": datetime.now().isoformat()
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Error calculating budget: {str(e)}",
            "tip": "Please provide itinerary in format: City DATE: Attraction1, Attraction2",
            "currentTime": datetime.now().isoformat()
        }, indent=2)


@tool
def generate_packing_list(itinerary: str) -> str:
    """
    Generate a complete packing list for Michael's trip based on weather and air quality.

    Michael's packing rules:
    - Always: toiletries, 1 underwear per day, 1 socks per day
    - Shirts: 1 per day (changes daily)
    - Pants/Shorts: Can wear for 2 days; pants if <10°C, shorts if >=10°C
    - Umbrella: Pack if rain expected on at least 1 day
    - Rain jacket: Pack if rain expected on at least 2 days
    - Jacket: Pack if below 5°C on at least 1 day
    - Winter coat: Substitute for jacket if below 0°C on at least 2 days
    - Masks: 1 per day with poor air quality (AQI > 100)

    Args:
        itinerary: JSON string or description of the trip with cities and dates.
                  Format: {"cities": [{"name": "Toronto", "date": "2025-01-31"}]}
                  Or: "Toronto 2025-01-31, Chicago 2025-02-01"

    Returns:
        Complete packing list with quantities and reasoning.
    """
    import re

    # Parse the itinerary
    cities_data = []

    try:
        # Try JSON format first
        if itinerary.strip().startswith("{"):
            data = json.loads(itinerary)
            cities_data = data.get("cities", [])
        else:
            # Parse natural language format
            # Handle various formats
            # "Toronto 2025-01-31, Chicago 2025-02-01"
            # "City1: Toronto 2025-01-31\nCity2: Chicago 2025-02-01"
            lines = itinerary.replace(",", "\n").strip().split("\n")

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Extract date pattern
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                if date_match:
                    date = date_match.group(1)
                    # Remove date and common prefixes to get city name
                    city_name = line.replace(date, "").strip()
                    city_name = re.sub(r'^City\d*:\s*', '', city_name, flags=re.IGNORECASE)
                    city_name = city_name.replace(" on ", " ").strip()
                    city_name = city_name.rstrip(":").strip()

                    if city_name:
                        cities_data.append({"name": city_name, "date": date})

        if not cities_data:
            return json.dumps({
                "error": "Could not parse itinerary",
                "tip": "Please provide in format: Toronto 2025-01-31, Chicago 2025-02-01",
                "currentTime": datetime.now().isoformat()
            }, indent=2)

        # Get weather and air quality for each day
        daily_conditions = []
        num_days = len(cities_data)

        for city_info in cities_data:
            city = city_info.get("name", "Unknown")
            date = city_info.get("date", "Unknown")

            weather = get_weather_data_for_packing(city, date)
            air_quality = get_air_quality_for_packing(city, date)

            daily_conditions.append({
                "city": city,
                "date": date,
                "avg_temp": weather.get("avg_temp", 10),
                "temp_min": weather.get("temp_min", 5),
                "will_rain": weather.get("will_rain", False),
                "precipitation_prob": weather.get("precipitation_probability", 0),
                "mask_needed": air_quality.get("mask_needed", False),
                "aqi": air_quality.get("avg_aqi", 50)
            })

        # Apply Michael's packing rules

        # Count conditions
        days_below_0 = sum(1 for d in daily_conditions if d["temp_min"] < 0)
        days_below_5 = sum(1 for d in daily_conditions if d["temp_min"] < 5)
        days_below_10 = sum(1 for d in daily_conditions if d["avg_temp"] < 10)
        days_above_10 = sum(1 for d in daily_conditions if d["avg_temp"] >= 10)
        rainy_days = sum(1 for d in daily_conditions if d["will_rain"])
        mask_days = sum(1 for d in daily_conditions if d["mask_needed"])

        # Build packing list
        packing_list = {
            "essentials": [],
            "clothing": [],
            "outerwear": [],
            "accessories": [],
            "health_safety": []
        }

        # ESSENTIALS (always pack)
        packing_list["essentials"].append({
            "item": "Toiletries kit",
            "quantity": 1,
            "reason": "Always packed"
        })

        # UNDERWEAR & SOCKS (1 per day)
        packing_list["clothing"].append({
            "item": "Underwear",
            "quantity": num_days,
            "reason": f"1 per day × {num_days} days"
        })
        packing_list["clothing"].append({
            "item": "Socks (pairs)",
            "quantity": num_days,
            "reason": f"1 pair per day × {num_days} days"
        })

        # SHIRTS (1 per day, changes daily)
        # Long shirts for cold days, t-shirts for warm days
        long_shirts = days_below_10
        tshirts = days_above_10

        if long_shirts > 0:
            packing_list["clothing"].append({
                "item": "Long-sleeve shirts",
                "quantity": long_shirts,
                "reason": f"1 per day when temp < 10°C ({long_shirts} days)"
            })
        if tshirts > 0:
            packing_list["clothing"].append({
                "item": "T-shirts",
                "quantity": tshirts,
                "reason": f"1 per day when temp >= 10°C ({tshirts} days)"
            })

        # PANTS/SHORTS (can wear for 2 days)
        # Pants for cold days, shorts for warm days
        pants_needed = math.ceil(days_below_10 / 2) if days_below_10 > 0 else 0
        shorts_needed = math.ceil(days_above_10 / 2) if days_above_10 > 0 else 0

        if pants_needed > 0:
            packing_list["clothing"].append({
                "item": "Pants/Trousers",
                "quantity": pants_needed,
                "reason": f"Can wear 2 days each; {days_below_10} cold days ÷ 2 = {pants_needed}"
            })
        if shorts_needed > 0:
            packing_list["clothing"].append({
                "item": "Shorts",
                "quantity": shorts_needed,
                "reason": f"Can wear 2 days each; {days_above_10} warm days ÷ 2 = {shorts_needed}"
            })

        # OUTERWEAR
        # Winter coat if below 0°C on at least 2 days (substitutes jacket)
        # Jacket if below 5°C on at least 1 day (but not if packing winter coat)
        if days_below_0 >= 2:
            packing_list["outerwear"].append({
                "item": "Winter coat",
                "quantity": 1,
                "reason": f"Below 0°C on {days_below_0} days (≥2 days threshold)"
            })
        elif days_below_5 >= 1:
            packing_list["outerwear"].append({
                "item": "Jacket",
                "quantity": 1,
                "reason": f"Below 5°C on {days_below_5} day(s)"
            })

        # Umbrella if rain on at least 1 day
        if rainy_days >= 1:
            packing_list["accessories"].append({
                "item": "Umbrella",
                "quantity": 1,
                "reason": f"Rain expected on {rainy_days} day(s) (>30% precipitation probability)"
            })

        # Rain jacket if rain on at least 2 days
        if rainy_days >= 2:
            packing_list["accessories"].append({
                "item": "Rain jacket",
                "quantity": 1,
                "reason": f"Rain expected on {rainy_days} days (≥2 days threshold)"
            })

        # MASKS (1 per day with poor air quality)
        if mask_days > 0:
            packing_list["health_safety"].append({
                "item": "Face masks",
                "quantity": mask_days,
                "reason": f"1 per day with AQI > 100 ({mask_days} days)"
            })

        # Build daily weather summary
        daily_summary = []
        for d in daily_conditions:
            summary = {
                "date": d["date"],
                "city": d["city"],
                "temperature": f"{d['avg_temp']:.1f}°C avg (min: {d['temp_min']:.1f}°C)",
                "clothing_type": "Pants + Long shirt" if d["avg_temp"] < 10 else "Shorts + T-shirt",
                "rain_expected": "Yes" if d["will_rain"] else "No",
                "air_quality": f"AQI {d['aqi']}" + (" - Mask needed" if d["mask_needed"] else " - Good")
            }
            daily_summary.append(summary)

        # Calculate totals
        total_items = sum(
            item["quantity"]
            for category in packing_list.values()
            for item in category
        )

        # Format the final packing list
        formatted_list = {}
        for category, items in packing_list.items():
            if items:
                formatted_list[category.replace("_", " ").title()] = [
                    {
                        "item": item["item"],
                        "quantity": item["quantity"],
                        "reason": item["reason"]
                    }
                    for item in items
                ]

        return json.dumps({
            "packing_list": {
                "title": "Michael's Packing List",
                "trip_duration": f"{num_days} day(s)",
                "categories": formatted_list,
                "total_items": total_items
            },
            "weather_summary": {
                "daily_conditions": daily_summary,
                "cold_days_below_10C": days_below_10,
                "warm_days_above_10C": days_above_10,
                "days_below_5C": days_below_5,
                "days_below_0C": days_below_0,
                "rainy_days": rainy_days,
                "poor_air_quality_days": mask_days
            },
            "packing_rules_applied": {
                "underwear_socks": "1 per day",
                "shirts": "1 per day (long-sleeve if <10°C, t-shirt if >=10°C)",
                "pants_shorts": "1 per 2 days (pants if <10°C, shorts if >=10°C)",
                "umbrella": "Pack if rain on ≥1 day",
                "rain_jacket": "Pack if rain on ≥2 days",
                "jacket": "Pack if <5°C on ≥1 day",
                "winter_coat": "Substitutes jacket if <0°C on ≥2 days",
                "masks": "1 per day with AQI >100"
            },
            "currentTime": datetime.now().isoformat()
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Error generating packing list: {str(e)}",
            "tip": "Please provide itinerary with cities and dates",
            "currentTime": datetime.now().isoformat()
        }, indent=2)


# Export all tools for easy import
ALL_TOOLS = [
    get_weather_forecast,
    get_air_quality_forecast,
    get_tourist_attractions,
    get_place_address,
    check_attraction_availability,
    calculate_total_masks,
    get_restaurant_recommendations,
    get_hotel_recommendation,
    calculate_trip_budget,
    generate_packing_list
]
