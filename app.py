import streamlit as st
import pandas as pd
import requests
import os
import base64

# ===============================
# 📂 إعدادات GitHub
# ===============================
GITHUB_REPO = "mahmedabdallh123/input-data"
GITHUB_BRANCH = "main"
GITHUB_PATH = "Machine_Service_Lookup.xlsx"
GITHUB_TOKEN = "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"

LOCAL_FILE = "Machine_Service_Lookup.xlsx"
GITHUB_RAW_URL = f"https://github.com/{GITHUB_REPO}/raw/{GITHUB_BRANCH}/{GITHUB_PATH}"

# ===============================
# تحميل Excel من GitHub
# ===============================
def fetch_excel():
    if not os.path.exists(LOCAL_FILE):
        st.info("📥 تحميل الملف من GitHub...")
        try:
            r = requests.get(GITHUB_RAW_URL)
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
# رفع الملف على GitHub
# ===============================
def push_to_github(local_file, commit_msg):
    with open(local_file, "rb") as f:
        content = f.read()
    content_b64 = base64.b64encode(content).decode()

    # الحصول على SHA الحالي للملف
    url_get = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url_get, headers=headers)
    sha = r.json()["sha"] if r.status_code == 200 else None

    data = {
        "message": commit_msg,
        "content": content_b64,
        "branch": GITHUB_BRANCH
    }
    if sha:
        data["sha"] = sha

    url_put = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}"
    r = requests.put(url_put, json=data, headers=headers)
    if r.status_code in [200, 201]:
        st.success(f"✅ تم رفع الملف على GitHub: {r.json()['commit']['html_url']}")
    else:
        st.error(f"⚠ فشل رفع الملف: {r.text}")

# ===============================
# الواجهة
# ===============================
st.title("🛠 CMMS - تعديل وإضافة بيانات (GitHub)")

sheets = load_sheets()
tab1, tab2 = st.tabs(["عرض وتعديل شيت", "إضافة صف/عمود جديد"])

# ===============================
# Tab 1: تعديل البيانات
# ===============================
with tab1:
    st.subheader("✏️ تعديل البيانات")
    sheet_name = st.selectbox("اختر الشيت:", list(sheets.keys()))
    df = sheets[sheet_name]

    edited_df = st.data_editor(df, num_rows="dynamic")

    if st.button("💾 حفظ التعديلات", key="save_edit"):
        sheets[sheet_name] = edited_df
        with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
            for name, sh in sheets.items():
                sh.to_excel(writer, sheet_name=name, index=False)
        push_to_github(LOCAL_FILE, f"تعديل شيت {sheet_name}")

# ===============================
# Tab 2: إضافة صف أو عمود جديد
# ===============================
with tab2:
    st.subheader("➕ إضافة صف أو عمود جديد")
    sheet_name_add = st.selectbox("اختر الشيت:", list(sheets.keys()), key="add_sheet")
    df_add = sheets[sheet_name_add]

    st.markdown("#### إضافة صف")
    new_row = {}
    for col in df_add.columns:
        new_row[col] = st.text_input(f"{col}", key=f"add_row_{col}")
    if st.button("💾 إضافة الصف الجديد"):
        df_add = df_add.append(new_row, ignore_index=True)
        sheets[sheet_name_add] = df_add
        with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
            for name, sh in sheets.items():
                sh.to_excel(writer, sheet_name=name, index=False)
        push_to_github(LOCAL_FILE, f"إضافة صف جديد في شيت {sheet_name_add}")

    st.markdown("---")
    st.markdown("#### إضافة عمود جديد")
    new_col_name = st.text_input("اسم العمود الجديد")
    default_value = st.text_input("القيمة الافتراضية لكل الصفوف (اختياري)", "")
    if st.button("💾 إضافة العمود الجديد"):
        if new_col_name.strip() != "":
            df_add[new_col_name] = default_value
            sheets[sheet_name_add] = df_add
            with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
                for name, sh in sheets.items():
                    sh.to_excel(writer, sheet_name=name, index=False)
            push_to_github(LOCAL_FILE, f"إضافة عمود جديد '{new_col_name}' في شيت {sheet_name_add}")
        else:
            st.warning("⚠ أدخل اسم العمود الجديد أولاً")
