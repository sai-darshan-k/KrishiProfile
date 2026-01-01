from flask import Flask, render_template, request, jsonify
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone
import json
import uuid
import os

app = Flask(__name__, static_folder='static', template_folder='templates')

# === InfluxDB Configuration (Secure for Vercel) ===
INFLUXDB_URL = os.getenv('INFLUXDB_URL', "https://us-east-1-1.aws.cloud2.influxdata.com")
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', "nZ49M1MTGbHtRCrc2OJhx-kVIBWuwvereT-o1mcq2COz3urUNuUuIIMjysObK8oOEHn8352w7LKFyrX8PQpdsA==")
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', "Agri")
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', "smart_agri")

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# === Farmer ID Counter – Safe for Vercel Serverless ===
# /tmp is the only writable directory in Vercel serverless environment
ID_FILE = "/tmp/next_farmer_id.txt"

def get_next_farmer_id():
    if os.path.exists(ID_FILE):
        try:
            with open(ID_FILE, 'r') as f:
                content = f.read().strip()
                next_id = int(content) if content else 1
        except:
            next_id = 1
    else:
        next_id = 1
    
    # Write the incremented value for next use
    try:
        with open(ID_FILE, 'w') as f:
            f.write(str(next_id + 1))
    except:
        pass  # Fail silently if /tmp is unavailable (rare)
    
    return f"{next_id:04d}"  # Returns 0001, 0002, etc. Change format if needed


# === Routes ===

@app.route('/')
def index():
    return render_template('questionnaire.html')


@app.route('/submit', methods=['POST'])
def submit_form():
    try:
        data = request.json
        
        submission_id = str(uuid.uuid4())
        farmer_name = data.get('farmerName', 'Unknown Farmer').strip() or 'Unknown Farmer'
        farmer_id = get_next_farmer_id()

        def safe_int(value, default=0):
            try:
                return int(value) if value not in ['', None] else default
            except:
                return default
        
        def safe_float(value, default=0.0):
            try:
                return float(value) if value not in ['', None] else default
            except:
                return default

        current_time = datetime.now(timezone.utc)

        # Personal & Location Info
        personal_info = {
            "farmer_name": farmer_name,
            "parent_spouse_name": data.get('parentSpouseName', ''),
            "age": safe_int(data.get('age')),
            "gender": data.get('gender', ''),
            "aadhaar": data.get('aadhaar', ''),
            "mobile": data.get('mobile', ''),
            "village": data.get('village', ''),
            "taluk": data.get('taluk', ''),
            "district": data.get('district', ''),
            "state": data.get('state', '')
        }

        land_info = {
            "land_size": safe_float(data.get('landSize')),
            "land_unit": data.get('landUnit', ''),
            "ownership_type": data.get('ownershipType', ''),
            "experience_years": safe_int(data.get('experienceYears')),
            "has_insurance": data.get('hasInsurance', 'No')
        }

        # Write to InfluxDB
        point = Point("farmer_data") \
            .tag("submission_id", submission_id) \
            .tag("farmer_id", farmer_id) \
            .tag("farmer_name", farmer_name) \
            .tag("district", data.get('district', '')) \
            .tag("state", data.get('state', '')) \
            .field("personal_info", json.dumps(personal_info)) \
            .field("land_info", json.dumps(land_info)) \
            .field("schemes", json.dumps(data.get('schemes', []))) \
            .field("primary_market", data.get('primaryMarket', '')) \
            .field("additional_comments", data.get('additionalComments', '')) \
            .field("advisory_consent", data.get('advisoryConsent') == 'true') \
            .field("crops", json.dumps(data.get('crops', []))) \
            .time(current_time)
        
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)

        return jsonify({
            "success": True,
            "message": "Profile saved successfully!",
            "farmer_id": farmer_id,
            "farmer_name": farmer_name
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# Optional: Health check route
@app.route('/health')
def health():
    return "OK", 200


if __name__ == '__main__':
    app.run(debug=True)