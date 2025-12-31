from influxdb_client import InfluxDBClient
import json
from collections import defaultdict

# InfluxDB Configuration
INFLUXDB_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUXDB_TOKEN = "nZ49M1MTGbHtRCrc2OJhx-kVIBWuwvereT-o1mcq2COz3urUNuUuIIMjysObK8oOEHn8352w7LKFyrX8PQpdsA=="
INFLUXDB_ORG = "Agri"
INFLUXDB_BUCKET = "smart_agri"

# Initialize client
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

# Flux query to retrieve all farmer data
query = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "farmer_data")
'''

# Execute query
result = query_api.query(query=query)

# Group data by submission_id to reconstruct complete records
farmers = defaultdict(lambda: {
    'tags': {},
    'fields': {},
    'time': None
})

for table in result:
    for record in table.records:
        submission_id = record.values.get('submission_id')
        
        # Store timestamp
        if not farmers[submission_id]['time']:
            farmers[submission_id]['time'] = record.get_time()
        
        # Store all tags
        for key, value in record.values.items():
            if key.startswith('_') or key in ['result', 'table']:
                continue
            if key not in ['_field', '_value', '_measurement']:
                farmers[submission_id]['tags'][key] = value
        
        # Store field data
        field_name = record.get_field()
        field_value = record.get_value()
        
        # Parse JSON fields
        if field_name in ['personal_info', 'land_info', 'schemes', 'crops']:
            try:
                farmers[submission_id]['fields'][field_name] = json.loads(field_value)
            except:
                farmers[submission_id]['fields'][field_name] = field_value
        else:
            farmers[submission_id]['fields'][field_name] = field_value

# Display all farmers with complete data
print(f"Total Farmers Found: {len(farmers)}\n")

for submission_id, data in farmers.items():
    print("=" * 80)
    print(f"SUBMISSION ID: {submission_id}")
    print(f"TIMESTAMP: {data['time']}")
    print("-" * 80)
    
    # Display tags
    print("\nTAGS:")
    for key, value in data['tags'].items():
        print(f"  {key}: {value}")
    
    # Display fields
    print("\nFIELDS:")
    
    # Personal Info
    if 'personal_info' in data['fields']:
        print("\n  Personal Information:")
        personal = data['fields']['personal_info']
        for key, value in personal.items():
            print(f"    {key}: {value}")
    
    # Land Info
    if 'land_info' in data['fields']:
        print("\n  Land Information:")
        land = data['fields']['land_info']
        for key, value in land.items():
            print(f"    {key}: {value}")
    
    # Crops
    if 'crops' in data['fields']:
        print("\n  Crops:")
        for crop in data['fields']['crops']:
            print(f"    - {crop}")
    
    # Schemes
    if 'schemes' in data['fields']:
        print("\n  Schemes:")
        for scheme in data['fields']['schemes']:
            print(f"    - {scheme}")
    
    # Other fields
    other_fields = {k: v for k, v in data['fields'].items() 
                   if k not in ['personal_info', 'land_info', 'crops', 'schemes']}
    if other_fields:
        print("\n  Other Information:")
        for key, value in other_fields.items():
            print(f"    {key}: {value}")
    
    print("\n")

client.close()