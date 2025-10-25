import streamlit as st
import pandas as pd
import requests
import os
from io import BytesIO

# ===============================
# 📂 إعدادات الملف
# ===============================
GITHUB_URL = "https://github.com/mahmedabdallh123/input-data/raw/refs/heads/main/Machine_Service_Lookup.xlsx"
LOCAL_FILE = "Machine_Service_Lookup.xlsx"

# ===============================
# تحميل Excel من GitHub
# ===============================
def fetch_excel():
    if not os.path.exists(LOCAL_FILE):
        st.info("📥 تحميل الملف من GitHub...")
        try:
            r = requests.get(GITHUB_URL)
            r.raise_for_status()
            with open(LOCAL_FILE, "wb") as f:
                f.write(r.content)
            st.success("✅ تم تحميل الملف بنجاح.")
        except Exception as e:
            st.error(f"⚠ فشل تحميل الملف: {e}")
            st.stop()

# ===============================
# تحميل الشيتات
# ===============================
@st.cache_data
def load_sheets():
    fetch_excel()
    sheets = pd.read_excel(LOCAL_FILE, sheet_name=None)
    for name, df in sheets.items():
        df.columns = df.columns.str.strip()
    return sheets

# ===============================
# الواجهة
# ===============================
st.title("🛠 CMMS - تعديل وإضافة بيانات (GitHub)")

sheets = load_sheets()

tab1, tab2 = st.tabs(["عرض وتعديل شيت", "إضافة صف جديد"])

# ===============================
# Tab 1: تعديل البيانات
# ===============================
with tab1:
    st.subheader("✏️ تعديل البيانات")
    sheet_name = st.selectbox("اختر الشيت:", list(sheets.keys()))
    df = sheets[sheet_name]

    edited_df = st.data_editor(df, num_rows="dynamic")
    if st.button("💾 حفظ التعديلات", key="save_edit"):
        with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
            for name, sh in sheets.items():
                if name == sheet_name:
                    edited_df.to_excel(writer, sheet_name=name, index=False)
                else:
                    sh.to_excel(writer, sheet_name=name, index=False)
        st.success(f"✅ تم حفظ التعديلات على شيت {sheet_name}")

# ===============================
# Tab 2: إضافة صف جديد
# ===============================
with tab2:
    st.subheader("➕ إضافة صف جديد")
    sheet_name_add = st.selectbox("اختر الشيت لإضافة صف:", list(sheets.keys()), key="add_sheet")
    df_add = sheets[sheet_name_add]

    new_data = {}
    for col in df_add.columns:
        new_data[col] = st.text_input(f"{col}", key=f"add_{col}")

    if st.button("💾 إضافة الصف الجديد"):
        df_add = df_add.append(new_data, ignore_index=True)
        sheets[sheet_name_add] = df_add
        with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
            for name, sh in sheets.items():
                sh.to_excel(writer, sheet_name=name, index=False)
        st.success(f"✅ تم إضافة الصف الجديد في شيت {sheet_name_add}")
