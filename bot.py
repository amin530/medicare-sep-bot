from core import extract_text, clean_and_extract_with_gpt, check_iep2, check_icep_iep, check_part_b_status
from pathlib import Path
from datetime import datetime

print("✅ Enhanced Medicare SEP Bot (CLI) is starting...")

# Paths to files
page1 = Path("marx_page1.png")
page2 = Path("marx_page2.png")

if not page1.exists() or not page2.exists():
    print("❌ One or both OCR image files not found: 'marx_page1.png', 'marx_page2.png'")
    exit(1)

print(f"📄 OCR reading: {page1.name}")
text1 = extract_text(page1)
print(f"📄 OCR reading: {page2.name}")
text2 = extract_text(page2)

combined_text = text1 + "\n" + text2

print("\n📞 OCR TEXT PREVIEW:\n")
print(combined_text[:800] + "...\n")  # Show only first 800 characters

print("📊 Running GPT cleanup and SEP checks...")
data = clean_and_extract_with_gpt(combined_text)

if "error" in data:
    print(f"❌ GPT Error: {data['error']}")
    exit(1)

# Summary
print("\n📋 Summary")
print("------------")
print(f"👤 Name: {data.get('full_name', 'N/A')}")
print(f"🎂 DOB: {data.get('date_of_birth', 'N/A')}")
mbi = data.get('mbi', 'N/A').replace("O", "0")
print(f"🆔 MBI: {mbi}")
contract = data.get("contract_code", "")
pbp = data.get("pbp", "")
contract_code_display = f"H{contract}-{pbp}" if contract and pbp else "N/A"
print(f"📄 Current Plan: {contract_code_display}")
print(f"🏥 Plan Type: {data.get('plan_type', 'N/A')}")
print(f"📍 Location: {data.get('county', '')}, {data.get('state', '')}")

# SEP Logic
print("\n📊 SEP Eligibility Results")
print("---------------------------")
print(check_iep2(data.get("date_of_birth", "")))
print(check_icep_iep(data.get("part_a_date", ""), data.get("part_b_date", "")))
part_b_status_warning = check_part_b_status(data.get("part_b_status", ""))
if part_b_status_warning:
    print("⚠️  ", part_b_status_warning)

# LIS Logic
levels = data.get("recent_lis_levels", [])
if levels:
    last = levels[-1]
    try:
        last_date = datetime.strptime(last["start_date"], "%m/%d/%Y")
        days = (datetime.today() - last_date).days
        if days <= 90:
            print(f"✅ LIS (NLS): LIS level change within last 3 months (started {last['start_date']})")
        else:
            print("❌ No LIS level change in last 3 months.")
    except:
        print("❌ LIS start date format invalid.")
else:
    print("❌ No LIS level data available.")
