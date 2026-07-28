import os
import io
import zipfile
import xml.etree.ElementTree as ET
import streamlit as st
from geopy.distance import geodesic

# Page Configuration
st.set_page_config(page_title="KML Path Splitter", page_icon="✂️")

st.title("✂️ KML Path Splitter with Overlap")
st.caption("🚀 Developed by **Rakesh Valmiki😎**")
st.write("Upload a KML file to split long drone paths into smaller segments with customizable distance (KM) and overlap (meters).")

# Input Components
uploaded_file = st.file_uploader("Upload Input KML File", type=["kml"])

col1, col2 = st.columns(2)
with col1:
    user_km = st.number_input("Segment Distance (KM)", value=15.0, step=1.0, min_value=0.1)
with col2:
    overlap_m = st.number_input("Overlap Distance (Meters)", value=50.0, step=10.0, min_value=0.0)

# KML Coordinates Parser
def parse_kml_coordinates(kml_content):
    root = ET.fromstring(kml_content)
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    coords_node = root.find('.//kml:coordinates', ns)
    if coords_node is None or not coords_node.text:
        return []
        
    coords_text = coords_node.text.strip()
    points = []
    for coord in coords_text.split():
        parts = coord.split(',')
        if len(parts) >= 2:
            lon, lat = float(parts[0]), float(parts[1])
            ele = float(parts[2]) if len(parts) > 2 else 0.0
            points.append((lat, lon, ele))
    return points

# Path Splitter Logic
def split_path_with_overlap(points, segment_km, overlap_km):
    segments = []
    current_segment = [points[0]]
    accumulated_dist = 0.0

    for i in range(1, len(points)):
        p1 = (points[i-1][0], points[i-1][1])
        p2 = (points[i][0], points[i][1])
        dist = geodesic(p1, p2).km
        
        accumulated_dist += dist
        current_segment.append(points[i])
        
        if accumulated_dist >= segment_km:
            segments.append(current_segment)
            
            backtrack_dist = 0.0
            j = i
            while j > 0 and backtrack_dist < overlap_km:
                j -= 1
                p_a = (points[j][0], points[j][1])
                p_b = (points[j+1][0], points[j+1][1])
                backtrack_dist += geodesic(p_a, p_b).km
            
            current_segment = points[j:i+1]
            accumulated_dist = 0.0
            
    if len(current_segment) > 1:
        segments.append(current_segment)
        
    return segments

# KML Part Generator
def generate_kml_part_string(points, part_num):
    coords_str = "\n".join([f"{p[1]},{p[0]},{p[2]}" for p in points])
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Part {part_num}</name>
    <Placemark>
      <name>Segment {part_num}</name>
      <LineString>
        <tessellate>1</tessellate>
        <coordinates>
          {coords_str}
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""

# Execution Button
if st.button("✂️ Split Path & Generate KML Parts", type="primary"):
    if uploaded_file is None:
        st.error("❌ Please upload a valid KML file.")
    else:
        try:
            kml_bytes = uploaded_file.read()
            all_points = parse_kml_coordinates(kml_bytes)
            
            if not all_points:
                st.error("❌ No valid coordinates found in the uploaded KML file.")
            else:
                overlap_km = overlap_m / 1000.0
                parts = split_path_with_overlap(all_points, segment_km=user_km, overlap_km=overlap_km)
                
                st.success(f"🎉 Successfully split into {len(parts)} parts!")

                # Create ZIP File in memory
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for idx, part_points in enumerate(parts, start=1):
                        part_kml_str = generate_kml_part_string(part_points, idx)
                        file_name = f"Part_{idx}_{int(user_km)}km_overlap.kml"
                        zip_file.writestr(file_name, part_kml_str)

                zip_buffer.seek(0)

                # Download ZIP Button
                st.download_button(
                    label="📥 Download All Parts (ZIP)",
                    data=zip_buffer,
                    file_name="Split_KML_Parts.zip",
                    mime="application/zip"
                )

        except Exception as e:
            st.error(f"❌ Processing Error: {str(e)}")
