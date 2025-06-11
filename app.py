# app.py
import streamlit as st
from datetime import datetime
import os
from core import extract_text, clean_and_extract_with_gpt, check_iep2, check_icep_iep, check_part_b_status, check_dst_sep, check_mcd_sep, check_dif_sep, check_lec_sep, show_no_sep_suggestions

# Optional Password Protection
PASSWORD = os.getenv("APP_PASSWORD") or "sep123"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Medicare SEP Bot Login")
    password_input = st.text_input("Enter Access Password", type="password")
    if password_input == PASSWORD:
        st.session_state.authenticated = True
        st.experimental_rerun()
    else:
        st.stop()

st.set_page_config(page_title="Medicare SEP Bot", layout="centered")
st.title("🧠 Enhanced Medicare SEP Bot")

uploaded_files = st.file_uploader("Upload MARx or Medicaid screenshots (Page 1 & 2)", accept_multiple_files=True, type=["png", "jpg", "jpeg"])

if uploaded_files:
    combined_text = ""
    for file in uploaded_files:
        text = extract_text(file)
        combined_text += text + "\n"

    st.subheader("📄 OCR Text Preview")
    with st.expander("Click to expand raw OCR text"):
        st.text_area("OCR Output", combined_text, height=300)

    st.subheader("🧠 GPT-Cleaned Summary")
    data = clean_and_extract_with_gpt(combined_text)

    if "error" in data:
        st.error(f"GPT Error: {data['error']}")
        st.stop()

    full_name = data.get("full_name", "N/A")
    dob = data.get("date_of_birth", "N/A")
    mbi = data.get("mbi", "N/A").replace("O", "0")
    contract = data.get("contract_code", "")
    pbp = data.get("pbp", "")
    plan = data.get("plan_type", "")
    part_a = data.get("part_a_date", "N/A")
    part_b = data.get("part_b_date", "N/A")
    part_b_status = data.get("part_b_status", "")
    county = data.get("county", "")
    state = data.get("state", "")
    elections = data.get("recent_elections", [])
    contract_display = f"H{contract}-{pbp}" if contract and pbp else "N/A"

    st.markdown("### 🧠 GPT-Cleaned Summary")
    st.markdown(f"**👤 Name:** {full_name}")
    st.markdown(f"**🆔 MBI:** {mbi}")
    st.markdown(f"**🎂 DOB:** {dob}")
    if contract_display != "N/A":
        st.markdown(f"**📄 Current Plan:** [H{contract}-{pbp}](https://www.google.com/search?q=H{contract}-{pbp})")
    else:
        st.markdown("**📄 Current Plan:** Not found")
    st.markdown(f"**📋 Plan Type:** {plan}")
    st.markdown(f"**📍 Location:** {county}, {state}")

    st.markdown("\n### 📊 SEP Eligibility Results")
    seps_found = 0

    icep = check_icep_iep(part_a, part_b)
    if icep:
        st.info(icep)
        if "✅" in icep:
            seps_found += 1

    st.markdown(check_iep2(dob))

    b_status_flag = check_part_b_status(part_b_status)
    if b_status_flag:
        st.warning(b_status_flag)

    if "recent_lis_levels" in data:
        levels = data["recent_lis_levels"]
        if levels:
            last = levels[-1]
            try:
                last_date = datetime.strptime(last["start_date"], "%m/%d/%Y")
                days = (datetime.today() - last_date).days
                if days <= 90:
                    st.success(f"✅ LIS (NLS): LIS level change within last 3 months (started {last['start_date']})")
                    seps_found += 1
                else:
                    st.info("❌ No LIS level change in last 3 months.")
            except:
                st.info("❌ LIS level could not be parsed.")
        else:
            st.info("❌ No LIS level data available.")

    dst = check_dst_sep(county, state)
    if dst:
        st.success(dst)
        seps_found += 1

    if check_mcd_sep(data):
        st.success(check_mcd_sep(data))
        seps_found += 1

    if check_dif_sep(data):
        st.success(check_dif_sep(data))
        seps_found += 1

    lec_result = check_lec_sep(data)
    if lec_result:
        st.success(lec_result)
        seps_found += 1

    # Suggestions if no SEP or only DST
    if seps_found == 0 or (seps_found == 1 and dst):
        show_no_sep_suggestions(dst_only=bool(dst))
