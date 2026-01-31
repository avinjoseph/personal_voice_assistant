import requests
import json
import os
import logging
from datetime import datetime, timedelta

# --- Configuration ---
WEATHER_URL = "https://api.responsible-nlp.net/weather.php"
CALENDAR_URL = "https://api.responsible-nlp.net/calendar.php"
TEAM_CALENDAR_ID = os.getenv("TEAM_CALENDAR_ID", "3864546")

# --- Logger Setup ---
# This ensures logs appear in your Docker console
logger = logging.getLogger("tools")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - [TOOLS] - %(levelname)s - %(message)s'))
if not logger.handlers:
    logger.addHandler(handler)

def format_weather_response(data, user_text):
    """Deterministic mapping of API JSON to Speech."""
    if not isinstance(data, dict):
        return "I'm sorry, I couldn't retrieve the weather data right now."

    place = data.get("place", "the requested location").replace("&#039;", "'")
    forecast = data.get("forecast", [])
    
    # Resolve 'today' to the actual current weekday (e.g., 'Saturday')
    current_day = datetime.now().strftime('%A').lower()
    
    user_lower = user_text.lower()
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    
    # Priority: 1. Specific day mentioned, 2. 'Today' resolved to weekday
    target_day = next((d for d in days if d in user_lower), current_day)
    
    day_info = next((d for d in forecast if d['day'].lower() == target_day), None)
    
    if not day_info:
        return f"I couldn't find the forecast for {target_day.capitalize()} in {place}."

    condition = day_info.get("weather", "clear sky")
    high = day_info.get("temperature", {}).get("max", "?")
    low = day_info.get("temperature", {}).get("min", "?")

    return f"Weather for {place} on {target_day.capitalize()}: expect {condition} with a high of {high} degrees and a low of {low}."

def get_weather(city: str, user_text: str = ""):
    """
    Fetches 7-day forecast and dynamically maps 'today' or 'tomorrow' 
    to the correct weekday name for the API response.
    """
    try:
        # Clean city name (remove potential LLM artifacts like quotes)
        city = city.strip("'").strip('"')
        
        # 1. Call API (No API Key required per requirements)
        response = requests.post(WEATHER_URL, data={"place": city})
        if response.status_code != 200:
            return "I couldn't connect to the weather service."

        data = response.json()
        forecasts = data.get("forecast", [])
        if not forecasts:
            return f"I couldn't find weather data for {city}."

        # 2. Dynamic Day Resolution
        user_lower = user_text.lower()
        days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        
        # Get the actual name of today (e.g., 'saturday')
        current_day_name = datetime.now().strftime("%A").lower()
        
        # Determine Target Day
        if "tomorrow" in user_lower:
            target_day = (datetime.now() + timedelta(days=1)).strftime("%A").lower()
        else:
            # Check if a specific day name was mentioned
            target_day = next((d for d in days_of_week if d in user_lower), current_day_name)

        # 3. Find matching forecast
        # We search the 7-day forecast for the resolved target_day
        selected = next((f for f in forecasts if f.get("day", "").lower() == target_day), forecasts[0])
        
        # 4. Construct Response
        condition = selected.get("weather", "unknown conditions")
        temp = selected.get("temperature", {})
        t_min = temp.get("min", "?")
        t_max = temp.get("max", "?")
        place_name = data.get("place", city).replace("&#039;", "'") # Clean HTML entities

        return (f"Weather for {place_name}: On {target_day.capitalize()}, "
                f"expect {condition} with a high of {t_max} degrees and a low of {t_min} degrees.")

    except Exception as e:
        return "There was an error processing the weather data."

def manage_calendar(action: str, event_id: int = None,is_next_query: bool = False, **kwargs):
    base_params = {"calenderid": TEAM_CALENDAR_ID}
    headers = {"Content-Type": "application/json"}

    # REQUIREMENT: Resolve 'latest' appointment if ID is missing (Slide 134, 135)
    if action in ["delete", "update", "remove", "change"] and not event_id:
        list_res = requests.get(CALENDAR_URL, params=base_params)
        try:
            events = list_res.json()
            if events:
                # Sort by ID to find the highest (latest) one
                latest_event = max(events, key=lambda x: x['id'])
                event_id = latest_event['id']
                logger.info(f"Resolved latest ID for {action}: {event_id}")
            else:
                return "Your calendar is empty, nothing to modify."
        except:
            return "Could not retrieve list to identify the latest appointment."

    # 1. CREATE (POST) - Slide 95
    if action in ["add", "create"]:
        payload = {
            "title": kwargs.get("title") or "New Meeting",
            "description": "Voice Assistant Entry",
            "start_time": kwargs.get("start_time"),
            "end_time": kwargs.get("end_time") or kwargs.get("start_time"),
            "location": kwargs.get("location") or "TBD"
            
        }
        res = requests.post(CALENDAR_URL, params={"calenderid": TEAM_CALENDAR_ID}, 
                        headers={"Content-Type": "application/json"}, 
                        json=payload)       
        if res.status_code in [200, 201]:
            new_id = res.json().get('id', 'unknown')
            return f"Successfully created appointment '{payload['title']}' with ID {new_id}."
        return f"Error creating event: {res.text}"

    # # 2. UPDATE (PUT) - Slide 113
    # elif "update" in action or "change" in action:
    #     update_params = {**base_params, "id": event_id}
    #     payload = {k: v for k, v in kwargs.items() if v is not None}
    #     res = requests.put(CALENDAR_URL, params=update_params, headers=headers, json=payload)
    #     return f"Updated appointment ID {event_id}." if res.status_code == 200 else f"Update failed: {res.text}"

    # # 3. DELETE (DELETE) - Slide 121
    # elif "delete" in action:
    #     res = requests.delete(CALENDAR_URL, params={**base_params, "id": event_id})
    #     return f"Deleted appointment ID {event_id}." if res.status_code == 200 else f"Delete failed: {res.text}"

    if action == "delete":
        res = requests.delete(CALENDAR_URL, params={**base_params, "id": event_id})
        return f"Deleted appointment ID {event_id}." if res.status_code == 200 else "Delete failed."
    
    elif action == "update":
        payload = {k: v for k, v in kwargs.items() if v and k in ["title", "start_time", "location", "description"]}
        res = requests.put(CALENDAR_URL, params={**base_params, "id": event_id}, json=payload)
        return f"Updated appointment ID {event_id}." if res.status_code == 200 else "Update failed."

    if action == "list":
        res = requests.get(CALENDAR_URL, params=base_params)
        events = res.json()
        if not events: 
            return "You have no appointments scheduled."
        
        # Requirement: "Where is my next appointment?" -> Get smallest ID
        if is_next_query:
            # Finding the smallest ID as requested
            next_event = min(events, key=lambda x: x['id'])
            # Fetch single detail (GET with ID) as per Requirement 109
            detail_res = requests.get(CALENDAR_URL, params={**base_params, "id": next_event['id']})
            e = detail_res.json()
            return f"Your next appointment is {e.get('title')} on {e.get('start_time','').replace('T',' at ')}."

        # Standard List logic (Requirement 103)
        summary = [f"[ID {e.get('id')}] {e.get('title')} on {e.get('start_time','').replace('T',' at ')}" for e in events]
        return "Your schedule: " + ". ".join(summary)

    return "Unknown calendar action."