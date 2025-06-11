import requests
import json
from datetime import datetime

url = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries?$orderby=declarationDate desc&$top=1000"
res = requests.get(url)

if res.status_code != 200:
    raise Exception("Failed to fetch FEMA data")

data = res.json()["DisasterDeclarationsSummaries"]
print(f"📦 Fetched {len(data)} records from FEMA")
today = datetime.today()

dst_list = []
skipped = 0
today = datetime.today()

for item in data:
    try:
        state = item.get("state", "").strip()
        reason = item.get("incidentType", "Disaster").strip()
        county = item.get("designatedArea", "All").strip()
        start = item.get("incidentBeginDate", "")
        end = item.get("incidentEndDate", "")

        # DEBUG: Print raw dates
        print(f"🕒 RAW -> Start: {start}, End: {end}")

        # If no dates, skip it
        if not start:
            skipped += 1
            print("❌ Skipped: No start date.")
            continue

        start_date = datetime.strptime(start[:10], "%Y-%m-%d")
        end_date = None
        if end:
            end_date = datetime.strptime(end[:10], "%Y-%m-%d")

        if not end or end_date >= today:
            dst_list.append({
                "state": state,
                "reason": reason,
                "counties": ["All"] if "All" in county else [county],
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d") if end_date else "TBD"
            })
            print(f"✅ Added: {state}, {county}, {reason}")
        else:
            skipped += 1
            print("❌ Skipped: End date has passed.")

    except Exception as e:
        print(f"⚠️ Error: {e}")
        skipped += 1
        continue

with open("dst_list.json", "w") as f:
    json.dump(dst_list, f, indent=2)

print(f"✅ dst_list.json updated with {len(dst_list)} active FEMA records.")
input("\nPress Enter to close...")
