import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ตั้งค่าหน้าเว็บให้กว้างขึ้น
st.set_page_config(page_title="ข้อมูลการสำรวจ Logistics", layout="wide")

st.title("🗺️ แผนที่และตารางแสดงข้อมูลการสำรวจ")

# ข้อมูลการสำรวจของคุณ (คุณสามารถเพิ่มจุดอื่นๆ หรือเปลี่ยนไปใช้ pd.read_excel('ชื่อไฟล์.xlsx') ก็ได้)
data = {
    "ชื่อสถานที่": ["สำนักงานฟาร์ม มทส.", "ร้านด็อกเตอร์สโนว์", "รพ มทส"],
    "ละติจูด": [14.8890708, 14.9014382, 14.8661903],
    "ลองจิจูด": [102.0006967, 102.0092821, 102.0342216],
    "Demand 200cc": [320, 0, 130],
    "Demand 2000cc": [30, 0, 5],
    "Demand 5000cc": [5, 2, 0]
}

# แปลงข้อมูลให้อยู่ในรูปแบบตาราง
df = pd.DataFrame(data)

# 1. แสดงตารางข้อมูล
st.subheader("📋 ตารางแสดงข้อมูลค่าต่างๆ")
st.dataframe(df, use_container_width=True)

# 2. แสดงแผนที่
st.subheader("📍 แผนที่แสดงจุดสำรวจ")

# สร้างแผนที่ Folium โดยให้จุดศูนย์กลางอยู่ที่จุดแรกของข้อมูล (ฟาร์ม มทส.)
m = folium.Map(location=[df['ละติจูด'].iloc[0], df['ลองจิจูด'].iloc[0]], zoom_start=13)

# วนลูปเพื่อนำพิกัดและข้อมูล Demand มาปักหมุดบนแผนที่
for i, row in df.iterrows():
    # ข้อความที่จะแสดงเมื่อกดคลิกที่หมุด
    popup_text = (
        f"<b>{row['ชื่อสถานที่']}</b><br>"
        f"Demand 200cc: {row['Demand 200cc']} ขวด<br>"
        f"Demand 2L: {row['Demand 2000cc']} ขวด<br>"
        f"Demand 5L: {row['Demand 5000cc']} ขวด"
    )
    
    # ปักหมุดลงบนแผนที่
    folium.Marker(
        location=[row['ละติจูด'], row['ลองจิจูด']],
        popup=popup_text,
        tooltip=row['ชื่อสถานที่'], # ข้อความเมื่อเอาเมาส์ชี้
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

# แสดงแผนที่บนหน้าเว็บ Streamlit
st_folium(m, width=800, height=500)
