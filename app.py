import streamlit as st
import pandas as pd
import time
import io
import requests
from datetime import datetime

# ===============================
# ⚙ إعداد الصفحة
# ===============================
st.set_page_config(page_title="CMMS Yarn Prep", layout="wide")

# ===============================
# 🗝 بيانات الدخول
# ===============================
USERS = {
    "hall1": {"password": "123", "excel_url": "https://raw.githubusercontent.com/MedoTatch/cmms/main/hall1.xlsx"},
    "hall2": {"password": "456", "excel_url": "https://raw.githubusercontent.com/MedoTatch/cmms/main/hall2.xlsx"},
    "admin": {"password": "admin", "excel_url": "https://raw.githubusercontent.com/MedoTatch/cmms/main/hall1.xlsx"},
}

# ===============================
# 🧠 دالة تحميل البيانات
# ===============================
@st.cache_data
def load_excel_from_github(url):
    try:
        file_content = requests.get(url).content
        df_dict = pd.read_excel(io.BytesIO(file_content), sheet_name=None)
        return df_dict
    except Exception as e:
        st.error(f"حدث خطأ أثناء تحميل الملف: {e}")
        return None

# ===============================
# ⏳ دالة فحص الجلسة
# ===============================
def check_session():
    if "login_time" in st.session_state:
        elapsed = (datetime.now() - st.session_state["login_time"]).total_seconds()
        if elapsed > 3600:  # ساعة واحدة
            st.warning("⏰ انتهت الجلسة، يرجى تسجيل الدخول مرة أخرى.")
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.stop()

# ===============================
# 📊 دالة عرض حالة الماكينة
# ===============================
def check_machine_status(card_num, current_tons, all_sheets):
    try:
        sheet_name = list(all_sheets.keys())[0]
        df = all_sheets[sheet_name]

        if "Machine No" not in df.columns:
            st.error("❌ لا يوجد عمود باسم 'Machine No' في الملف.")
            return

        row = df[df["Machine No"].astype(str) == str(int(card_num))]
        if row.empty:
            st.warning("⚠ لم يتم العثور على الماكينة بهذا الرقم.")
            return

        st.subheader("🧾 تفاصيل الماكينة:")
        st.dataframe(row, use_container_width=True)

        required_cols = ["Last Service Tons", "Interval Tons"]
        if not all(col in df.columns for col in required_cols):
            st.info("⚙ الملف لا يحتوي على الأعمدة المطلوبة للحساب.")
            return

        last_tons = float(row.iloc[0]["Last Service Tons"])
        interval = float(row.iloc[0]["Interval Tons"])
        due = last_tons + interval

        st.write(f"🔹 آخر خدمة عند: {last_tons}")
        st.write(f"🔹 الفاصل بين الخدمات: {interval}")
        st.write(f"🔹 الخدمة القادمة عند: {due}")
        st.write(f"🔹 الأطنان الحالية: {current_tons}")

        if current_tons >= due:
            st.error("🔴 الخدمة مطلوبة الآن!")
        elif current_tons >= due - (0.2 * interval):
            st.warning("🟡 اقترب موعد الخدمة.")
        else:
            st.success("🟢 الماكينة تعمل بشكل طبيعي.")

    except Exception as e:
        st.error(f"حدث خطأ أثناء فحص الماكينة: {e}")

# ===============================
# 🧾 صفحة تعديل الإكسيل (للأدمن)
# ===============================
def show_edit_page(excel_url):
    st.subheader("🛠 تعديل بيانات الإكسيل")

    df_dict = load_excel_from_github(excel_url)
    if not df_dict:
        return

    sheet_name = list(df_dict.keys())[0]
    df = df_dict[sheet_name]

    st.dataframe(df, use_container_width=True)

    edited_df = st.data_editor(df, use_container_width=True)

    if st.button("💾 حفظ التعديلات"):
        try:
            towrite = io.BytesIO()
            with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
                edited_df.to_excel(writer, index=False, sheet_name=sheet_name)
            towrite.seek(0)
            st.download_button(
                "⬇ تحميل الملف المعدل",
                data=towrite,
                file_name="updated_file.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            st.success("✅ تم حفظ الملف محليًا، يمكنك رفعه إلى GitHub يدويًا.")
        except Exception as e:
            st.error(f"حدث خطأ أثناء الحفظ: {e}")

# ===============================
# 🚪 صفحة الدخول
# ===============================
def login_page():
    st.title("🔐 نظام متابعة الصيانة | CMMS Yarn Prep")

    username = st.text_input("اسم المستخدم:")
    password = st.text_input("كلمة المرور:", type="password")

    if st.button("تسجيل الدخول"):
        if username in USERS and USERS[username]["password"] == password:
            st.session_state["username"] = username
            st.session_state["login_time"] = datetime.now()
            st.success("✅ تم تسجيل الدخول بنجاح.")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة.")

# ===============================
# 🧩 التطبيق الرئيسي
# ===============================
def main():
    check_session()

    username = st.session_state.get("username", None)
    if not username:
        login_page()
        st.stop()

    st.sidebar.title(f"👋 أهلاً {username}")
    excel_url = USERS[username]["excel_url"]
    all_sheets = load_excel_from_github(excel_url)

    tabs = ["📋 عرض الحالة", "⚙ تعديل البيانات"] if username == "admin" else ["📋 عرض الحالة"]
    selected_tab = st.tabs(tabs)

    # تبويب عرض الحالة
    with selected_tab[0]:
        st.subheader("📋 فحص حالة الماكينة")

        card_num = st.text_input("رقم الماكينة:")
        current_tons = st.number_input("عدد الأطنان الحالية:", min_value=0.0)

        if st.button("✅ عرض الحالة"):
            if all_sheets:
                check_machine_status(card_num, current_tons, all_sheets)
            else:
                st.warning("⚠ لم يتم تحميل الملف بعد.")

    # تبويب التعديل للأدمن
    if username == "admin":
        with selected_tab[1]:
            show_edit_page(excel_url)

# ===============================
# 🚀 تشغيل التطبيق
# ===============================
if _name_ == "_main_":
    main()
