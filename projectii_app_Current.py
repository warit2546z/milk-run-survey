import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import gpxpy
import xml.etree.ElementTree as ET
import math
import datetime

# --- ฟังก์ชันคำนวณระยะทางแบบเส้นตรง (กรณีไม่มีข้อมูลจริง) ---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

st.set_page_config(page_title="Logistics Route & ETA Dashboard", layout="wide")
st.title("🗺️ ระบบจัดการเส้นทางและตารางเวลาจัดส่ง")

col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("1️⃣ อัปโหลดไฟล์สถานที่ (Excel / CSV)", type=["xlsx", "csv"])
with col2:
    route_file = st.file_uploader("2️⃣ อัปโหลดไฟล์เส้นทาง (GPX / KML) - ถ้ามี", type=["gpx", "kml"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        if 'ชื่อสถานที่' in df.columns and 'Lat' in df.columns and 'Lon' in df.columns:
            
            st.subheader("📝 ตารางข้อมูลจัดส่ง (สามารถคลิกแก้ไขได้)")
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

            # --- ตั้งค่าพารามิเตอร์ ---
            st.markdown("---")
            with st.expander("⚙️ ตั้งค่าพารามิเตอร์รถขนส่ง (เวลา, น้ำมัน, CO2)", expanded=True):
                st.write("**ตั้งค่าเวลาเดินทาง**")
                t_col1, t_col2, t_col3 = st.columns(3)
                with t_col1:
                    start_time = st.time_input("เวลาเริ่มออกเดินทาง", datetime.time(8, 0))
                with t_col2:
                    avg_speed = st.number_input("ความเร็วเฉลี่ยรถ (กม./ชม.)", min_value=1.0, value=40.0, step=5.0)
                with t_col3:
                    # ปรับค่า Default เป็น 1 นาทีตามที่ต้องการ
                    service_time = st.number_input("เวลาลงของแต่ละจุด (นาที)", min_value=0, value=1, step=1)
                
                st.write("**ตั้งค่าต้นทุนและสิ่งแวดล้อม**")
                c_col1, c_col2, c_col3, c_col4 = st.columns(4)
                with c_col1:
                    fuel_rate = st.number_input("อัตราสิ้นเปลือง (กม./ลิตร)", value=10.0)
                with c_col2:
                    fuel_price = st.number_input("ราคาน้ำมัน (บาท/ลิตร)", value=32.50)
                with c_col3:
                    co2_rate = st.number_input("ปล่อย CO2 (kg/ลิตร)", value=2.68)
                with c_col4:
                    baseline_dist = st.number_input("ระยะทางเดิมก่อนปรับปรุง (กม.)", value=0.0)

            # --- เริ่มคำนวณ ---
            current_datetime = datetime.datetime.combine(datetime.date.today(), start_time)
            schedule_data = []
            total_distance = 0.0
            total_travel_mins = 0.0
            
            # เช็คว่ามีคอลัมน์ระยะทางจริงจากตาราง Excel หรือไม่
            col_real_dist = 'ระยะห่างระหว่างแต่ละจุด (กม.)'
            has_real_dist = col_real_dist in edited_df.columns

            for i in range(len(edited_df)):
                row = edited_df.iloc[i]
                if i == 0:
                    dist = 0.0
                    travel_mins = 0
                else:
                    # ถ้าระบุระยะทางจริงใน Excel มา ให้ใช้ค่านั้นเลย
                    if has_real_dist:
                        try:
                            dist = float(row[col_real_dist])
                        except:
                            dist = 0.0 # กรณีเป็นเครื่องหมาย - หรือข้อมูลว่าง
                    else:
                        # ถ้าไม่มี ให้คำนวณแบบเส้นตรง
                        prev_row = edited_df.iloc[i-1]
                        dist = calculate_distance(prev_row['Lat'], prev_row['Lon'], row['Lat'], row['Lon'])
                    
                    travel_mins = (dist / avg_speed) * 60
                
                total_distance += dist
                total_travel_mins += travel_mins
                
                current_datetime += datetime.timedelta(minutes=travel_mins)
                arrival_time = current_datetime.strftime("%H:%M:%S")
                
                current_datetime += datetime.timedelta(minutes=service_time)
                departure_time = current_datetime.strftime("%H:%M:%S")
                
                schedule_data.append({
                    "ลำดับ": i, # ปรับให้เริ่มที่ 0 เหมือนในไฟล์ของคุณ
                    "ชื่อสถานที่": row['ชื่อสถานที่'],
                    "ระยะห่าง (กม.)": f"{dist:.2f}",
                    "เวลาไปถึง (ETA)": arrival_time,
                    "เวลาเดินทางต่อ": departure_time
                })
            
            # --- คำนวณผลลัพธ์รวม (Dashboard) ---
            total_service_mins = len(edited_df) * service_time
            total_time_mins = total_travel_mins + total_service_mins
            
            hours = int(total_time_mins // 60)
            mins = int(total_time_mins % 60)
            
            drive_hours = int(total_travel_mins // 60)
            drive_mins = int(total_travel_mins % 60)
            
            service_hours = int(total_service_mins // 60)
            service_mins = int(total_service_mins % 60)
            
            fuel_used = total_distance / fuel_rate if fuel_rate > 0 else 0
            total_cost = fuel_used * fuel_price
            total_co2 = fuel_used * co2_rate

            delta_dist, delta_cost, delta_co2, delta_time_str = None, None, None, None
            if baseline_dist > 0:
                delta_dist = total_distance - baseline_dist
                baseline_fuel = baseline_dist / fuel_rate
                delta_cost = total_cost - (baseline_fuel * fuel_price)
                delta_co2 = total_co2 - (baseline_fuel * co2_rate)
                
                baseline_time_mins = (baseline_dist / avg_speed) * 60 + total_service_mins
                delta_time_mins = total_time_mins - baseline_time_mins
                delta_time_str = f"{int(delta_time_mins)} นาที"

            # --- Dashboard ---
            st.markdown("---")
            st.subheader("📊 การวิเคราะห์ผลลัพธ์รวม")
            
            if has_real_dist:
                st.success("✅ ระบบกำลังใช้ข้อมูล 'ระยะห่างระหว่างแต่ละจุด (กม.)' จากไฟล์ Excel ของคุณ (แม่นยำที่สุด)")
            else:
                st.warning("⚠️ ไม่พบคอลัมน์ 'ระยะห่างระหว่างแต่ละจุด (กม.)' ระบบจึงประเมินระยะทางแบบเส้นตรง (ซึ่งอาจน้อยกว่าวิ่งถนนจริง)")

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric(label="ระยะทางรวม", value=f"{total_distance:.2f} กม.", 
                          delta=f"{delta_dist:.2f} กม." if delta_dist else None, delta_color="inverse")
            with m2:
                st.metric(label="ต้นทุนน้ำมัน", value=f"฿{total_cost:.2f}", 
                          delta=f"฿{delta_cost:.2f}" if delta_cost else None, delta_color="inverse")
            with m3:
                st.metric(label="CO2 ทั้งเที่ยว", value=f"{total_co2:.2f} kg", 
                          delta=f"{delta_co2:.2f} kg" if delta_co2 else None, delta_color="inverse")
            with m4:
                st.metric(label="เวลาปฏิบัติงาน (ขับรถ+ลงของ)", value=f"{hours} ชม. {mins} นาที", 
                          delta=f"ขับรถ {drive_hours} ชม. {drive_mins} น. | ลงของ {service_hours} ชม. {service_mins} น.", 
                          delta_color="off")

            # --- ตารางเวลา ---
            st.subheader("⏱️ ตารางประมาณการเวลาจัดส่ง (ETA)")
            schedule_df = pd.DataFrame(schedule_data)
            st.dataframe(schedule_df, use_container_width=True)

            # --- แผนที่ ---
            st.markdown("---")
            st.subheader("📍 แผนที่แสดงจุดจัดส่ง")
            
            if not edited_df.empty:
                center_lat = edited_df['Lat'].mean()
                center_lon = edited_df['Lon'].mean()
                m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

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

                for i, row in edited_df.iterrows():
                    eta_info = schedule_df.iloc[i]
                    popup_html = f"""
                    <h4 style='margin-bottom:5px;'>ลำดับ {i}: {row['ชื่อสถานที่']}</h4>
                    <hr style='margin:5px 0'>
                    <b>ถึงเวลา:</b> <span style='color:green;'>{eta_info['เวลาไปถึง (ETA)']}</span><br>
                    <b>ออกเวลา:</b> <span style='color:red;'>{eta_info['เวลาเดินทางต่อ']}</span><br><br>
                    """
                    for col in edited_df.columns:
                        if col not in ['ชื่อสถานที่', 'Lat', 'Lon']:
                            popup_html += f"<b>{col}:</b> {row[col]}<br>"
                    
                    number_icon = folium.DivIcon(html=f"""
                        <div style="background-color:#0078ff; color:white; border-radius:50%; width:30px; height:30px; 
                        display:flex; justify-content:center; align-items:center; font-weight:bold; border:2px solid white; 
                        box-shadow: 0 0 4px rgba(0,0,0,0.5); font-size:14pt;">{i}</div>
                    """, icon_anchor=(15, 15))
                    
                    folium.Marker(
                        location=[row['Lat'], row['Lon']],
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=f"ลำดับ {i} : {row['ชื่อสถานที่']}", 
                        icon=number_icon
                    ).add_to(m)

                st_folium(m, width=1000, height=600)
            
        else:
            st.error("❌ ไฟล์ Excel ต้องมีหัวคอลัมน์ 'ชื่อสถานที่', 'Lat' และ 'Lon'")
            
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

else:
    st.info("👆 อัปโหลดไฟล์สถานที่เพื่อเริ่มต้นระบบ")
