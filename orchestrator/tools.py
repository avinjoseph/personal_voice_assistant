import requests
import json
import os
import logging
from datetime import datetime, timedelta

# --- Configuration ---
WEATHER_URL = "https://api.responsible-nlp.net/weather.php"
CALENDAR_URL = "https://api.responsible-nlp.net/calendar.php"

# IMPORTANT: Ensure this ID matches your team ID
TEAM_CALENDAR_ID = os.getenv("TEAM_CALENDAR_ID", "3864546")

# Setup dedicated logger
calendar_logger = logging.getLogger('calendar_logger')
calendar_logger.setLevel(logging.INFO)
if not calendar_logger.handlers:
    file_handler = logging.FileHandler('calendar_api.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    calendar_logger.addHandler(file_handler)

def get_weather(city: str):
    """
    Fetches weather and converts the 7-day JSON forecast into a readable string.
    """
    try:
        # Weather API expects 'place' in body and 'apikey'
        response = requests.post(WEATHER_URL, data={"place": city, "apikey": TEAM_CALENDAR_ID})
        
        if response.status_code != 200:
            return f"Error: Weather API returned {response.status_code}"
        
        data = response.json()
        
        if "forecast" not in data:
            return f"Weather data found for {city}, but format is unexpected."

        report_lines = [f"Weather in {data.get('place', city)}:"]
        
        # Limit to 2 days for brevity in voice response
        for day in data["forecast"][:2]:
            day_name = day.get("day", "Unknown")
            weather_desc = day.get("weather", "unknown")
            t_max = day.get("temperature", {}).get("max", "?")
            line = f"{day_name}: {weather_desc}, High {t_max}°C."
            report_lines.append(line)

        return " ".join(report_lines)

    except Exception as e:
        return f"Error connecting to Weather API: {str(e)}"

def manage_calendar(action: str, event_id: int = None, title: str = None, 
                    start_time: str = None, end_time: str = None, 
                    location: str = None, description: str = None):
    """
    Handles Calendar API interactions (List, Create, Delete).
    """
    try:
        calendar_logger.info(f"Action: {action} | Title: {title} | Start: {start_time}")
        
        base_params = {"calenderid": TEAM_CALENDAR_ID}
        headers = {"Content-Type": "application/json"}

        # 1. LIST APPOINTMENTS
        if action == "list":
            res = requests.get(CALENDAR_URL, params=base_params)
            try:
                events = res.json()
                if not events:
                    return "You have no appointments scheduled."
                
                # Format list for the LLM to read easily
                summary = []
                for e in events:
                    # Handle potentially missing keys safely
                    e_id = e.get('id', 'N/A')
                    e_title = e.get('title', 'Untitled')
                    e_start = e.get('start_time', 'No time')
                    summary.append(f"[ID {e_id}] {e_title} at {e_start}")
                
                return ". ".join(summary)
            except:
                return f"Failed to list appointments. Response: {res.text}"

        # 2. CREATE APPOINTMENT
        elif action == "create":
            if not title: title = "New Meeting"
            if not location: location = "TBD"
            if not description: description = "Voice Entry"
            
            # Default to current time + 1 hour if not provided
            if not start_time:
                now = datetime.now()
                start_time = now.isoformat(timespec='minutes')
                end_time = (now + timedelta(hours=1)).isoformat(timespec='minutes')
            elif start_time and not end_time:
                 # Try to parse start time and add 1 hour
                 try:
                     dt_start = datetime.fromisoformat(start_time.replace(" ", "T"))
                     end_time = (dt_start + timedelta(hours=1)).isoformat(timespec='minutes')
                 except:
                     # Fallback if parsing fails, let API handle it or use default
                     end_time = start_time 

            payload = {
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "location": location,
                "description": description
            }
            # Clean payload
            payload = {k: v for k, v in payload.items() if v is not None}

            res = requests.post(CALENDAR_URL, params=base_params, headers=headers, json=payload)
            
            if res.status_code in [200, 201]:
                return f"Successfully created appointment: '{title}'."
            else:
                return f"Error creating event: {res.text}"
        elif action == "update":
            if not event_id: 
                return "I need an Appointment ID to update it."
            
            # Only include fields that are actually provided
            payload = {
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "location": location,
                "description": description
            }
            # Remove None values so we don't overwrite existing data with nulls
            payload = {k: v for k, v in payload.items() if v is not None}
            
            if not payload:
                return "You didn't tell me what to update."

            update_params = base_params.copy()
            update_params["id"] = event_id
            
            # Use PUT to update
            res = requests.put(CALENDAR_URL, params=update_params, headers=headers, json=payload)
            calendar_logger.info(f"Calendar Update Response: {res.text}")
            
            if res.status_code == 200:
                return f"Successfully updated appointment ID {event_id}."
            else:
                return f"Failed to update. API Error: {res.text}"
        # 3. DELETE APPOINTMENT
        elif action == "delete":
            # If no ID provided, try to find the last created event
            if not event_id:
                # Get list first
                list_res = requests.get(CALENDAR_URL, params=base_params)
                try:
                    events = list_res.json()
                    if not events:
                        return "Calendar is already empty."
                    # Assume last item is most recent (or first, depending on API sort, let's try last)
                    last_event = events[-1] 
                    event_id = last_event.get('id')
                    title_to_delete = last_event.get('title', 'Unknown')
                except:
                     return "Could not retrieve list to identify appointment to delete."
            else:
                title_to_delete = f"ID {event_id}"

            delete_params = base_params.copy()
            delete_params["id"] = event_id
            
            res = requests.delete(CALENDAR_URL, params=delete_params)
            
            if res.status_code == 200:
                return f"Deleted appointment: {title_to_delete}."
            else:
                return f"Failed to delete. {res.text}"

        return "Unknown calendar action."

    except Exception as e:
        calendar_logger.error(f"System Error: {str(e)}")
        return f"System Error: {str(e)}"