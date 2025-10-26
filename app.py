# app.py
import streamlit as st
import pandas as pd
import requests
import os
import io
import traceback
import base64

# Optional: only import Github if you will push (avoid import errors if not installed)
try:
    from github import Github
    GITHUB_AVAILABLE = True
except Exception:
    GITHUB_AVAILABLE = False

# ===============================
# إعدادات GitHub / ملف
# ===============================
REPO_NAME = "mahmedabdallh123/input-data"  # اضبط لو لازم
BRANCH = "main"
FILE_PATH = "Machine_Service_Lookup.xlsx"
LOCAL_FILE = "Machine_Service_Lookup.xlsx"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH}/{FILE_PATH}"

st.set_page_config(page_title="CMMS Excel Manager", layout="wide")

# ===============================
# مساعدة: تنزيل ملف للمستخدم (download link)
# ===============================
def get_download_link(file_bytes, filename):
    b64 = base64.b64encode(file_bytes).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">⬇ تحميل {filename}</a>'
    return href

# ===============================
# تنزيل الملف من GitHub إن لم يكن موجودًا
# ===============================
def fetch_excel_if_missing():
    if os.path.exists(LOCAL_FILE):
        return True, None
    try:
        st.info("📥 محاولة تحميل الملف من GitHub...")
        r = requests.get(GITHUB_RAW_URL, timeout=15)
        r.raise_for_status()
        with open(LOCAL_FILE, "wb") as f:
            f.write(r.content)
        st.success("✅ تم تحميل الملف من GitHub.")
        return True, None
    except Exception as e:
        err = str(e)
        st.warning("⚠ لم نتمكن من تنزيل الملف من GitHub تلقائيًا.")
        st.info("يمكنك رفع الملف يدويًا أو تحقق من إعدادات الريبو/مسار الملف/إنترنت السيرفر.")
        return False, err

# ===============================
# تحميل جميع الشيتات من الملف المحلي (آمنة)
# ===============================
@st.cache_data
def load_sheets_local():
    try:
        sheets = pd.read_excel(LOCAL_FILE, sheet_name=None, dtype=object)
        # تنظيف أسماء الأعمدة
        for name, df in sheets.items():
            df.columns = df.columns.str.strip()
        return sheets, None
    except Exception as e:
        return None, str(e)

# ===============================
# حفظ الملف محليًا وإعطاء خيار رفع إلى GitHub أو تنزيله
# ===============================
def save_sheets_locally_and_offer_download(sheets_dict, filename=LOCAL_FILE):
    # save to bytes
    buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for name, df in sheets_dict.items():
                # ensure sheet name length and valid
                safe_name = str(name)[:31]  # Excel sheet name limit
                df.to_excel(writer, sheet_name=safe_name, index=False)
        buffer.seek(0)
        bytes_data = buffer.getvalue()
        # write to local file too
        with open(filename, "wb") as f:
            f.write(bytes_data)
        # offer download link
        st.markdown(get_download_link(bytes_data, filename), unsafe_allow_html=True)
        st.success("✅ تم حفظ الملف محليًا — يمكنك تحميله الآن أو رفعه إلى GitHub.")
        return True, None
    except Exception as e:
        return False, str(e)

# ===============================
# رفع الملف إلى GitHub (باستخدام PyGithub عبر token في st.secrets)
# ===============================
def push_to_github_from_local(commit_message="Update from Streamlit"):
    # require secrets
    try:
        token = st.secrets["github"]["token"]
    except Exception:
        return False, "GitHub token not set in st.secrets (github.token)."

    if not GITHUB_AVAILABLE:
        return False, "PyGithub غير مثبت على السيرفر. ثبت المكتبة (pip install PyGithub)."

    try:
        g = Github(token)
        repo = g.get_repo(REPO_NAME)
        with open(LOCAL_FILE, "rb") as f:
            content = f.read()
        # get current file to retrieve sha
        try:
            contents = repo.get_contents(FILE_PATH, ref=BRANCH)
            sha = contents.sha
        except Exception:
            # file may not exist yet, do create
            sha = None

        if sha:
            repo.update_file(path=FILE_PATH, message=commit_message, content=content, sha=sha, branch=BRANCH)
        else:
            repo.create_file(path=FILE_PATH, message=commit_message, content=content, branch=BRANCH)
        return True, None
    except Exception as e:
        return False, str(e)

# ===============================
# الصفحة الأساسية
# ===============================
st.title("🛠 CMMS - تعديل وإدارة Excel من GitHub")

# 1) تأكد من وجود الملف محلياً أو اسمح برفعه
ok, err = fetch_excel_if_missing()
if not ok:
    st.error(f"تعذر تنزيل الملف تلقائيًا: {err}")
    uploaded = st.file_uploader("📤 ارفع الملف Machine_Service_Lookup.xlsx من جهازك (بديل التنزيل):", type=["xlsx"])
    if uploaded:
        try:
            with open(LOCAL_FILE, "wb") as f:
                f.write(uploaded.getbuffer())
            st.success("✅ تم حفظ الملف محليًا من الرفع.")
            ok = True
        except Exception as e:
            st.error(f"حدث خطأ أثناء حفظ الملف المرفوع: {e}")
            st.stop()
    else:
        st.stop()

# 2) تحميل جميع الشيتات من الملف المحلي
sheets, load_err = load_sheets_local()
if sheets is None:
    st.error(f"فشل تحميل الشيتات من الملف المحلي: {load_err}")
    st.stop()

# 3) Sidebar: اختر الشيت المطلوب أو اعرض Tabs لجميع الشيتات
st.sidebar.header("📂 شيتات الملف")
sheet_names = list(sheets.keys())
st.sidebar.write(f"عدد الشيتات المحمّلة: *{len(sheet_names)}*")

# اختر شيت واحد للعمل عليه (افتراضيًا أول شيت موجود)
selected_sheet = st.sidebar.selectbox("اختر الشيت للعمل عليه:", sheet_names, index=0)

# زر لتحديث الشيتات من GitHub يدوياً
if st.sidebar.button("🔄 تحديث من GitHub"):
    ok2, err2 = fetch_excel_if_missing()
    if ok2:
        # invalidate cache
        st.cache_data.clear()
        sheets, load_err = load_sheets_local()
        if sheets is None:
            st.error(f"فشل إعادة التحميل: {load_err}")
        else:
            st.experimental_rerun()
    else:
        st.error(f"فشل التنزيل: {err2}")

st.sidebar.markdown("---")
st.sidebar.markdown("*خيارات حفظ:*")
# زر حفظ ورفع
if st.sidebar.button("💾 حفظ ورفع إلى GitHub"):
    # نجرب نحفظ الملف محليًا أولاً
    success, err = save_sheets_locally_and_offer_download(sheets, filename=LOCAL_FILE)
    if not success:
        st.error(f"فشل الحفظ المحلي: {err}")
    else:
        pushed, perr = push_to_github_from_local(commit_message="Update from Streamlit (UI)")
        if pushed:
            st.success("✅ تم رفع الملف إلى GitHub.")
            st.cache_data.clear()
            st.experimental_rerun()
        else:
            st.warning(f"لم يتم الرفع إلى GitHub: {perr}. يمكنك تحميل الملف يدويًا ثم رفعه للـ repo.")

st.sidebar.markdown("---")
st.sidebar.info("إذا لم تكن تريد الرفع، استخدم زر التحميل بعد الحفظ المحلي.")

# 4) اعرض بيانات الشيت المحدد
st.subheader(f"📄 محتوى الشيت: {selected_sheet} (إجمالي صفوف: {len(sheets[selected_sheet])})")
st.dataframe(sheets[selected_sheet].reset_index(drop=True), use_container_width=True)

# 5) الوظائف: tabs تعمل على الشيت المحدد
tabs = st.tabs(["✏ تعديل", "➕ إضافة صف", "🆕 إضافة عمود", "🗑 حذف صف", "🔍 فحص سريع"])

# ---- تبويب التعديل ----
with tabs[0]:
    st.markdown(f"### ✏ تعديل بيانات الشيت {selected_sheet}")
    df = sheets[selected_sheet].astype(str)
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"editor_{selected_sheet}")
    if st.button("حفظ التعديلات (محلي + عرض تحميل)", key=f"save_edit_{selected_sheet}"):
        sheets[selected_sheet] = edited.astype(object)
        oksave, errsave = save_sheets_locally_and_offer_download(sheets)
        if not oksave:
            st.error(f"فشل الحفظ: {errsave}")
        else:
            st.success("✅ تم الحفظ محليًا. (يمكنك رفعه أو تنزيله)")

# ---- تبويب إضافة صف ----
with tabs[1]:
    st.markdown(f"### ➕ إضافة صف جديد إلى {selected_sheet}")
    df_add = sheets[selected_sheet].astype(str).reset_index(drop=True)
    st.info("أدخل قيم الأعمدة الجديدة كـ نص. يمكن تعديلها لاحقًا في تبويب التعديل.")
    new_row = {}
    cols = df_add.columns.tolist()
    for c in cols:
        new_row[c] = st.text_input(f"{c}", key=f"newrow_{selected_sheet}_{c}")
    if st.button("أضف الصف الآن", key=f"addrow_btn_{selected_sheet}"):
        try:
            nr = pd.DataFrame([new_row])
            sheets[selected_sheet] = pd.concat([df_add, nr], ignore_index=True).astype(object)
            ok, err = save_sheets_locally_and_offer_download(sheets)
            if ok:
                st.success("✅ تم إضافة الصف وحفظ الملف محليًا.")
            else:
                st.error(f"فشل الحفظ بعد الإضافة: {err}")
        except Exception as e:
            st.error(f"خطأ أثناء إضافة الصف: {e}\n{traceback.format_exc()}")

# ---- تبويب إضافة عمود ----
with tabs[2]:
    st.markdown(f"### 🆕 إضافة عمود إلى {selected_sheet}")
    new_col_name = st.text_input("اسم العمود الجديد:")
    default_val = st.text_input("القيمة الافتراضية لكل الصفوف (اختياري):", "")
    if st.button("أضف العمود", key=f"addcol_btn_{selected_sheet}"):
        if not new_col_name.strip():
            st.warning("أدخل اسمًا صالحًا للعمود.")
        else:
            try:
                sheets[selected_sheet][new_col_name] = default_val
                ok, err = save_sheets_locally_and_offer_download(sheets)
                if ok:
                    st.success("✅ تم إضافة العمود وحفظ الملف محليًا.")
                else:
                    st.error(f"فشل الحفظ بعد إضافة العمود: {err}")
            except Exception as e:
                st.error(f"خطأ أثناء إضافة العمود: {e}\n{traceback.format_exc()}")

# ---- تبويب حذف صف ----
with tabs[3]:
    st.markdown(f"### 🗑 حذف صفوف من {selected_sheet}")
    df_del = sheets[selected_sheet].astype(str).reset_index(drop=True)
    st.dataframe(df_del, use_container_width=True)
    rows_text = st.text_input("أدخل أرقام الصفوف للحذف (مثال: 0,2,5):", "")
    confirm = st.checkbox("✅ أؤكد الحذف")
    if st.button("تنفيذ حذف الصفوف", key=f"delrows_btn_{selected_sheet}"):
        if not confirm:
            st.warning("يجب تأكيد الحذف أولًا.")
        else:
            try:
                indices = [int(x.strip()) for x in rows_text.split(",") if x.strip().isdigit()]
                if not indices:
                    st.warning("لم تُدخل أي أرقام صحيحة.")
                else:
                    df_new = df_del.drop(indices).reset_index(drop=True)
                    sheets[selected_sheet] = df_new.astype(object)
                    ok, err = save_sheets_locally_and_offer_download(sheets)
                    if ok:
                        st.success(f"✅ تم حذف الصفوف: {indices} وحفظ الملف محليًا.")
                    else:
                        st.error(f"فشل الحفظ بعد الحذف: {err}")
            except Exception as e:
                st.error(f"خطأ أثناء الحذف: {e}\n{traceback.format_exc()}")

# ---- تبويب فحص سريع ----
with tabs[4]:
    st.markdown("### 🔍 فحص سريع داخل الشيت المحدد")
    st.write("عرض أول 10 صفوف وسرد أسماء الأعمدة لفحص سريع:")
    st.write("*أسماء الأعمدة:*", list(sheets[selected_sheet].columns))
    st.dataframe(sheets[selected_sheet].head(10), use_container_width=True)

# نهاية الملف
