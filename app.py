import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from dotenv import load_dotenv
from dateutil import parser

load_dotenv()
app = Flask(__name__)
API_KEY = os.getenv("API_KEY")  # Ensure API key is kept secure

@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json()
    intent_name = req.get("queryResult", {}).get("intent", {}).get("displayName")
    parameters = req.get("queryResult", {}).get("parameters", {})
    
    # Handle different intents
    if intent_name == "Greetings":
        return jsonify({"fulfillmentText": "Hello! This is Weather Bot. How may I help you?"})
    
    if intent_name == "Goodbye":
        return jsonify({"fulfillmentText": "Thank you for contacting me. Goodbye!"})
    
    if intent_name == "GetCurrentWeather":
        city = parameters.get("geo-city")
        if not city:
            return jsonify({"fulfillmentText": "Please provide your city."})
        return get_weather_info(city, is_current=True)
    
    if intent_name == "GetWeatherForecast":
        city = parameters.get("geo-city")
        date = parameters.get("date-time")
        if not city or not date:
            return jsonify({"fulfillmentText": "Please provide both the city and the date for the forecast."})
        return get_weather_info(city, date=date)
    
    return jsonify({"fulfillmentText": "I'm sorry, I didn't understand that. How may I assist you?"})

def get_weather_info(city, date=None, is_current=False):
    try:
        # Use current weather API for current conditions
        if is_current:
            current_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
            response = requests.get(current_url).json()
            
            if response.get("cod") == 200:
                current_weather = {
                    "temp": response["main"].get("temp", "N/A"),
                    "description": response["weather"][0].get("description", "N/A"),
                    "humidity": response["main"].get("humidity", "N/A"),
                    "wind_speed": response["wind"].get("speed", "N/A")
                }
                return jsonify({
                    "fulfillmentText": f"The current weather for {city} is {current_weather['description']} with a temperature of {current_weather['temp']}°C, humidity {current_weather['humidity']}%, and wind speed {current_weather['wind_speed']} m/s."
                })
            else:
                return jsonify({"fulfillmentText": f"Sorry, I couldn't fetch the current weather for {city}."})
        
        # Use forecast API for future dates
        if date:
            try:
                target_date = parser.parse(date, fuzzy=False).date()
            except (ValueError, TypeError):
                return jsonify({"fulfillmentText": "Invalid date format. Please provide a valid date."})

            forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
            response = requests.get(forecast_url).json()

            if response.get("cod") == "200":
                today = datetime.today().date()
                last_available_date = today + timedelta(days=5)  # OpenWeatherMap provides up to 5 days of forecasts
                
                if target_date > last_available_date:
                    return jsonify({"fulfillmentText": f"Sorry, I can only provide forecasts up to {last_available_date.strftime('%A, %d %B %Y')}."})

                # Find the closest forecast to the target date
                closest_forecast = min(
                    response.get("list", []),
                    key=lambda entry: abs(datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S").date() - target_date)
                )

                forecast = {
                    "temp": closest_forecast["main"].get("temp", "N/A"),
                    "description": closest_forecast["weather"][0].get("description", "N/A"),
                    "humidity": closest_forecast["main"].get("humidity", "N/A"),
                    "wind_speed": closest_forecast["wind"].get("speed", "N/A")
                }

                return jsonify({
                    "fulfillmentText": f"The forecast for {city} on {target_date.strftime('%A, %d %B %Y')} is {forecast['description']} with a temperature of {forecast['temp']}°C, humidity {forecast['humidity']}%, and wind speed {forecast['wind_speed']} m/s."
                })
            else:
                return jsonify({"fulfillmentText": f"Sorry, I couldn't fetch the forecast for {city}."})

    except requests.exceptions.RequestException:
        return jsonify({"fulfillmentText": "Error fetching weather data. Please try again later."})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
