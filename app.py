from core import extract_text, clean_and_extract_with_gpt, check_iep2, check_icep_iep, check_part_b_status, check_dst_sep, check_mcd_sep, check_dif_sep
from datetime import datetime
import streamlit as st
import os

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
    else:
        # Summary
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
        contract_code_display = f"H{contract}-{pbp}" if contract and pbp else "N/A"

        st.markdown(f"**👤 Name:** {full_name}")
        st.markdown(f"**🆔 MBI:** {mbi}")
        st.markdown(f"**🎂 DOB:** {dob}")
        if contract_code_display != "N/A":
            st.markdown(f"**📄 Current Plan:** [{contract_code_display}](https://www.google.com/search?q={contract_code_display})")
        else:
            st.markdown("**📄 Current Plan:** Not found")
        st.markdown(f"**🏥 Plan Type:** {plan}")
        st.markdown(f"**📍 Location:** {county}, {state}")
        if elections:
            st.markdown(f"**🗳️ Election Code(s):** {', '.join(elections)}")

        # STOP logic for Employer/PACE contracts
        if contract.startswith("8") and not data.get("part_b_status", "").strip():
            st.error("🛑 Employer Group Plan Detected (starts with '8') and no Part B end date. Do NOT proceed.")
            st.stop()
        if contract.startswith("X"):
            st.error("🛑 Invalid contract (starts with 'X'). Do NOT proceed.")
            st.stop()
        if "PACE" in plan.upper():
            st.error("🛑 PACE plan detected. Do NOT proceed.")
            st.stop()

        # LAYUP detection for PDP only
        if "prescription drug" in plan.lower() and part_a and part_b:
            st.success("🎯 LAYUP: Customer has PDP-only and both Part A + B. Easy switch if no other coverage.")

        st.subheader("📊 SEP Eligibility Results")

        # Valid ICEP/IEP logic ONLY if today is around the A/B start
        try:
            a_date = datetime.strptime(part_a, "%m/%d/%Y")
            b_date = datetime.strptime(part_b, "%m/%d/%Y")
            today = datetime.today()
            if abs((today - a_date).days) <= 90 and a_date == b_date:
                st.success(f"✅ ICEP/IEP likely (Part A and B start: {a_date.strftime('%m/%d/%Y')})")
            elif b_date > a_date:
                st.info(f"⚠️ Part B started after Part A (A: {part_a}, B: {part_b}) — ICEP may apply")
            else:
                st.info(f"❌ ICEP/IEP window likely passed (A: {part_a}, B: {part_b})")
        except:
            st.warning("❌ Failed to determine ICEP/IEP timing.")

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
                    else:
                        st.info("❌ No LIS level change in last 3 months.")
                except:
                    st.info("❌ LIS level could not be parsed.")
            else:
                st.info("❌ No LIS level data available.")
        else:
            st.info("❌ LIS data missing from GPT response.")

        dst_result = check_dst_sep(county, state)
        if dst_result:
            st.success(dst_result)

        mcd_result = check_mcd_sep(data)
        if mcd_result:
            st.success(mcd_result)

        dif_result = check_dif_sep(data)
        if dif_result:
            st.success(dif_result)
