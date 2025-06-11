from PIL import Image
import pytesseract
import openai
import json
import re
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Load FEMA DST file
DST_DATA = []
try:
    with open("dst_list.json", "r", encoding="utf-8") as f:
        DST_DATA = json.load(f)
except:
    DST_DATA = []

def extract_text(image_file):
    if image_file is None:
        return ""
    image = Image.open(image_file)
    text = pytesseract.image_to_string(image, config='--psm 6')
    return text

def clean_and_extract_with_gpt(ocr_text):
    prompt = f"""
You are a Medicare OCR assistant.
Your job is to clean this MARx and Medicaid text and return a clean JSON object with:
- full_name
- date_of_birth
- mbi (correct OCR errors like S->5, O->0, etc.)
- contract_code (just the most recent plan)
- pbp (that matches contract)
- plan_type
- part_a_date
- part_b_date
- part_b_status
- county
- state
- recent_lis_levels (up to 3, each with 'start_date' and 'level')
- recent_medicaid_levels (optional, up to 3 like LIS)
- recent_elections (e.g. 'X0001' + PDP info)
Text:
```{ocr_text}```
Return only valid JSON.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        content = response["choices"][0]["message"]["content"].strip()
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        else:
            raise ValueError("GPT response does not contain valid JSON.")
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)}

def check_iep2(dob_str):
    try:
        dob = datetime.strptime(dob_str, "%m/%d/%Y")
        turning_65 = datetime(dob.year + 65, dob.month, 1)
        today = datetime.today()
        delta = (turning_65 - today).days
        if 0 <= delta <= 90:
            return f"✅ IEP2 window open (turning 65: {turning_65.strftime('%B %Y')})"
        elif -90 <= delta < 0:
            return f"⚠️ IEP2 just passed (turned 65: {turning_65.strftime('%B %Y')})"
        else:
            return f"❌ Not in IEP2 window (turns 65: {turning_65.strftime('%B %Y')})"
    except:
        return "❌ IEP2 check failed."

def check_icep_iep(part_a_date, part_b_date):
    try:
        a = datetime.strptime(part_a_date, "%m/%d/%Y")
        b = datetime.strptime(part_b_date, "%m/%d/%Y")
        if a == b:
            return f"✅ ICEP/IEP likely (Part A and B start: {a.strftime('%m/%d/%Y')})"
        return f"⚠️ Part B after Part A → May qualify for ICEP (A: {a.strftime('%m/%d/%Y')}, B: {b.strftime('%m/%d/%Y')})"
    except:
        return "❌ Failed to determine ICEP/IEP."

def check_part_b_status(status):
    if not status or "currently entitled" not in status.lower():
        return "⚠️ Part B entitlement status is not active — review before proceeding."
    return None

def check_dst_sep(county, state):
    today = datetime.today()
    for record in DST_DATA:
        record_state = record["state"].strip().upper()
        record_counties = [c.strip().upper() for c in record["counties"]]
        if record_state != state.upper():
            continue
        end = record["end_date"]
        if end == "TBD":
            return f"✅ DST SEP likely for {state} ({county}) — ends TBD."
        try:
            ends = datetime.strptime(end, "%Y-%m-%d")
            if today > ends:
                continue
            if "ALL" in record_counties or county.upper() in record_counties:
                return f"✅ DST SEP active for {county.title()}, {state.upper()} (ends {end})"
        except:
            continue
    return None

def check_mcd_sep(data):
    levels = data.get("recent_medicaid_levels", [])
    if len(levels) >= 2:
        prev = levels[-2]["level"]
        curr = levels[-1]["level"]
        if prev != curr:
            return f"✅ MCD SEP: Medicaid level changed from {prev} to {curr}."
    return None

def check_dif_sep(data):
    elections = data.get("recent_elections", [])
    if any("X0001" in e for e in elections):
        if any("pdp" in e.lower() for e in elections):
            return "✅ DIF SEP: Auto-enrolled PDP after X0001 election."
    return None

def check_lec_sep(data):
    elections = data.get("recent_elections", [])
    if any("employer" in e.lower() or "cobra" in e.lower() for e in elections):
        return "✅ LEC SEP: Lost employer or COBRA coverage."
    return None

def fallback_questions():
    return [
        ("Check if there's a 5-star plan in their area.", "⭐"),
        ("Check if the customer has a chronic condition like diabetes or heart disease.", "❤️"),
        ("Check if the customer recently moved.", "📦"),
        ("Check if the customer was recently released from incarceration.", "🚔"),
        ("Ask if the customer just lost Medicaid or LIS.", "📉"),
        ("Ask if they left a dual-eligible or SNP plan.", "♿"),
        ("Check if the customer is leaving long-term care.", "🏥"),
    ]
