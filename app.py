import os 
from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from dateutil import parser 


load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")#i have ecrypted my api key

@app.route("/", methods=["GET"])
def home():
    return "Webhook is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json()
    intent_name = req.get("queryResult", {}).get("intent", {}).get("displayName")
    parameters = req.get("queryResult", {}).get("parameters", {})
    city = parameters.get("geo-city")
    date = parameters.get("date-time")
    date_period = parameters.get("date-period")
    
    
    if not date and date_period:
        date = date_period.get("startDate")
    
    
    if not date:
        date = datetime.today().strftime("%Y-%m-%d")
    
    
    if intent_name == "SetUserCity":
        if city:
            return jsonify({
                "fulfillmentText": f"Got it! Your location is set to {city}. What would you like to know?",
                "outputContexts": [
                    {
                        "name": req["session"] + "/contexts/user_location",
                        "lifespanCount": 10,
                        "parameters": {"geo-city": city}
                    }
                ]
            })
        else:
            return jsonify({"fulfillmentText": "Which city are you setting as your location?"})

    
    if not city:
        output_contexts = req.get("queryResult", {}).get("outputContexts", [])
        for context in output_contexts:
            parameters = context.get("parameters", {})
            if parameters.get("geo-city"):
                city = parameters["geo-city"]
                break  # Stop searching once the city is found

    
    if not city:
        return jsonify({"fulfillmentText": "I need a city to check the weather. Which city are you asking about?"})

    return get_weather_forecast(city, date)


def get_weather_forecast(city, date):
    if date:
        try:
            target_date = parser.parse(date).date()
        except Exception as e:
            print(f"Date parsing error: {e}")
            return jsonify({"fulfillmentText": "I couldn't understand the date. Please try again."})
    else:
        target_date = datetime.today().date()

    print(f"Final target date for forecast: {target_date}")

    forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(forecast_url).json()
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return jsonify({"fulfillmentText": "Error fetching weather data. Please try again later."})
    
    if "list" not in response:
        return jsonify({"fulfillmentText": "Sorry, I couldn't fetch the weather forecast."})

    today = datetime.today().date()
    last_available_date = today + timedelta(days=5)

    if target_date > last_available_date:
        return jsonify({"fulfillmentText": f"Sorry, I can only provide forecasts up to {last_available_date.strftime('%A, %d %B %Y')}."})

    daily_forecasts = {}
    print("Available forecast dates from OpenWeather API:")

    for entry in response.get("list", []):
        forecast_time = datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S")
        forecast_date = forecast_time.date()
        print(forecast_date)

        if forecast_date == target_date:
            daily_forecasts[forecast_date] = {
                "temp": entry["main"].get("temp", "N/A"),
                "description": entry["weather"][0].get("description", "N/A"),
                "humidity": entry["main"].get("humidity", "N/A"),
                "wind_speed": entry["wind"].get("speed", "N/A"),
                "pressure": entry["main"].get("pressure", "N/A")
            }

    if target_date in daily_forecasts:
        forecast = daily_forecasts[target_date]
        response_text = (
            f"The weather forecast for {city} on {target_date.strftime('%A, %d %B %Y')} is {forecast['description']} with a "
            f"temperature of {forecast['temp']}°C, humidity of {forecast['humidity']}%, wind speed of {forecast['wind_speed']} m/s, "
            f"and pressure of {forecast['pressure']} hPa."
        )
    else:
        response_text = f"No forecast available for {target_date.strftime('%A, %d %B %Y')}."

    return jsonify({"fulfillmentText": response_text})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
