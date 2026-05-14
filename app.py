import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ตั้งค่าหน้าเว็บให้กว้างขึ้น
st.set_page_config(page_title="Logistics Survey Dashboard", layout="wide")

st.title("🗺️ ระบบนำเข้าไฟล์ข้อมูลสำรวจและแสดงผลบนแผนที่")

# สร้างส่วนสำหรับอัปโหลดไฟล์
uploaded_file = st.file_uploader("📂 กรุณาอัปโหลดไฟล์ข้อมูล (รองรับ Excel .xlsx หรือ .csv)", type=["xlsx", "csv"])

if uploaded_file is not None:
    try:
        # ตรวจสอบประเภทไฟล์และอ่านข้อมูล
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        # ตรวจสอบว่าในไฟล์มีคอลัมน์ที่จำเป็นสำหรับทำแผนที่หรือไม่
        if 'ชื่อสถานที่' in df.columns and 'ละติจูด' in df.columns and 'ลองจิจูด' in df.columns:
            
            # 1. แสดงตารางข้อมูล
            st.subheader("📋 ตารางแสดงข้อมูลค่าต่างๆ")
            st.dataframe(df, use_container_width=True)

            # 2. แสดงแผนที่
            st.subheader("📍 แผนที่แสดงจุดสำรวจ")
            
            # คำนวณหาจุดกึ่งกลางของแผนที่จากพิกัดทั้งหมด
            center_lat = df['ละติจูด'].mean()
            center_lon = df['ลองจิจูด'].mean()
            m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

            # วนลูปเพื่อนำพิกัดและข้อมูลมาปักหมุด
            for i, row in df.iterrows():
                
                # สร้างข้อความ Popup โดยดึงข้อมูลทุกคอลัมน์ที่ไม่ได้ชื่อว่าพิกัดมาแสดงอัตโนมัติ
                popup_html = f"<h4 style='margin-bottom:5px;'>{row['ชื่อสถานที่']}</h4><hr style='margin:5px 0'>"
                for col in df.columns:
                    if col not in ['ชื่อสถานที่', 'ละติจูด', 'ลองจิจูด']:
                        popup_html += f"<b>{col}:</b> {row[col]}<br>"
                
                # ปักหมุดลงบนแผนที่
                folium.Marker(
                    location=[row['ละติจูด'], row['ลองจิจูด']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=str(row['ชื่อสถานที่']), 
                    icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(m)

            # แสดงผลแผนที่บนเว็บ
            st_folium(m, width=1000, height=600)
            
        else:
            st.error("❌ ข้อผิดพลาด: ไฟล์ของคุณต้องมีหัวคอลัมน์ชื่อ 'ชื่อสถานที่', 'ละติจูด' และ 'ลองจิจูด' (พิมพ์ให้ตรงกันเป๊ะๆ)")
            
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")

else:
    # ข้อความแสดงเมื่อยังไม่มีการอัปโหลดไฟล์
    st.info("👆 กรุณาอัปโหลดไฟล์ข้อมูลของคุณด้านบน เพื่อเริ่มต้นการแสดงผล")
    st.write("**เงื่อนไขของไฟล์ที่นำมาอัปโหลด:** ต้องมีหัวคอลัมน์ (บรรทัดแรกสุด) ที่ใช้คำว่า **ชื่อสถานที่**, **ละติจูด** และ **ลองจิจูด** ส่วนคอลัมน์ข้อมูลอื่นๆ ระบบจะนำไปแสดงผลให้อัตโนมัติ")
