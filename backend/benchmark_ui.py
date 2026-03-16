import streamlit as st
import subprocess
import os
import sys

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Benchmark UI", page_icon="🧪", layout="wide")
st.title("Topic Modeling Benchmark Dashboard")
st.markdown("บอกลาการพิมพ์ Command Line ยาวๆ! ปรับค่าพารามิเตอร์ผ่าน UI แล้วกดรันได้เลย")

# Sidebar สำหรับตั้งค่าพารามิเตอร์
st.sidebar.header("Model Parameters")

# Model
model_choice = st.sidebar.selectbox("Select Model", ["LDA", "NMF", "BERTopic"])

# Topics (K)
k_option = st.sidebar.number_input("Number of Topics (K) [0 = Auto/Domain Count]", min_value=0, value=0, step=1)

# Thresholds
st.sidebar.subheader("Threshold Settings")
target_level = st.sidebar.selectbox("Target Concept Level", [0, 1, 2], index=1)
openalex_threshold = st.sidebar.slider("OpenAlex Base Threshold", 0.0, 1.0, 0.3, 0.05)

st.sidebar.markdown("---")
st.sidebar.markdown("**Multi-label Tuning** (ได้จาก Grid Search)")
abs_threshold = st.sidebar.slider("Absolute Threshold (prob > X)", 0.0, 1.0, 0.1, 0.05)
rel_threshold = st.sidebar.slider("Relative Threshold (prob >= max*Y)", 0.0, 1.0, 0.3, 0.05)

# for BERTopic
use_approx = False
use_lemma = False
if model_choice == "BERTopic":
    st.sidebar.subheader("BERTopic Options")
    use_approx = st.sidebar.checkbox("Use Approximate Dist. (c-TF-IDF)", value=True)
    use_lemma = st.sidebar.checkbox("Use Lemmatized Input", value=False)

# File Input / Output
st.sidebar.markdown("---")
st.sidebar.subheader("File & Export Settings")
input_file = st.sidebar.text_input("Input JSON File (เว้นว่างเพื่อดึงจาก DB)", value="")

col1, col2 = st.sidebar.columns(2)
export_csv = col1.checkbox("Export CSV", value=True)
export_3d = col2.checkbox("Export 3D HTML", value=True)

# Main Area
st.subheader("Run Experiment")

if st.button("▶Start Benchmark", type="primary", use_container_width=True):
    with st.spinner("กำลังรันโมเดลและประเมินผล (ดู Log ด้านล่าง)..."):
        
        script_name = f"run_{model_choice.lower()}_benchmark"
        
        # Command Line
        cmd = [sys.executable, "manage.py", script_name]
        
        if k_option > 0:
            cmd.extend(["--k", str(k_option)])
            
        cmd.extend([
            "--threshold", str(openalex_threshold),
            "--abs_threshold", str(abs_threshold),
            "--rel_threshold", str(rel_threshold),
            "--target_level", str(target_level)
        ])
        
        if input_file:
            cmd.extend(["--input", input_file])
            
        if export_csv:
            cmd.extend(["--export_csv", f"results_{model_choice.lower()}.csv"])
            
        if export_3d:
            cmd.extend(["--export_scatter_3d", f"scatter3d_{model_choice.lower()}.html"])
            
        if model_choice == "BERTopic":
            if use_approx: cmd.append("--use_approx_dist")
            if use_lemma: cmd.append("--use_lemmatized_input")

        # show Command
        st.code(" ".join(cmd), language="bash")
        
        # run with subprocess and show Output
        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True,
                encoding='utf-8'
            )
            
            # Log
            log_area = st.empty()
            log_text = ""
            
            for line in process.stdout:
                log_text += line
                log_area.text_area("Terminal Output:", log_text, height=400)
                
            process.wait()
            
            if process.returncode == 0:
                st.success("รัน Benchmark สำเร็จ!")
                
                if export_3d and os.path.exists(f"scatter3d_{model_choice.lower()}.html"):
                    with open(f"scatter3d_{model_choice.lower()}.html", "r", encoding="utf-8") as f:
                        html_data = f.read()
                    st.components.v1.html(html_data, height=600, scrolling=True)
                    
            else:
                st.error("เกิดข้อผิดพลาดในการรัน กรุณาเช็ค Log ด้านบน")
                
        except Exception as e:
            st.error(f"Error executing command: {e}")