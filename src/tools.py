import requests
import json
import os
import logging
from datetime import datetime, timedelta

# --- Configuration ---
WEATHER_URL = "https://api.responsible-nlp.net/weather.php"
CALENDAR_URL = "https://api.responsible-nlp.net/calendar.php"

# IMPORTANT: Change this to a UNIQUE ID for your team to avoid data collisions
TEAM_CALENDAR_ID = "3864546" 

# Setup dedicated logger for calendar
calendar_logger = logging.getLogger('calendar_logger')
calendar_logger.setLevel(logging.INFO)
# Avoid adding multiple handlers if the logger is already configured
if not calendar_logger.handlers:
    file_handler = logging.FileHandler('calendar_api.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    calendar_logger.addHandler(file_handler)

def get_weather(city: str):
    """
    Fetches weather and converts the 7-day JSON forecast into a readable string summary.
    """
    try:
        # Weather API expects 'place' in the body
        # Using TEAM_CALENDAR_ID as the apikey for both tools as requested
        response = requests.post(WEATHER_URL, data={"place": city, "apikey": TEAM_CALENDAR_ID})
        
        if response.status_code != 200:
            return f"Error: Weather API returned {response.status_code}"
        
        data = response.json()
        
        if "forecast" not in data:
            return f"Weather data found for {city}, but the format is unexpected."

        report_lines = [f"Weather Forecast for {data.get('place', city)}:"]
        
        for day in data["forecast"]:
            day_name = day.get("day", "Unknown day")
            weather_desc = day.get("weather", "unknown conditions")
            temp = day.get("temperature", {})
            t_min = temp.get("min", "?")
            t_max = temp.get("max", "?")
            
            line = f"- {day_name.capitalize()}: {weather_desc}, High {t_max}°C, Low {t_min}°C."
            report_lines.append(line)

        return "\n".join(report_lines)

    except Exception as e:
        return f"Error connecting to Weather API: {str(e)}"

def manage_calendar(action: str, event_id: int = None, title: str = None, 
                   start_time: str = None, end_time: str = None, 
                   location: str = None, description: str = None):
    """
    Handles Calendar API interactions with robust defaults and error handling.
    """
    try:
        calendar_logger.info(f"Calendar Action: {action} | Params: ID={event_id}, Title={title}, Start={start_time}, End={end_time}, Loc={location}")
        
        headers = {"Content-Type": "application/json"}
        # Ensure the required parameter is sent with every request
        base_params = {"calenderid": TEAM_CALENDAR_ID}

        # 1. LIST ALL (GET)
        if action == "list":
            res = requests.get(CALENDAR_URL, params=base_params)
            calendar_logger.info(f"Calendar List Response: {res.text[:200]}...") # Log first 200 chars
            try:
                return res.json()
            except:
                return f"List failed. Raw response: {res.text}"

        # 2. READ SINGLE (GET)
        elif action == "read":
            if not event_id: return "Error: Missing event_id for read."
            read_params = base_params.copy()
            read_params["id"] = event_id
            res = requests.get(CALENDAR_URL, params=read_params)
            calendar_logger.info(f"Calendar Read Response: {res.text[:200]}...") # Log first 200 chars
            try:
                return res.json()
            except:
                return res.text

        # 3. CREATE (POST)
        elif action == "create":
            # --- ROBUSTNESS FIX: Handle missing required fields ---
            if not title: title = "New Meeting"
            if not location: location = "TBD"
            if not description: description = "Scheduled via Voice Assistant"
            
            # Auto-calculate end_time if missing (Default to 1 hour)
            if start_time and not end_time:
                try:
                    # Parse start_time (Handle 'T' separator or space)
                    clean_start = start_time.replace(" ", "T")
                    dt_start = datetime.fromisoformat(clean_start)
                    dt_end = dt_start + timedelta(hours=1)
                    # Format back to ISO format required by API
                    end_time = dt_end.isoformat(timespec='minutes')
                    # Ensure start_time is also strictly formatted
                    start_time = dt_start.isoformat(timespec='minutes')
                except ValueError:
                    # If parsing fails, pass it through as-is and let API decide
                    pass

            payload = {
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "location": location,
                "description": description
            }
            # Clean payload
            payload = {k: v for k, v in payload.items() if v is not None}
            
            # Log for debugging
            print(f"[DEBUG] Creating Event with Payload: {payload}")

            res = requests.post(CALENDAR_URL, params=base_params, headers=headers, json=payload)
            calendar_logger.info(f"Calendar Create Response: {res.text}")
            
            if res.status_code in [200, 201]:
                return f"Success: {res.text}"
            else:
                return f"Error creating event. API Status: {res.status_code}, Response: {res.text}"

        # 4. UPDATE (PUT)
        elif action == "update":
            if not event_id: return "Error: Missing event_id for update."
            
            payload = {
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "location": location,
                "description": description
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            
            update_params = base_params.copy()
            update_params["id"] = event_id
            
            res = requests.put(CALENDAR_URL, params=update_params, headers=headers, json=payload)
            calendar_logger.info(f"Calendar Update Response: {res.text}")
            return f"Update result: {res.text}"

        # 5. DELETE (DELETE)
        elif action == "delete":
            if not event_id: return "Error: Missing event_id for delete."
            
            delete_params = base_params.copy()
            delete_params["id"] = event_id
            
            res = requests.delete(CALENDAR_URL, params=delete_params)
            calendar_logger.info(f"Calendar Delete Response: {res.text}")
            return f"Delete result: {res.text}"
            
        return "Error: Invalid action specified."

    except Exception as e:
        calendar_logger.error(f"Calendar API Error: {str(e)}")
        return f"System Error in manage_calendar: {str(e)}"