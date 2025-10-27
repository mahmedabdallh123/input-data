import streamlit as st
import pandas as pd
import requests
import os
from github import Github
from base64 import b64decode

# ===============================
# إعدادات
# ===============================
REPO_NAME = "mahmedabdallh123/input-data"
BRANCH = "main"
FILE_PATH = "Machine_Service_Lookup.xlsx"
LOCAL_FILE = "Machine_Service_Lookup.xlsx"

# ===============================
# تحميل Excel من GitHub (مرة واحدة لو مش موجود محلياً)
# ===============================
def fetch_excel_if_missing():
    """📥 تحميل ملف Excel من GitHub (بجميع الشيتات) إذا لم يكن موجوداً محلياً"""
    if not os.path.exists(LOCAL_FILE):
        st.info("📥 تحميل الملف من GitHub عبر API...")
        try:
            # 🔒 قراءة التوكين من Streamlit secrets
            token = st.secrets["github"]["token"]
            g = Github(token)
            repo = g.get_repo(REPO_NAME)

            # 📦 جلب المحتوى من GitHub بالفرع المحدد
            file_content = repo.get_contents(FILE_PATH, ref=BRANCH)
            content = b64decode(file_content.content)  # فك الترميز Base64

            # 💾 حفظ الملف محلياً كما هو (بصيغة Excel أصلية)
            with open(LOCAL_FILE, "wb") as f:
                f.write(content)

            st.success("✅ تم تحميل الملف من GitHub بنجاح (بجميع الشيتات).")

        except Exception as e:
            st.error(f"⚠ فشل تحميل الملف من GitHub: {e}")
            st.stop()
    else:
        st.info("📄 الملف موجود محلياً بالفعل.")

# ===============================
# تحميل الشيتات (كل الأعمدة نصوص لتسهيل الكتابة)
# ===============================
@st.cache_data
def load_sheets():
    sheets = pd.read_excel(LOCAL_FILE, sheet_name=None, dtype=object)
    for name, df in sheets.items():
        df.columns = df.columns.str.strip()
    return sheets

# ===============================
# دالة حفظ محلي + رفع على GitHub + مسح الكاش + إعادة تحميل
# ===============================
def save_local_excel_and_push(sheets_dict, commit_message="Update from Streamlit"):
    with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
        for name, sh in sheets_dict.items():
            try:
                sh.to_excel(writer, sheet_name=name, index=False)
            except Exception:
                sh.astype(object).to_excel(writer, sheet_name=name, index=False)

    try:
        token = st.secrets["github"]["token"]
    except Exception:
        st.error("🔒 GitHub token not found in Streamlit secrets. Please set it.")
        return False

    g = Github(token)
    repo = g.get_repo(REPO_NAME)

    with open(LOCAL_FILE, "rb") as f:
        content = f.read()

    try:
        contents = repo.get_contents(FILE_PATH, ref=BRANCH)
        repo.update_file(path=FILE_PATH, message=commit_message, content=content, sha=contents.sha, branch=BRANCH)
    except Exception as e:
        st.error(f"⚠ فشل رفع الملف إلى GitHub: {e}")
        return False

    st.cache_data.clear()
    new_sheets = load_sheets()
    st.success("✅ تم الحفظ والرفع على GitHub بنجاح.")
    return new_sheets

# ===============================
# واجهة المستخدم
# ===============================
st.title("🛠 CMMS - تعديل وإضافة بيانات (GitHub)")

# تأكد من وجود الملف المحلي (تنزيله لو مكنش موجود)
fetch_excel_if_missing()

# نحمل الشيتات (مخبأة)
sheets = load_sheets()

tab1, tab2, tab3 = st.tabs(["عرض وتعديل شيت", "إضافة صف جديد (أحداث متتالية)", "إضافة عمود جديد"])

# -------------------------------
# Tab 1: تعديل بيانات وعرض
# -------------------------------
with tab1:
    st.subheader("✏ تعديل البيانات")
    sheet_name = st.selectbox("اختر الشيت:", list(sheets.keys()), key="edit_sheet")
    df = sheets[sheet_name].astype(str)

    edited_df = st.data_editor(df, num_rows="dynamic")
    if st.button("💾 حفظ التعديلات", key=f"save_edit_{sheet_name}"):
        sheets[sheet_name] = edited_df.astype(object)
        new_sheets = save_local_excel_and_push(sheets, commit_message=f"Edit sheet {sheet_name}")
        if isinstance(new_sheets, dict):
            sheets = new_sheets
            st.dataframe(sheets[sheet_name])

# -------------------------------
# Tab 2: إضافة صف جديد
# -------------------------------
with tab2:
    st.subheader("➕ إضافة صف جديد (سجل حدث جديد داخل نفس الرينج)")
    sheet_name_add = st.selectbox("اختر الشيت لإضافة صف:", list(sheets.keys()), key="add_sheet")
    df_add = sheets[sheet_name_add].astype(str)

    st.markdown("*أدخل بيانات الحدث (يمكنك إدخال أي نص/أرقام/تواريخ)*")
    new_data = {}
    for col in df_add.columns:
        new_data[col] = st.text_input(f"{col}", key=f"add_{sheet_name_add}_{col}")

    if st.button("💾 إضافة الصف الجديد", key=f"add_row_{sheet_name_add}"):
        new_row_df = pd.DataFrame([new_data]).astype(str)
        df_add = pd.concat([sheets[sheet_name_add].astype(str), new_row_df], ignore_index=True)
        sheets[sheet_name_add] = df_add.astype(object)

        new_sheets = save_local_excel_and_push(sheets, commit_message=f"Add new row to {sheet_name_add}")
        if isinstance(new_sheets, dict):
            sheets = new_sheets
            st.success("✅ تم إضافة الحدث الجديد بنجاح!")
            st.dataframe(sheets[sheet_name_add])

# -------------------------------
# Tab 3: إضافة عمود جديد
# -------------------------------
with tab3:
    st.subheader("🆕 إضافة عمود جديد")
    sheet_name_col = st.selectbox("اختر الشيت لإضافة عمود:", list(sheets.keys()), key="add_col_sheet")
    df_col = sheets[sheet_name_col].astype(str)

    new_col_name = st.text_input("اسم العمود الجديد:")
    default_value = st.text_input("القيمة الافتراضية لكل الصفوف (اختياري):", "")

    if st.button("💾 إضافة العمود الجديد", key=f"add_col_{sheet_name_col}"):
        if new_col_name:
            df_col[new_col_name] = default_value
            sheets[sheet_name_col] = df_col.astype(object)

            new_sheets = save_local_excel_and_push(sheets, commit_message=f"Add new column '{new_col_name}' to {sheet_name_col}")
            if isinstance(new_sheets, dict):
                sheets = new_sheets
                st.success("✅ تم إضافة العمود الجديد بنجاح!")
                st.dataframe(sheets[sheet_name_col])
        else:
            st.warning("⚠ الرجاء إدخال اسم العمود الجديد.")
