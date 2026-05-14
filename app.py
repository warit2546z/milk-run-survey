import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import gpxpy
import xml.etree.ElementTree as ET

# ตั้งค่าหน้าเว็บให้กว้างขึ้น
st.set_page_config(page_title="Logistics Survey & Route Dashboard", layout="wide")

st.title("🗺️ ระบบจำลองเส้นทางและข้อมูลการจัดส่ง")

col1, col2 = st.columns(2)
with col1:
    # สร้างส่วนสำหรับอัปโหลดไฟล์สถานที่ (Excel/CSV)
    uploaded_file = st.file_uploader("1️⃣ อัปโหลดไฟล์ข้อมูลสถานที่ (Excel / CSV)", type=["xlsx", "csv"])
with col2:
    # สร้างส่วนสำหรับอัปโหลดไฟล์เส้นทาง (GPX/KML)
    route_file = st.file_uploader("2️⃣ อัปโหลดไฟล์เส้นทาง (GPX / KML) - เลือกใส่หรือไม่ก็ได้", type=["gpx", "kml"])

if uploaded_file is not None:
    try:
        # ตรวจสอบประเภทไฟล์และอ่านข้อมูล
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        # ตรวจสอบว่าในไฟล์มีคอลัมน์ที่จำเป็นสำหรับทำแผนที่หรือไม่
        if 'ชื่อสถานที่' in df.columns and 'Lat' in df.columns and 'Lon' in df.columns:
            
            st.subheader("📋 ตารางลำดับการจัดส่งและข้อมูล")
            st.dataframe(df, use_container_width=True)

            st.subheader("📍 แผนที่แสดงเส้นทางและจุดจัดส่ง")
            
            # คำนวณหาจุดกึ่งกลางของแผนที่
            center_lat = df['Lat'].mean()
            center_lon = df['Lon'].mean()
            m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

            # ---------------------------------------------------------
            # ส่วนที่ 1: การวาดเส้นทาง (ถ้ามีการอัปโหลดไฟล์ GPX/KML)
            # ---------------------------------------------------------
            if route_file is not None:
                route_points = []
                filename = route_file.name.lower()
                
                try:
                    # กรณีเป็นไฟล์ GPX
                    if filename.endswith('.gpx'):
                        gpx = gpxpy.parse(route_file.getvalue().decode('utf-8'))
                        for track in gpx.tracks:
                            for segment in track.segments:
                                for point in segment.points:
                                    route_points.append((point.latitude, point.longitude))
                    
                    # กรณีเป็นไฟล์ KML
                    elif filename.endswith('.kml'):
                        tree = ET.fromstring(route_file.getvalue())
                        # ค้นหา tag coordinates ทั้งหมดใน KML
                        for coords in tree.iterfind('.//{*}coordinates'):
                            text = coords.text.strip()
                            for pt in text.split(): # แยกด้วยช่องว่าง
                                parts = pt.split(',')
                                if len(parts) >= 2:
                                    # KML เก็บค่าเป็น ลอจิจูด, ละติจูด (Lon, Lat) เราต้องสลับเป็น (Lat, Lon)
                                    route_points.append((float(parts[1]), float(parts[0])))
                    
                    # ถ้าระบุจุดได้ ให้วาดเส้นลงแผนที่
                    if route_points:
                        folium.PolyLine(
                            route_points, 
                            color="red", 
                            weight=4, 
                            opacity=0.8,
                            tooltip="เส้นทางจัดส่ง"
                        ).add_to(m)
                except Exception as e:
                    st.warning(f"ไม่สามารถอ่านไฟล์เส้นทางได้: {e}")

            # ---------------------------------------------------------
            # ส่วนที่ 2: ปักหมุดเป็นเลขลำดับ (ยึดตามบรรทัดในไฟล์ Excel)
            # ---------------------------------------------------------
            for i, row in df.iterrows():
                
                # ข้อความเมื่อคลิกหมุด
                popup_html = f"<h4 style='margin-bottom:5px;'>ลำดับที่ {i+1}: {row['ชื่อสถานที่']}</h4><hr style='margin:5px 0'>"
                for col in df.columns:
                    if col not in ['ชื่อสถานที่', 'Lat', 'Lon']:
                        popup_html += f"<b>{col}:</b> {row[col]}<br>"
                
                # สร้าง Icon แบบปรับแต่งเอง (ใส่ตัวเลขไว้ตรงกลาง)
                number_icon = folium.DivIcon(html=f"""
                    <div style="
                        background-color: #0078ff;
                        color: white;
                        border-radius: 50%;
                        width: 30px;
                        height: 30px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        font-weight: bold;
                        border: 2px solid white;
                        box-shadow: 0 0 4px rgba(0,0,0,0.5);
                        font-size: 14pt;
                    ">
                        {i + 1}
                    </div>
                """, icon_anchor=(15, 15)) # กำหนดจุดศูนย์กลางหมุด
                
                # นำหมุดไปวาง
                folium.Marker(
                    location=[row['Lat'], row['Lon']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"ลำดับที่ {i+1} : {row['ชื่อสถานที่']}", 
                    icon=number_icon
                ).add_to(m)

            # แสดงผลแผนที่บนเว็บ
            st_folium(m, width=1000, height=600)
            
        else:
            st.error("❌ ไฟล์ Excel ต้องมีหัวคอลัมน์ 'ชื่อสถานที่', 'Lat' และ 'Lon' ให้ถูกต้อง")
            
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")

else:
    st.info("👆 กรุณาอัปโหลดไฟล์ Excel/CSV เพื่อเริ่มต้น (ไฟล์เส้นทาง GPX/KML จะอัปโหลดหรือไม่ก็ได้)")
