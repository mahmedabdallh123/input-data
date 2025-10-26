import streamlit as st
import pandas as pd
import requests
import os
from github import Github

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
    if not os.path.exists(LOCAL_FILE):
        st.info("📥 تحميل الملف من GitHub...")
        try:
            url = f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH}/{FILE_PATH}"
            r = requests.get(url)
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
    sheets = pd.read_excel(LOCAL_FILE, sheet_name=None, dtype=object)
    for name, df in sheets.items():
        df.columns = df.columns.str.strip()
    return sheets

# ===============================
# حفظ ورفع الملف على GitHub
# ===============================
def save_local_excel_and_push(sheets_dict, commit_message="Update from Streamlit"):
    # كتابة الملف محليًا
    with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
        for name, sh in sheets_dict.items():
            sh.to_excel(writer, sheet_name=name, index=False)

    # رفع الملف على GitHub
    try:
        token = st.secrets["github"]["token"]
    except Exception:
        st.error("🔒 GitHub token not found in Streamlit secrets.")
        return False

    g = Github(token)
    repo = g.get_repo(REPO_NAME)
    with open(LOCAL_FILE, "rb") as f:
        content = f.read()

    try:
        contents = repo.get_contents(FILE_PATH, ref=BRANCH)
        repo.update_file(
            path=FILE_PATH,
            message=commit_message,
            content=content,
            sha=contents.sha,
            branch=BRANCH
        )
    except Exception as e:
        st.error(f"⚠ فشل رفع الملف إلى GitHub: {e}")
        return False

    st.cache_data.clear()
    st.success("✅ تم الحفظ والرفع بنجاح.")
    return load_sheets()

# ===============================
# واجهة التطبيق
# ===============================
st.title("🛠 CMMS - تعديل وإضافة بيانات (GitHub)")

# تحميل الملف
fetch_excel_if_missing()
sheets = load_sheets()

if not sheets:
    st.stop()

# عرض الشيتات كلها Tabs تلقائيًا
sheet_names = list(sheets.keys())
st.sidebar.header("📂 قائمة الشيتات")
selected_sheet = st.sidebar.selectbox("اختر الشيت المطلوب:", sheet_names)
st.success(f"✅ تم تحميل {len(sheet_names)} شيت من الملف.")

# Tabs رئيسية للوظائف
tab_names = ["👁 عرض وتعديل", "➕ إضافة صف", "🆕 إضافة عمود", "🗑 حذف صف"]
tabs = st.tabs(tab_names)

# ===============================
# 👁 تبويب 1: عرض وتعديل البيانات
# ===============================
with tabs[0]:
    st.subheader(f"✏ تعديل بيانات - {selected_sheet}")
    df = sheets[selected_sheet].astype(str)
    edited_df = st.data_editor(df, num_rows="dynamic")

    if st.button("💾 حفظ التعديلات", key=f"save_edit_{selected_sheet}"):
        sheets[selected_sheet] = edited_df.astype(object)
        sheets = save_local_excel_and_push(sheets, f"Edit {selected_sheet}")
        st.dataframe(sheets[selected_sheet])

# ===============================
# ➕ تبويب 2: إضافة صف جديد
# ===============================
with tabs[1]:
    st.subheader(f"➕ إضافة صف جديد إلى {selected_sheet}")
    df_add = sheets[selected_sheet].astype(str)
    new_data = {col: st.text_input(f"{col}", key=f"add_{col}") for col in df_add.columns}

    if st.button("💾 إضافة الصف الجديد", key=f"add_row_{selected_sheet}"):
        new_row = pd.DataFrame([new_data])
        sheets[selected_sheet] = pd.concat([df_add, new_row], ignore_index=True).astype(object)
        sheets = save_local_excel_and_push(sheets, f"Add row to {selected_sheet}")
        st.success("✅ تمت إضافة الصف بنجاح!")
        st.dataframe(sheets[selected_sheet])

# ===============================
# 🆕 تبويب 3: إضافة عمود جديد
# ===============================
with tabs[2]:
    st.subheader(f"🆕 إضافة عمود إلى {selected_sheet}")
    new_col = st.text_input("اسم العمود الجديد:")
    default_value = st.text_input("القيمة الافتراضية (اختياري):", "")

    if st.button("💾 إضافة العمود", key=f"add_col_{selected_sheet}"):
        if new_col:
            sheets[selected_sheet][new_col] = default_value
            sheets = save_local_excel_and_push(sheets, f"Add column {new_col} to {selected_sheet}")
            st.success("✅ تم إضافة العمود بنجاح!")
            st.dataframe(sheets[selected_sheet])
        else:
            st.warning("⚠ الرجاء إدخال اسم العمود.")

# ===============================
# 🗑 تبويب 4: حذف صف
# ===============================
with tabs[3]:
    st.subheader(f"🗑 حذف صف من {selected_sheet}")
    df_del = sheets[selected_sheet].astype(str).reset_index(drop=True)
    st.dataframe(df_del)

    rows_to_delete = st.text_input("أدخل أرقام الصفوف للحذف (مثلاً: 0,2,5):")
    confirm = st.checkbox("✅ تأكيد الحذف")

    if st.button("🗑 تنفيذ الحذف", key=f"delete_rows_{selected_sheet}"):
        if confirm and rows_to_delete.strip():
            rows = [int(x.strip()) for x in rows_to_delete.split(",") if x.strip().isdigit()]
            df_new = df_del.drop(rows).reset_index(drop=True)
            sheets[selected_sheet] = df_new.astype(object)
            sheets = save_local_excel_and_push(sheets, f"Delete rows {rows} from {selected_sheet}")
            st.success(f"✅ تم حذف الصفوف {rows}")
            st.dataframe(sheets[selected_sheet])
        else:
            st.warning("⚠ تأكد من إدخال الصفوف وتأكيد الحذف.")
