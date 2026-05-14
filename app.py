import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import gpxpy
import xml.etree.ElementTree as ET
import math
import datetime

# --- ฟังก์ชันคำนวณระยะทางระหว่าง 2 พิกัด (กิโลเมตร) ---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # รัศมีโลก (กม.)
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# ตั้งค่าหน้าเว็บให้กว้างขึ้น
st.set_page_config(page_title="Logistics Route & ETA Dashboard", layout="wide")

st.title("🗺️ ระบบจัดการเส้นทางและตารางเวลาจัดส่ง")

# แบ่งหน้าจออัปโหลดไฟล์
col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("1️⃣ อัปโหลดไฟล์สถานที่ (Excel / CSV)", type=["xlsx", "csv"])
with col2:
    route_file = st.file_uploader("2️⃣ อัปโหลดไฟล์เส้นทาง (GPX / KML) - ถ้ามี", type=["gpx", "kml"])

if uploaded_file is not None:
    try:
        # อ่านไฟล์
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        if 'ชื่อสถานที่' in df.columns and 'Lat' in df.columns and 'Lon' in df.columns:
            
            st.subheader("📝 ตารางข้อมูล (สามารถคลิกแก้ไข หรือเพิ่ม/ลบแถวได้เลย)")
            # --- 1. ตารางแบบแก้ไขได้ (Data Editor) ---
            # ตัวแปร edited_df จะเก็บข้อมูลล่าสุดที่คุณแก้ไขบนเว็บ
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

            # --- 2. การคำนวณเวลาจัดส่ง (ETA) ---
            st.markdown("---")
            st.subheader("⏱️ ตารางประมาณการเวลาจัดส่ง (ETA)")
            
            # แผงควบคุมตัวแปรเวลา
            t_col1, t_col2, t_col3 = st.columns(3)
            with t_col1:
                start_time = st.time_input("เวลาเริ่มออกเดินทาง", datetime.time(8, 0))
            with t_col2:
                avg_speed = st.number_input("ความเร็วเฉลี่ยรถ (กม./ชม.)", min_value=1.0, value=40.0, step=5.0)
            with t_col3:
                service_time = st.number_input("เวลาจอดส่งของแต่ละจุด (นาที)", min_value=0, value=10, step=5)

            # เริ่มคำนวณเวลา
            current_datetime = datetime.datetime.combine(datetime.date.today(), start_time)
            schedule_data = []
            total_distance = 0.0

            # วนลูปตามข้อมูลตารางที่แก้ไขแล้ว
            for i in range(len(edited_df)):
                row = edited_df.iloc[i]
                
                # ถ้าเป็นจุดแรก ไม่ต้องคิดระยะทางเดินทาง
                if i == 0:
                    dist = 0.0
                    travel_mins = 0
                else:
                    prev_row = edited_df.iloc[i-1]
                    dist = calculate_distance(prev_row['Lat'], prev_row['Lon'], row['Lat'], row['Lon'])
                    travel_mins = (dist / avg_speed) * 60 # คำนวณเวลาเดินทางเป็นนาที
                
                total_distance += dist
                current_datetime += datetime.timedelta(minutes=travel_mins)
                arrival_time = current_datetime.strftime("%H:%M")
                
                current_datetime += datetime.timedelta(minutes=service_time)
                departure_time = current_datetime.strftime("%H:%M")
                
                schedule_data.append({
                    "ลำดับ": i + 1,
                    "ชื่อสถานที่": row['ชื่อสถานที่'],
                    "ระยะห่าง (กม.)": f"{dist:.2f}",
                    "เวลาไปถึง (ETA)": arrival_time,
                    "เวลาเดินทางต่อ": departure_time
                })
            
            # แสดงผลตารางเวลา
            schedule_df = pd.DataFrame(schedule_data)
            st.dataframe(schedule_df, use_container_width=True)
            st.info(f"**ระยะทางจัดส่งรวมโดยประมาณ (เส้นตรงระหว่างจุด):** {total_distance:.2f} กิโลเมตร")

            # --- 3. แผนที่ ---
            st.markdown("---")
            st.subheader("📍 แผนที่แสดงจุดจัดส่ง")
            
            # ใช้ข้อมูลจากตารางที่แก้ไขแล้ว (edited_df) มาทำแผนที่
            if not edited_df.empty:
                center_lat = edited_df['Lat'].mean()
                center_lon = edited_df['Lon'].mean()
                m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

                # วาดเส้นทาง GPX/KML (ถ้ามี)
                if route_file is not None:
                    route_points = []
                    filename = route_file.name.lower()
                    try:
                        if filename.endswith('.gpx'):
                            gpx = gpxpy.parse(route_file.getvalue().decode('utf-8'))
                            for track in gpx.tracks:
                                for segment in track.segments:
                                    for point in segment.points:
                                        route_points.append((point.latitude, point.longitude))
                        elif filename.endswith('.kml'):
                            tree = ET.fromstring(route_file.getvalue())
                            for coords in tree.iterfind('.//{*}coordinates'):
                                text = coords.text.strip()
                                for pt in text.split():
                                    parts = pt.split(',')
                                    if len(parts) >= 2:
                                        route_points.append((float(parts[1]), float(parts[0])))
                        
                        if route_points:
                            folium.PolyLine(route_points, color="red", weight=4, opacity=0.8).add_to(m)
                    except Exception as e:
                        st.warning(f"ไม่สามารถอ่านไฟล์เส้นทางได้: {e}")

                # ปักหมุดตามคิว
                for i, row in edited_df.iterrows():
                    # จัดเตรียมข้อมูลใน Popup ให้ตรงกับค่าในตาราง ETA
                    eta_info = schedule_df.iloc[i]
                    popup_html = f"""
                    <h4 style='margin-bottom:5px;'>ลำดับ {i+1}: {row['ชื่อสถานที่']}</h4>
                    <hr style='margin:5px 0'>
                    <b>ถึงเวลา:</b> <span style='color:green;'>{eta_info['เวลาไปถึง (ETA)']}</span><br>
                    <b>ออกเวลา:</b> <span style='color:red;'>{eta_info['เวลาเดินทางต่อ']}</span><br><br>
                    """
                    # นำข้อมูลคอลัมน์อื่นๆ มาแสดง
                    for col in edited_df.columns:
                        if col not in ['ชื่อสถานที่', 'Lat', 'Lon']:
                            popup_html += f"<b>{col}:</b> {row[col]}<br>"
                    
                    number_icon = folium.DivIcon(html=f"""
                        <div style="background-color:#0078ff; color:white; border-radius:50%; width:30px; height:30px; 
                        display:flex; justify-content:center; align-items:center; font-weight:bold; border:2px solid white; 
                        box-shadow: 0 0 4px rgba(0,0,0,0.5); font-size:14pt;">{i + 1}</div>
                    """, icon_anchor=(15, 15))
                    
                    folium.Marker(
                        location=[row['Lat'], row['Lon']],
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=f"ลำดับ {i+1} : {row['ชื่อสถานที่']}", 
                        icon=number_icon
                    ).add_to(m)

                st_folium(m, width=1000, height=600)
            
        else:
            st.error("❌ ไฟล์ Excel ต้องมีหัวคอลัมน์ 'ชื่อสถานที่', 'Lat' และ 'Lon'")
            
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

else:
    st.info("👆 อัปโหลดไฟล์สถานที่เพื่อเริ่มต้นระบบ")
