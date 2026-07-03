import os
import json
import uuid
import datetime
import base64
import io
import requests
from flask import Flask, render_template, request, jsonify, send_file
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image

# Load environment variables from .env using absolute path
dotenv_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

# ReportLab imports for PDF generation
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

app = Flask(__name__)

# Initialize GenAI Client
# If GEMINI_API_KEY is not set in environment, check for GOOGLE_API_KEY.
api_key = os.environ.get("GEMINI_API_KEY")
client = None
if api_key:
    client = genai.Client(api_key=api_key)
elif os.environ.get("GOOGLE_API_KEY"):
    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

# Pydantic schema for structured output from Gemini
class CropDiagnosis(BaseModel):
    is_ambiguous: bool = Field(
        description="True if the user's input is too vague or ambiguous to make a diagnosis. False otherwise."
    )
    clarifying_question: Optional[str] = Field(
        default=None,
        description="If is_ambiguous is True, provide ONE simple, friendly clarifying question. Otherwise, None."
    )
    is_healthy: bool = Field(
        description="True if the crop is described as healthy or normal with no issues. False otherwise."
    )
    crop: Optional[str] = Field(
        default=None,
        description="The name of the crop (e.g., Cotton, Rice, Tomato)."
    )
    disease_name: Optional[str] = Field(
        default=None,
        description="The name of the diagnosed crop disease. If is_healthy is True, set to 'Healthy Crop'."
    )
    cause: Optional[str] = Field(
        default=None,
        description="A 1-sentence description of the cause of the disease, or general health description if healthy."
    )
    immediate_action_steps: List[str] = Field(
        default_factory=list,
        description="Exactly 3 simple, bulleted action steps for immediate treatment or containment, or general care steps if healthy."
    )
    prevention_tips: List[str] = Field(
        default_factory=list,
        description="Exactly 2 simple, bulleted tips for prevention of the disease, or general maintenance if healthy."
    )
    severity: str = Field(
        default="Medium",
        description="The severity level of the disease. Must be one of: 'Low', 'Medium', 'High', 'Critical'. If healthy or ambiguous, default to 'Low'."
    )
    location_city: Optional[str] = Field(
        default=None,
        description="The city, town, or district name mentioned in the user's message (e.g., 'Surat', 'Nashik'). If none is mentioned, set to None."
    )
    weather_note: Optional[str] = Field(
        default=None,
        description="If weather data is provided in [WEATHER CONTEXT], add a 1-2 sentence note explaining if these weather conditions are favorable for the disease to spread. Set to None if no weather data is available."
    )
    helpline: str = Field(
        default="Kisan Call Center: 1800-180-1551",
        description="The Kisan helpline number, which must be: Kisan Call Center: 1800-180-1551"
    )

class HindiTranslationResponse(BaseModel):
    disease_name: str = Field(description="The Hindi translation of the disease name.")
    cause: str = Field(description="The Hindi translation of the cause.")
    immediate_action_steps: List[str] = Field(description="The Hindi translation of the 3 immediate action steps.")
    prevention_tips: List[str] = Field(description="The Hindi translation of the 2 prevention tips.")
    weather_note: Optional[str] = Field(default=None, description="The Hindi translation of the weather note, if any.")

SYSTEM_INSTRUCTION = """
You are SmartFarm, an AI crop advisory agent built for Indian farmers. Your job is to diagnose crop diseases and give clear, actionable advice.

Analyze the farmer's input (which may include a crop photo and text description) and follow these rules:
1. Extract the crop type, symptoms, location, and season from the message.
2. Formulate a diagnosis of the most likely crop disease based on the combination of crop and symptoms (and visual details from the image if uploaded).
3. If the input is too vague or ambiguous (e.g., "help me", "my crop is sick"), set is_ambiguous to True and provide ONE clear, friendly clarifying question.
4. If the crop is described as healthy, set is_healthy to True and provide general crop maintenance tips.
5. Otherwise (successful diagnosis):
   - Set is_ambiguous to False and is_healthy to False.
   - Set crop to the name of the crop.
   - Set disease_name to the likely disease.
   - Set cause to exactly 1 sentence explaining the cause of the disease.
   - Set immediate_action_steps to EXACTLY 3 bullet steps for treatment or containment. Keep language simple.
   - Set prevention_tips to EXACTLY 2 bullet steps for preventing the disease in the future. Keep language simple.
   - Set severity to one of: 'Low', 'Medium', 'High', 'Critical'. Be realistic based on the impact of the disease.
   - Set helpline to 'Kisan Call Center: 1800-180-1551'.

If [WEATHER CONTEXT] is provided in the input, analyze if the current temperature, humidity, and precipitation levels are favorable for the disease to spread. Add a weather note explaining this clearly in 1-2 sentences.

Always use simple, friendly, and non-technical language that is easy for a farmer to understand. Always include the Kisan Call Center helpline number.
"""

# History helpers
def read_history():
    history_path = os.path.join(app.root_path, 'history.json')
    if not os.path.exists(history_path):
        return []
    try:
        with open(history_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def write_history(data):
    history_path = os.path.join(app.root_path, 'history.json')
    try:
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error writing history: {e}")

@app.route("/")
def index():
    has_api_key = client is not None
    return render_template("index.html", has_api_key=has_api_key)

@app.route("/history", methods=["GET"])
def get_history():
    history = read_history()
    # return only last 5 to the client
    return jsonify(history[:5])

def fetch_weather_openmeteo(city):
    try:
        # 1. Geocode
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_resp = requests.get(geo_url, params={"name": city, "count": 1}, timeout=5)
        geo_data = geo_resp.json()
        
        if "results" in geo_data and geo_data["results"]:
            loc = geo_data["results"][0]
            lat = loc["latitude"]
            lon = loc["longitude"]
            resolved_city = loc["name"]
            
            # 2. Forecast weather
            weather_url = "https://api.open-meteo.com/v1/forecast"
            weather_params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "hourly": "relativehumidity_2m",
                "timezone": "Asia/Kolkata"
            }
            w_resp = requests.get(weather_url, params=weather_params, timeout=5)
            w_data = w_resp.json()
            
            # Extract temperature
            current_weather = w_data.get("current_weather", {})
            temp = current_weather.get("temperature")
            cw_time = current_weather.get("time") # e.g. '2026-06-27T19:00'
            
            # Extract humidity from hourly relativehumidity_2m
            hourly = w_data.get("hourly", {})
            hourly_times = hourly.get("time", [])
            hourly_humidities = hourly.get("relativehumidity_2m", [])
            
            humidity = 60 # fallback default
            if cw_time in hourly_times:
                idx = hourly_times.index(cw_time)
                humidity = hourly_humidities[idx]
            else:
                now_hour = datetime.datetime.now().strftime("%Y-%m-%dT%H:00")
                if now_hour in hourly_times:
                    idx = hourly_times.index(now_hour)
                    humidity = hourly_humidities[idx]
                elif hourly_humidities:
                    humidity = hourly_humidities[0]
            
            # Map weathercode to description
            weathercode = current_weather.get("weathercode", 0)
            desc_map = {
                0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
                55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
                80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
                95: "Thunderstorm"
            }
            description = desc_map.get(weathercode, "Clear")
            wind_speed = current_weather.get("windspeed", 0.0)
            
            return {
                "city": resolved_city,
                "temp": temp,
                "humidity": humidity,
                "precipitation": 0.0,
                "description": description,
                "wind_speed": wind_speed,
                "source": "Open-Meteo"
            }
    except Exception as e:
        print(f"Error fetching Open-Meteo weather for {city}: {e}")
    return None

def fetch_weather_openweathermap(city):
    key = os.environ.get("OPENWEATHER_API_KEY") or os.environ.get("OPENWEATHERMAP_API_KEY")
    if not key:
        return None
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            w_data = resp.json()
            main = w_data.get("main", {})
            wind = w_data.get("wind", {})
            weather_list = w_data.get("weather", [])
            description = weather_list[0].get("description", "Clear") if weather_list else "Clear"
            
            rain = w_data.get("rain", {})
            precipitation = rain.get("1h", 0.0) or rain.get("3h", 0.0) or 0.0
            
            return {
                "city": w_data.get("name", city),
                "temp": main.get("temp"),
                "humidity": main.get("humidity"),
                "precipitation": precipitation,
                "description": description.capitalize(),
                "wind_speed": wind.get("speed", 0.0),
                "source": "OpenWeatherMap"
            }
    except Exception as e:
        print(f"Error fetching OpenWeatherMap weather for {city}: {e}")
    return None

def fetch_weather_data(city):
    # Rule 3: Open-Meteo is the PRIMARY source
    weather_data = fetch_weather_openmeteo(city)
    if weather_data:
        return weather_data
    # Fallback to OpenWeatherMap
    return fetch_weather_openweathermap(city)

@app.route("/weather", methods=["POST"])
def get_weather_route():
    data = request.get_json() or {}
    problem_desc = data.get("problem_description", "").strip()
    
    if not problem_desc:
        return jsonify({"error": "No description provided."}), 400
        
    city = None
    if client:
        try:
            extract_resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Extract only the city, district, or town name from this text: '{problem_desc}'. Return a single word or null. Do not write anything else.",
                config=types.GenerateContentConfig(temperature=0.1)
            )
            extracted = extract_resp.text.strip().replace("'", "").replace('"', '').strip()
            if extracted and extracted.lower() != "null" and len(extracted) < 30:
                city = extracted
        except Exception as e:
            print(f"Error extracting city in /weather: {e}")
            
    if not city:
        import re
        matches = re.findall(r'\bin\s+([A-Za-z]+)\b', problem_desc)
        if matches:
            city = matches[0]
        else:
            matches = re.findall(r'\b([A-Za-z]+),\s+[A-Za-z]+', problem_desc)
            if matches:
                city = matches[0]
                
    if not city:
        return jsonify({"error": "Could not identify any location in the description."}), 400
        
    weather_data = fetch_weather_data(city)
    if weather_data:
        return jsonify(weather_data)
    else:
        return jsonify({"error": f"Failed to fetch weather data for city: {city}"}), 500

@app.route("/diagnose", methods=["POST"])
def diagnose():
    global client
    if client is None:
        api_key_check = os.environ.get("GEMINI_API_KEY")
        if api_key_check:
            client = genai.Client(api_key=api_key_check)
        elif os.environ.get("GOOGLE_API_KEY"):
            client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    
    if client is None:
        return jsonify({
            "error": "Gemini API key is not configured. Please set the GEMINI_API_KEY environment variable."
        }), 500

    problem_desc = request.form.get("problem_description", "").strip()
    image_file = request.files.get("image")

    if not problem_desc and not image_file:
        return jsonify({"error": "Please describe your crop problem or upload a photo."}), 400

    # 1. Step 1: Try to extract city name from description to fetch weather
    city = None
    if problem_desc:
        try:
            extract_resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Extract only the city, district, or town name from this text: '{problem_desc}'. Return a single word or null. Do not write anything else.",
                config=types.GenerateContentConfig(temperature=0.1)
            )
            extracted = extract_resp.text.strip().replace("'", "").replace('"', '').strip()
            if extracted and extracted.lower() != "null" and len(extracted) < 30:
                city = extracted
        except Exception as e:
            print(f"Error extracting city with Gemini: {e}")
        
        # Regex-based fallback to extract city name if Gemini fails or returns nothing
        if not city:
            import re
            # Match "in <City>" (e.g. "in Surat", "in Nashik")
            matches = re.findall(r'\bin\s+([A-Za-z]+)\b', problem_desc)
            if matches:
                city = matches[0]
            else:
                # Match "<City>, <State>" (e.g. "Surat, Gujarat")
                matches = re.findall(r'\b([A-Za-z]+),\s+[A-Za-z]+', problem_desc)
                if matches:
                    city = matches[0]

    # 2. Step 2: Fetch current weather for the city
    weather_data = None
    if city:
        weather_data = fetch_weather_data(city)

    # 3. Step 3: Call Gemini with text and image (multimodal)
    contents = []
    filename = None
    
    if image_file:
        try:
            # Save the image to static/uploads
            filename = f"{uuid.uuid4().hex}_{image_file.filename}"
            upload_path = os.path.join(app.root_path, 'static', 'uploads', filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            image_file.seek(0)
            image_bytes = image_file.read()
            with open(upload_path, 'wb') as f:
                f.write(image_bytes)
            
            # Pack image part for API
            img_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=image_file.content_type or "image/jpeg"
            )
            contents.append(img_part)
        except Exception as e:
            return jsonify({"error": f"Image processing failed: {str(e)}"}), 500

    prompt = problem_desc if problem_desc else "Analyze this crop photo to diagnose potential diseases."
    if weather_data:
        prompt += f"\n\n[WEATHER CONTEXT] The current weather in {weather_data['city']} is: Temperature: {weather_data['temp']}°C, Relative Humidity: {weather_data['humidity']}%, Precipitation: {weather_data['precipitation']}mm."
    
    contents.append(prompt)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=CropDiagnosis,
                temperature=0.2,
            )
        )
        
        result = json.loads(response.text)
        
        # Post-process and save to history if it's a successful diagnosis or healthy state
        if not result.get("is_ambiguous"):
            diagnosis_id = uuid.uuid4().hex
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            result['id'] = diagnosis_id
            result['timestamp'] = timestamp
            result['problem_description'] = problem_desc
            result['image_filename'] = filename
            result['weather'] = weather_data
            
            # Save to history
            history = read_history()
            history.insert(0, result)
            history = history[:20] # keep last 20
            write_history(history)
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"An error occurred while calling the Gemini API: {str(e)}"}), 500

@app.route("/translate", methods=["POST"])
def translate():
    global client
    if client is None:
        return jsonify({"error": "Gemini API key is not configured."}), 500
        
    data = request.get_json() or {}
    
    try:
        prompt = f"""
        Translate the following English crop diagnosis report fields to simple, clear Hindi (in Devanagari script) for an Indian farmer.
        
        Fields to translate:
        - Disease Name: {data.get('disease_name', '')}
        - Cause: {data.get('cause', '')}
        - Immediate Action Steps: {', '.join(data.get('immediate_action_steps', []))}
        - Prevention Tips: {', '.join(data.get('prevention_tips', []))}
        - Weather Note: {data.get('weather_note', '') or 'None'}
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are a professional Hindi translator specializing in agriculture.",
                response_mime_type="application/json",
                response_schema=HindiTranslationResponse,
                temperature=0.1,
            )
        )
        
        translated_data = json.loads(response.text)
        return jsonify(translated_data)
        
    except Exception as e:
        return jsonify({"error": f"Translation failed: {str(e)}"}), 500

@app.route("/export/<id>", methods=["GET"])
def export_pdf(id):
    history = read_history()
    report_data = None
    for item in history:
        if item.get("id") == id:
            report_data = item
            break
            
    if not report_data:
        return "Diagnosis report not found.", 404
        
    try:
        # Generate PDF using ReportLab
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#107C41") # forest green
        secondary_color = colors.HexColor("#E47810") # amber/orange
        text_color = colors.HexColor("#1A202C")
        
        # Styles
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=primary_color,
            spaceAfter=15
        )
        
        section_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=17,
            textColor=primary_color,
            spaceBefore=12,
            spaceAfter=6
        )
        
        body_style = ParagraphStyle(
            'BodyTextCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=text_color,
            spaceAfter=8
        )

        bullet_style = ParagraphStyle(
            'BulletCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=text_color,
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=5
        )
        
        story = []
        
        story.append(Paragraph("🌾 SmartFarm Crop Advisory Report", title_style))
        story.append(Paragraph("SmartFarm — AI Crop Advisor for Indian Farmers", body_style))
        story.append(Spacer(1, 10))
        
        # Metadata Table
        meta_data = [
            [Paragraph("<b>Crop:</b>", body_style), Paragraph(report_data.get('crop', 'N/A'), body_style),
             Paragraph("<b>Date:</b>", body_style), Paragraph(report_data.get('timestamp', 'N/A')[:10], body_style)],
            [Paragraph("<b>Disease:</b>", body_style), Paragraph(report_data.get('disease_name', 'N/A'), body_style),
             Paragraph("<b>Severity:</b>", body_style), Paragraph(report_data.get('severity', 'Medium'), body_style)]
        ]
        t = Table(meta_data, colWidths=[60, 200, 50, 200])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0FDF4")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#BBF7D0")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))
        
        # Farmer description
        story.append(Paragraph("📋 Farmer Query / Description", section_style))
        story.append(Paragraph(report_data.get('problem_description', 'N/A'), body_style))
        story.append(Spacer(1, 10))
        
        # Weather
        weather = report_data.get('weather')
        if weather and weather.get('temp') is not None:
            story.append(Paragraph("🌦️ Local Weather Conditions", section_style))
            weather_text = f"Location: <b>{weather.get('city', 'N/A')}</b> | Temperature: <b>{weather.get('temp')}°C</b> | Humidity: <b>{weather.get('humidity')}%</b> | Precipitation: <b>{weather.get('precipitation')}mm</b>"
            story.append(Paragraph(weather_text, body_style))
            if report_data.get('weather_note'):
                story.append(Paragraph(f"<b>Weather Note:</b> {report_data.get('weather_note')}", body_style))
            story.append(Spacer(1, 10))
            
        # Cause
        story.append(Paragraph("🦠 Disease Cause", section_style))
        story.append(Paragraph(report_data.get('cause', 'N/A'), body_style))
        story.append(Spacer(1, 10))
        
        # Immediate Action
        story.append(Paragraph("💊 Immediate Action Steps", section_style))
        for idx, step in enumerate(report_data.get('immediate_action_steps', [])):
            story.append(Paragraph(f"{idx+1}. {step}", bullet_style))
        story.append(Spacer(1, 10))
        
        # Prevention
        story.append(Paragraph("🛡️ Prevention Tips", section_style))
        for idx, tip in enumerate(report_data.get('prevention_tips', [])):
            story.append(Paragraph(f"• {tip}", bullet_style))
        story.append(Spacer(1, 15))
        
        # Helpline
        helpline_data = [[
            Paragraph("<font color='white'><b>Need More Help? Talk to an Expert:</b></font>", body_style),
            Paragraph(f"<font color='white'><b>{report_data.get('helpline', 'Kisan Call Center: 1800-180-1551')}</b></font>", body_style)
        ]]
        helpline_table = Table(helpline_data, colWidths=[200, 300])
        helpline_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), secondary_color),
            ('PADDING', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(helpline_table)
        
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"SmartFarm_Report_{report_data.get('crop')}_{report_data.get('timestamp')[:10]}.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        return f"Error generating PDF: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
