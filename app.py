import streamlit as st
import pandas as pd
import requests
import json
import os
import shutil
from datetime import datetime, timedelta
from github import Github

# ===============================
# 🔐 إعدادات المستخدمين والجلسات
# ===============================
USERS_FILE = "users.json"
STATE_FILE = "state.json"
SESSION_DURATION = timedelta(minutes=10)
MAX_ACTIVE_USERS = 2

# ===============================
# 📂 إعداد GitHub و Excel
# ===============================
REPO_NAME = "mahmedabdallh123/input-data"
BRANCH = "main"
FILE_PATH = "Machine_Service_Lookup.xlsx"
LOCAL_FILE = "Machine_Service_Lookup.xlsx"
GITHUB_EXCEL_URL = f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH}/{FILE_PATH}"

# ===============================
# ⚙ دوال إدارة المستخدمين
# ===============================
def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        st.error("❌ خطأ في ملف users.json")
        st.stop()

def load_state():
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def cleanup_sessions(state):
    now = datetime.now()
    changed = False
    for user, info in state.items():
        if info.get("active") and "login_time" in info:
            try:
                login_time = datetime.fromisoformat(info["login_time"])
                if now - login_time > SESSION_DURATION:
                    info["active"] = False
                    info.pop("login_time", None)
                    changed = True
            except:
                info["active"] = False
                changed = True
    if changed:
        save_state(state)
    return state

def logout_action():
    state = load_state()
    username = st.session_state.get("username")
    if username and username in state:
        state[username]["active"] = False
        state[username].pop("login_time", None)
        save_state(state)
    st.session_state.clear()
    st.rerun()

def login_ui():
    users = load_users()
    state = cleanup_sessions(load_state())

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None

    st.title("🔐 تسجيل الدخول - Bail Yarn")
    username_input = st.selectbox("👤 اختر المستخدم", list(users.keys()))
    password = st.text_input("🔑 كلمة المرور", type="password")

    active_users = [u for u, v in state.items() if v.get("active")]
    active_count = len(active_users)
    st.caption(f"🔒 المستخدمون النشطون الآن: {active_count} / {MAX_ACTIVE_USERS}")

    if not st.session_state.logged_in:
        if st.button("تسجيل الدخول"):
            if username_input in users and users[username_input]["password"] == password:
                if username_input != "admin" and username_input in active_users:
                    st.warning("⚠ هذا المستخدم مسجل دخول بالفعل.")
                    return False
                elif username_input != "admin" and active_count >= MAX_ACTIVE_USERS:
                    st.error("🚫 الحد الأقصى للمستخدمين المتصلين حالياً.")
                    return False

                state[username_input] = {"active": True, "login_time": datetime.now().isoformat()}
                save_state(state)
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.success(f"✅ تم تسجيل الدخول: {username_input}")
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة.")
        return False
    else:
        username = st.session_state.username
        st.success(f"✅ مسجل الدخول كـ: {username}")
        if st.button("🚪 تسجيل الخروج"):
            logout_action()
        return True

# ===============================
# 📊 تحميل البيانات من GitHub
# ===============================
def fetch_from_github():
    try:
        response = requests.get(GITHUB_EXCEL_URL, stream=True, timeout=10)
        response.raise_for_status()
        with open(LOCAL_FILE, "wb") as f:
            shutil.copyfileobj(response.raw, f)
        st.cache_data.clear()
        st.session_state["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.success("✅ تم تحديث البيانات من GitHub بنجاح وتم مسح الكاش.")
    except Exception as e:
        st.error(f"⚠ فشل التحديث من GitHub: {e}")

@st.cache_data(show_spinner=False)
def load_excel():
    if not os.path.exists(LOCAL_FILE):
        st.error("❌ الملف المحلي غير موجود. برجاء الضغط على زر التحديث أولًا.")
        return None
    df = pd.read_excel(LOCAL_FILE)
    df.columns = df.columns.str.strip()
    return df

# ===============================
# 🔎 عرض حالة الماكينة
# ===============================
def check_machine_status(card_num, current_tons, df):
    try:
        machine_row = df[df["Card"] == int(card_num)]
        if machine_row.empty:
            st.warning("❌ رقم الماكينة غير موجود في الملف.")
            return

        row = machine_row.iloc[0]
        required_tons = float(row["Tons Required"])
        done_tons = float(row["Tons Done"])
        status = "✅ Service Needed" if current_tons - done_tons >= required_tons else "🟢 Running Normally"

        st.subheader("🔍 حالة الماكينة")
        st.write(f"*Card:* {card_num}")
        st.write(f"*Tons Done:* {done_tons}")
        st.write(f"*Tons Required:* {required_tons}")
        st.write(f"*Current Tons:* {current_tons}")
        st.write(f"*الحالة:* {status}")

    except Exception as e:
        st.error(f"⚠ خطأ أثناء فحص الحالة: {e}")

# ===============================
# 🧰 تعديل البيانات (Admin)
# ===============================
def show_edit_page():
    st.title("🛠 تعديل البيانات (Admin)")
    df = load_excel()
    if df is None:
        return

    edited_df = st.data_editor(df, num_rows="dynamic")
    if st.button("💾 حفظ التعديلات ورفعها"):
        save_and_push_excel(edited_df)

def save_and_push_excel(df, commit_message="Update from Streamlit"):
    import openpyxl
    with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    try:
        token = st.secrets["github"]["token"]
    except:
        st.error("🔒 GitHub token غير موجود في secrets.")
        return False

    try:
        g = Github(token)
        repo = g.get_repo(REPO_NAME)
        with open(LOCAL_FILE, "rb") as f:
            content = f.read()
        contents = repo.get_contents(FILE_PATH, ref=BRANCH)
        repo.update_file(FILE_PATH, commit_message, content, contents.sha, branch=BRANCH)
        st.cache_data.clear()
        st.success("✅ تم الحفظ والرفع على GitHub بنجاح.")
        return True
    except Exception as e:
        st.error(f"⚠ فشل الرفع: {e}")
        return False

# ===============================
# 🖥 الواجهة الرئيسية
# ===============================
if not st.session_state.get("logged_in"):
    if not login_ui():
        st.stop()
else:
    tabs = ["📋 عرض الحالة"]
    if st.session_state.get("username") == "admin":
        tabs.append("🛠 تعديل البيانات (Admin)")

    selected = st.tabs(tabs)

    # 📋 عرض الحالة
    with selected[0]:
        if st.button("🔄 تحديث البيانات من GitHub"):
            fetch_from_github()

        df = load_excel()
        if df is not None:
            card_num = st.number_input("رقم الماكينة:", min_value=1, step=1)
            current_tons = st.number_input("عدد الأطنان الحالية:", min_value=0, step=100)

            if st.button("عرض الحالة"):
                check_machine_status(card_num, current_tons, df)

    # 🛠 تعديل البيانات (Admin)
    if st.session_state.get("username") == "admin":
        with selected[1]:
            show_edit_page()
