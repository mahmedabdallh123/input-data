# app.py - نسخة كاملة ومتكاملة (CMMS - Bail Yarn)
import streamlit as st
import pandas as pd
import json
import os
import io
import requests
import shutil
import re
from datetime import datetime, timedelta
from base64 import b64decode

# محاولة استيراد PyGithub (لرفع التعديلات)
try:
    from github import Github
    GITHUB_AVAILABLE = True
except Exception:
    GITHUB_AVAILABLE = False

# ===============================
# إعدادات عامة
# ===============================
USERS_FILE = "users.json"
STATE_FILE = "state.json"
SESSION_DURATION = timedelta(minutes=10)  # مدة الجلسة 10 دقائق
MAX_ACTIVE_USERS = 2  # أقصى عدد مستخدمين مسموح

# إعدادات GitHub
REPO_NAME = "mahmedabdallh123/input-data"
BRANCH = "main"
FILE_PATH = "Machine_Service_Lookup.xlsx"
LOCAL_FILE = "Machine_Service_Lookup.xlsx"
GITHUB_EXCEL_URL = f"https://github.com/{REPO_NAME}/raw/refs/heads/{BRANCH}/{FILE_PATH}"

# ===============================
# دوال مساعدة للملفات والحالة
# ===============================
def load_users():
    if not os.path.exists(USERS_FILE):
        default = {"admin": {"password": "admin"}}
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
        return default
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"❌ خطأ في ملف users.json: {e}")
        st.stop()

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

def load_state():
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def cleanup_sessions(state):
    now = datetime.now()
    changed = False
    for user, info in list(state.items()):
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

def remaining_time(state, username):
    if not username or username not in state:
        return None
    info = state.get(username)
    if not info or not info.get("active"):
        return None
    try:
        lt = datetime.fromisoformat(info["login_time"])
        remaining = SESSION_DURATION - (datetime.now() - lt)
        if remaining.total_seconds() <= 0:
            return None
        return remaining
    except:
        return None

# -------------------------------
# 🔐 تسجيل الخروج
# -------------------------------
def logout_action():
    state = load_state()
    username = st.session_state.get("username")
    if username and username in state:
        state[username]["active"] = False
        state[username].pop("login_time", None)
        save_state(state)
    # احذف متغيرات الجلسة
    keys = list(st.session_state.keys())
    for k in keys:
        st.session_state.pop(k, None)
    st.rerun()

# -------------------------------
# 🧠 واجهة تسجيل الدخول
# -------------------------------
def login_ui():
    users = load_users()
    state = cleanup_sessions(load_state())
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None

    st.title("🔐 تسجيل الدخول - Bail Yarn (CMMS)")

    # اختيار المستخدم
    username_input = st.selectbox("👤 اختر المستخدم", list(users.keys()))
    password = st.text_input("🔑 كلمة المرور", type="password")

    active_users = [u for u, v in state.items() if v.get("active")]
    active_count = len(active_users)
    st.caption(f"🔒 المستخدمون النشطون الآن: {active_count} / {MAX_ACTIVE_USERS}")

    if not st.session_state.logged_in:
        if st.button("تسجيل الدخول"):
            if username_input in users and users[username_input]["password"] == password:
                if username_input == "admin":
                    pass
                elif username_input in active_users:
                    st.warning("⚠ هذا المستخدم مسجل دخول بالفعل.")
                    return False
                elif active_count >= MAX_ACTIVE_USERS:
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
        rem = remaining_time(state, username)
        if rem:
            mins, secs = divmod(int(rem.total_seconds()), 60)
            st.info(f"⏳ الوقت المتبقي: {mins:02d}:{secs:02d}")
        else:
            st.warning("⏰ انتهت الجلسة، سيتم تسجيل الخروج.")
            logout_action()
        if st.button("🚪 تسجيل الخروج"):
            logout_action()
        return True

# -------------------------------
# 🔄 طرق جلب الملف من GitHub
# -------------------------------
def fetch_from_github_requests():
    """تحميل بإستخدام رابط RAW (requests)"""
    try:
        response = requests.get(GITHUB_EXCEL_URL, stream=True, timeout=20)
        response.raise_for_status()
        with open(LOCAL_FILE, "wb") as f:
            shutil.copyfileobj(response.raw, f)
        try:
            st.cache_data.clear()
        except:
            pass
        st.session_state["last_update"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        st.success("✅ تم تحديث البيانات من GitHub بنجاح وتم مسح الكاش.")
    except Exception as e:
        st.error(f"⚠ فشل التحديث من GitHub (requests): {e}")

def fetch_from_github_api():
    """تحميل عبر GitHub API (باستخدام PyGithub token في secrets)"""
    if not GITHUB_AVAILABLE:
        st.warning("PyGithub غير متوفر، سيتم المحاولة عبر رابط RAW.")
        fetch_from_github_requests()
        return
    try:
        token = st.secrets.get("github", {}).get("token", None)
        if not token:
            st.warning("توكين GitHub غير موجود في secrets، سيتم التحميل عبر رابط RAW.")
            fetch_from_github_requests()
            return
        g = Github(token)
        repo = g.get_repo(REPO_NAME)
        file_content = repo.get_contents(FILE_PATH, ref=BRANCH)
        content = b64decode(file_content.content)
        with open(LOCAL_FILE, "wb") as f:
            f.write(content)
        try:
            st.cache_data.clear()
        except:
            pass
        st.session_state["last_update"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        st.success("✅ تم تحميل الملف من GitHub API بنجاح.")
    except Exception as e:
        st.error(f"⚠ فشل تحميل الملف من GitHub API: {e}")

# -------------------------------
# 📂 تحميل الشيتات (بدون كاش)
# -------------------------------
def load_all_sheets_uncached():
    if not os.path.exists(LOCAL_FILE):
        return None
    sheets = pd.read_excel(LOCAL_FILE, sheet_name=None)
    for name, df in sheets.items():
        df.columns = df.columns.str.strip()
    return sheets

def load_sheets_for_edit_uncached():
    if not os.path.exists(LOCAL_FILE):
        return None
    sheets = pd.read_excel(LOCAL_FILE, sheet_name=None, dtype=object)
    for name, df in sheets.items():
        df.columns = df.columns.str.strip()
    return sheets

# (لأغراض أخرى يمكنك الاحتفاظ بـ cached versions إن أردت)
@st.cache_data(show_spinner=False)
def load_all_sheets_cached():
    return load_all_sheets_uncached()

@st.cache_data(show_spinner=False)
def load_sheets_for_edit_cached():
    return load_sheets_for_edit_uncached()

# -------------------------------
# 🔁 حفظ محلي + رفع على GitHub + إعادة تحميل
# -------------------------------
def save_local_excel_and_push(sheets_dict, commit_message="Update from Streamlit"):
    """يحفظ الملف محليًا، يحاول رفعه إلى GitHub إذا التوكين متاح، ثم يعيد تحميل الشيتات (غير مخزنة)."""
    # حفظ محليًا أولًا
    try:
        with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
            for name, sh in sheets_dict.items():
                try:
                    sh.to_excel(writer, sheet_name=name, index=False)
                except Exception:
                    sh.astype(object).to_excel(writer, sheet_name=name, index=False)
    except Exception as e:
        st.error(f"⚠ فشل في حفظ الملف محليًا: {e}")
        return load_sheets_for_edit_uncached()

    # مسح الكاش المحلي
    try:
        st.cache_data.clear()
    except:
        pass

    # جلب التوكين من secrets
    token = st.secrets.get("github", {}).get("token", None)
    if not token:
        st.warning("🔒 GitHub token not found in Streamlit secrets. التغييرات ستبقى محليًا فقط.")
        return load_sheets_for_edit_uncached()

    if not GITHUB_AVAILABLE:
        st.error("PyGithub غير مثبت على البيئة. التعديلات ستبقى محلياً.")
        return load_sheets_for_edit_uncached()

    # محاولة الرفع عبر API
    try:
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
        except Exception:
            # لو الملف غير موجود حاول إنشاءه
            try:
                repo.create_file(
                    path=FILE_PATH,
                    message=commit_message,
                    content=content,
                    branch=BRANCH
                )
            except Exception as e_create:
                st.error(f"⚠ فشل إنشاء الملف على GitHub: {e_create}")
                return load_sheets_for_edit_uncached()

        st.success("✅ تم الحفظ والرفع على GitHub بنجاح.")
        return load_sheets_for_edit_uncached()
    except Exception as e:
        st.error(f"⚠ فشل الاتصال بـ GitHub: {e}")
        return load_sheets_for_edit_uncached()

# -------------------------------
# 🔁 دالة لإعادة تحميل الشيتات داخل الجلسة فورًا
# -------------------------------
def reload_sheets_into_session():
    """يمسح الكاش ويعيد تحميل الشيتات من الملف المحلي إلى session_state."""
    try:
        st.cache_data.clear()
    except:
        pass
    st.session_state["all_sheets"] = load_all_sheets_uncached()
    st.session_state["sheets_edit"] = load_sheets_for_edit_uncached()
    st.session_state["last_update"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

# -------------------------------
# 🧰 دوال مساعدة للمعالجة والنصوص
# -------------------------------
def normalize_name(s):
    if s is None: return ""
    s = str(s).replace("\n", "+")
    s = re.sub(r"[^0-9a-zA-Z\u0600-\u06FF\+\s_/.-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

def split_needed_services(needed_service_str):
    if not isinstance(needed_service_str, str) or needed_service_str.strip() == "":
        return []
    parts = re.split(r"\+|,|\n|;", needed_service_str)
    return [p.strip() for p in parts if p.strip() != ""]

def highlight_cell(val, col_name):
    color_map = {
        "Service Needed": "background-color: #fff3cd; color:#856404; font-weight:bold;",
        "Done Services": "background-color: #d4edda; color:#155724; font-weight:bold;",
        "Not Done Services": "background-color: #f8d7da; color:#721c24; font-weight:bold;",
        "Last Date": "background-color: #e7f1ff; color:#004085; font-weight:bold;",
        "Last Tones": "background-color: #f0f0f0; color:#333; font-weight:bold;",
        "Other": "background-color: #e2f0d9; color:#2e6f32; font-weight:bold;",
        "Servised by": "background-color: #fdebd0; color:#7d6608; font-weight:bold;",
        "Min_Tons": "background-color: #ebf5fb; color:#154360; font-weight:bold;",
        "Max_Tons": "background-color: #f9ebea; color:#641e16; font-weight:bold;",
    }
    return color_map.get(col_name, "")

def style_table(row):
    return [highlight_cell(row[col], col) for col in row.index]

# -------------------------------
# 🖥 دالة فحص الماكينة
# -------------------------------
def check_machine_status(card_num, current_tons, all_sheets):
    if not all_sheets or "ServicePlan" not in all_sheets:
        st.error("❌ الملف لا يحتوي على شيت ServicePlan.")
        return
    service_plan_df = all_sheets["ServicePlan"]
    card_sheet_name = f"Card{card_num}"
    if card_sheet_name not in all_sheets:
        st.warning(f"⚠ لا يوجد شيت باسم {card_sheet_name}")
        return
    card_df = all_sheets[card_sheet_name]

    # نطاق العرض
    if "view_option" not in st.session_state:
        st.session_state.view_option = "الشريحة الحالية فقط"

    st.subheader("⚙ نطاق العرض")
    view_option = st.radio(
        "اختر نطاق العرض:",
        ("الشريحة الحالية فقط", "كل الشرائح الأقل", "كل الشرائح الأعلى", "نطاق مخصص", "كل الشرائح"),
        horizontal=True,
        key="view_option"
    )

    min_range = st.session_state.get("min_range", max(0, current_tons - 500))
    max_range = st.session_state.get("max_range", current_tons + 500)
    if view_option == "نطاق مخصص":
        col1, col2 = st.columns(2)
        with col1:
            min_range = st.number_input("من (طن):", min_value=0, step=100, value=min_range, key="min_range")
        with col2:
            max_range = st.number_input("إلى (طن):", min_value=min_range, step=100, value=max_range, key="max_range")

    # اختيار الشرائح
    if view_option == "الشريحة الحالية فقط":
        selected_slices = service_plan_df[(service_plan_df["Min_Tones"] <= current_tons) & (service_plan_df["Max_Tones"] >= current_tons)]
    elif view_option == "كل الشرائح الأقل":
        selected_slices = service_plan_df[service_plan_df["Max_Tones"] <= current_tons]
    elif view_option == "كل الشرائح الأعلى":
        selected_slices = service_plan_df[service_plan_df["Min_Tones"] >= current_tons]
    elif view_option == "نطاق مخصص":
        selected_slices = service_plan_df[(service_plan_df["Min_Tones"] >= min_range) & (service_plan_df["Max_Tones"] <= max_range)]
    else:
        selected_slices = service_plan_df.copy()

    if selected_slices.empty:
        st.warning("⚠ لا توجد شرائح مطابقة حسب النطاق المحدد.")
        return

    all_results = []
    for _, current_slice in selected_slices.iterrows():
        slice_min = current_slice["Min_Tones"]
        slice_max = current_slice["Max_Tones"]
        needed_service_raw = current_slice.get("Service", "")
        needed_parts = split_needed_services(needed_service_raw)
        needed_norm = [normalize_name(p) for p in needed_parts]

        mask = (card_df.get("Min_Tones", 0).fillna(0) <= slice_max) & (card_df.get("Max_Tones", 0).fillna(0) >= slice_min)
        matching_rows = card_df[mask]

        done_services_set = set()
        last_date = "-"
        last_tons = "-"
        last_other = "-"
        last_servised_by = "-"

        if not matching_rows.empty:
            ignore_cols = {"card", "Tones", "Min_Tones", "Max_Tones", "Date", "Other", "Servised by"}
            for _, r in matching_rows.iterrows():
                for col in matching_rows.columns:
                    if col not in ignore_cols:
                        val = str(r.get(col, "")).strip()
                        if val and val.lower() not in ["nan", "none", ""]:
                            done_services_set.add(col)
            # قراءة آخر تاريخ
            if "Date" in matching_rows.columns:
                try:
                    cleaned_dates = matching_rows["Date"].astype(str).str.replace("\\", "/", regex=False)
                    dates = pd.to_datetime(cleaned_dates, errors="coerce", dayfirst=True)
                    if dates.notna().any():
                        idx = dates.idxmax()
                        last_date = dates.loc[idx].strftime("%d/%m/%Y")
                except:
                    last_date = "-"
            # آخر طن
            if "Tones" in matching_rows.columns:
                tons_vals = pd.to_numeric(matching_rows["Tones"], errors="coerce")
                if tons_vals.notna().any():
                    last_tons = int(tons_vals.max())
            # Other
            if "Other" in matching_rows.columns:
                last_other = str(matching_rows["Other"].dropna().iloc[-1]) if matching_rows["Other"].notna().any() else "-"
            # Servised by
            if "Servised by" in matching_rows.columns:
                last_servised_by = str(matching_rows["Servised by"].dropna().iloc[-1]) if matching_rows["Servised by"].notna().any() else "-"

        done_services = sorted(list(done_services_set))
        done_norm = [normalize_name(c) for c in done_services]
        not_done = [orig for orig, n in zip(needed_parts, needed_norm) if n not in done_norm]

        all_results.append({
            "Min_Tons": slice_min,
            "Max_Tons": slice_max,
            "Service Needed": " + ".join(needed_parts) if needed_parts else "-",
            "Done Services": ", ".join(done_services) if done_services else "-",
            "Not Done Services": ", ".join(not_done) if not_done else "-",
            "Last Date": last_date,
            "Last Tones": last_tons,
            "Other": last_other,
            "Servised by": last_servised_by
        })

    result_df = pd.DataFrame(all_results).dropna(how="all").reset_index(drop=True)

    st.markdown("### 📋 نتائج الفحص")
    st.dataframe(result_df.style.apply(style_table, axis=1), use_container_width=True)

    # تنزيل النتائج
    buffer = io.BytesIO()
    result_df.to_excel(buffer, index=False, engine="openpyxl")
    st.download_button(
        label="💾 حفظ النتائج كـ Excel",
        data=buffer.getvalue(),
        file_name=f"Service_Report_Card{card_num}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# -------------------------------
# 🖥 الواجهة الرئيسية
# -------------------------------
st.set_page_config(page_title="CMMS - Bail Yarn", layout="wide")

# شريط تسجيل الدخول / أدوات
with st.sidebar:
    st.header("👤 الجلسة")
    if not st.session_state.get("logged_in"):
        if not login_ui():
            st.stop()
    else:
        state = cleanup_sessions(load_state())
        username = st.session_state.username
        rem = remaining_time(state, username)
        if rem:
            mins, secs = divmod(int(rem.total_seconds()), 60)
            st.success(f"👋 {username} | ⏳ {mins:02d}:{secs:02d}")
        else:
            logout_action()

    st.markdown("---")
    st.write("🔧 أدوات:")
    if st.button("🔄 تحديث الملف من GitHub (RAW)"):
        fetch_from_github_requests()
        # بعد التحميل اعادة تحميل الجلسة فورًا
        reload_sheets_into_session()
        st.rerun()
    if st.button("🔄 تحديث الملف من GitHub (API)"):
        fetch_from_github_api()
        reload_sheets_into_session()
        st.rerun()
    st.markdown("ملحوظة: تحميل الـ RAW يعمل بدون توكين، لكن الرفع يحتاج توكين في secrets.")
    st.markdown("---")
    if st.button("🚪 تسجيل الخروج"):
        logout_action()

# -------------------------------
# تحميل أولي للشيتات داخل session_state
# -------------------------------
if "all_sheets" not in st.session_state:
    st.session_state["all_sheets"] = load_all_sheets_uncached()
if "sheets_edit" not in st.session_state:
    st.session_state["sheets_edit"] = load_sheets_for_edit_uncached()

all_sheets = st.session_state.get("all_sheets")
sheets_edit = st.session_state.get("sheets_edit")

# الواجهة الرئيسية: Tabs
st.title("🏭 CMMS - Bail Yarn")
tabs = st.tabs(["📊 عرض وفحص الماكينات", "🛠 تعديل وإدارة البيانات (GitHub)","⚙ إدارة المستخدمين"])

# -------------------------------
# Tab 1: عرض وفحص الماكينات
# -------------------------------
with tabs[0]:
    st.header("📊 عرض وفحص الماكينات")
    if all_sheets is None:
        st.warning("❗ الملف المحلي غير موجود. استخدم أحد أزرار التحديث في الشريط الجانبي لتحميل الملف من GitHub.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            card_num = st.number_input("رقم الماكينة:", min_value=1, step=1, key="card_num_main")
        with col2:
            current_tons = st.number_input("عدد الأطنان الحالية:", min_value=0, step=100, key="current_tons_main")

        if st.button("عرض الحالة"):
            st.session_state["show_results"] = True

        if st.session_state.get("show_results", False):
            check_machine_status(st.session_state.card_num_main, st.session_state.current_tons_main, all_sheets)

# -------------------------------
# Tab 2: تعديل وإدارة البيانات
# -------------------------------
with tabs[1]:
    st.header("🛠 تعديل وإدارة البيانات (GitHub)")

    username = st.session_state.get("username")
    token_exists = bool(st.secrets.get("github", {}).get("token", None))
    can_push = (username == "admin") or (token_exists and GITHUB_AVAILABLE)

    if sheets_edit is None:
        st.warning("❗ الملف المحلي غير موجود. اضغط تحديث من GitHub في الشريط الجانبي أولًا.")
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "عرض وتعديل شيت",
            "إضافة صف جديد (أحداث متتالية)",
            "إضافة عمود جديد",
            "🗑 حذف صف"
        ])

        # Tab1 - تعديل وعرض
        with tab1:
            st.subheader("✏ تعديل البيانات")
            sheet_name = st.selectbox("اختر الشيت:", list(sheets_edit.keys()), key="edit_sheet")
            df = sheets_edit[sheet_name].astype(str)

            edited_df = st.data_editor(df, num_rows="dynamic")

            if st.button("💾 حفظ التعديلات", key=f"save_edit_{sheet_name}"):
                if not can_push:
                    st.warning("🚫 لا تملك صلاحية الرفع إلى GitHub من هذه الجلسة.")
                sheets_edit[sheet_name] = edited_df.astype(object)

                # حفظ ورفع
                _ = save_local_excel_and_push(
                    sheets_edit,
                    commit_message=f"Edit sheet {sheet_name} by {st.session_state.get('username')}"
                )

                # إعادة تحميل الجلسة وعرض التغيرات
                reload_sheets_into_session()
                st.success("✅ تم حفظ التعديلات. جاري تحديث العرض...")
                st.rerun()

        # Tab2 - إضافة صف
        with tab2:
            st.subheader("➕ إضافة صف جديد (سجل حدث جديد داخل نفس الرينج)")
            sheet_name_add = st.selectbox("اختر الشيت لإضافة صف:", list(sheets_edit.keys()), key="add_sheet")
            df_add = sheets_edit[sheet_name_add].astype(str).reset_index(drop=True)
            st.markdown("أدخل بيانات الحدث (يمكنك إدخال أي نص/أرقام/تواريخ)")

            new_data = {}
            for col in df_add.columns:
                new_data[col] = st.text_input(f"{col}", key=f"add_{sheet_name_add}_{col}")

            if st.button("💾 إضافة الصف الجديد", key=f"add_row_{sheet_name_add}"):

                new_row_df = pd.DataFrame([new_data]).astype(str)

                # البحث عن أعمدة الرينج
                min_col, max_col, card_col = None, None, None
                for c in df_add.columns:
                    c_low = c.strip().lower()
                    if c_low in ("min_tones", "min_tone", "min tones", "min"):
                        min_col = c
                    if c_low in ("max_tones", "max_tone", "max tones", "max"):
                        max_col = c
                    if c_low in ("card", "machine", "machine_no", "machine id"):
                        card_col = c

                if not min_col or not max_col:
                    st.error("⚠ لم يتم العثور على أعمدة Min_Tones و/أو Max_Tones في الشيت.")
                else:
                    def to_num_or_none(x):
                        try:
                            return float(x)
                        except:
                            return None

                    new_min_raw = str(new_data.get(min_col, "")).strip()
                    new_max_raw = str(new_data.get(max_col, "")).strip()
                    new_min_num = to_num_or_none(new_min_raw)
                    new_max_num = to_num_or_none(new_max_raw)

                    # البحث عن موضع الإدراج
                    insert_pos = len(df_add)
                    mask = pd.Series([False] * len(df_add))

                    if card_col:
                        new_card = str(new_data.get(card_col, "")).strip()
                        if new_card != "":
                            if new_min_num is not None and new_max_num is not None:
                                mask = (
                                    (df_add[card_col].astype(str).str.strip() == new_card) &
                                    (pd.to_numeric(df_add[min_col], errors='coerce') == new_min_num) &
                                    (pd.to_numeric(df_add[max_col], errors='coerce') == new_max_num)
                                )
                            else:
                                mask = (
                                    (df_add[card_col].astype(str).str.strip() == new_card) &
                                    (df_add[min_col].astype(str).str.strip() == new_min_raw) &
                                    (df_add[max_col].astype(str).str.strip() == new_max_raw)
                                )
                    else:
                        if new_min_num is not None and new_max_num is not None:
                            mask = (
                                (pd.to_numeric(df_add[min_col], errors='coerce') == new_min_num) &
                                (pd.to_numeric(df_add[max_col], errors='coerce') == new_max_num)
                            )
                        else:
                            mask = (
                                (df_add[min_col].astype(str).str.strip() == new_min_raw) &
                                (df_add[max_col].astype(str).str.strip() == new_max_raw)
                            )

                    if mask.any():
                        insert_pos = mask[mask].index[-1] + 1
                    else:
                        try:
                            df_add["_min_num"] = pd.to_numeric(df_add[min_col], errors='coerce').fillna(-1)
                            if new_min_num is not None:
                                insert_pos = int((df_add["_min_num"] < new_min_num).sum())
                            else:
                                insert_pos = len(df_add)
                            df_add = df_add.drop(columns=["_min_num"])
                        except Exception:
                            insert_pos = len(df_add)

                    df_top = df_add.iloc[:insert_pos].reset_index(drop=True)
                    df_bottom = df_add.iloc[insert_pos:].reset_index(drop=True)
                    df_new = pd.concat(
                        [df_top, new_row_df.reset_index(drop=True), df_bottom],
                        ignore_index=True
                    )

                    sheets_edit[sheet_name_add] = df_new.astype(object)

                    if not can_push:
                        st.warning("🚫 لا تملك صلاحية الرفع (التغييرات ستبقى محلياً).")
                        # فقط اكتب الملف محلياً
                        with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
                            for name, sh in sheets_edit.items():
                                try:
                                    sh.to_excel(writer, sheet_name=name, index=False)
                                except:
                                    sh.astype(object).to_excel(writer, sheet_name=name, index=False)
                        # reload & rerun
                        reload_sheets_into_session()
                        st.success("✅ تم إدراج الصف محليًا (لم يتم رفعه إلى GitHub).")
                        st.rerun()
                    else:
                        _ = save_local_excel_and_push(
                            sheets_edit,
                            commit_message=f"Add new row under range {new_min_raw}-{new_max_raw} in {sheet_name_add} by {st.session_state.get('username')}"
                        )
                        reload_sheets_into_session()
                        st.success("✅ تم الإضافة — تم إدراج الصف في الموقع المناسب.")
                        st.rerun()

        # Tab3 - إضافة عمود
        with tab3:
            st.subheader("🆕 إضافة عمود جديد")
            sheet_name_col = st.selectbox("اختر الشيت لإضافة عمود:", list(sheets_edit.keys()), key="add_col_sheet")
            df_col = sheets_edit[sheet_name_col].astype(str)
            new_col_name = st.text_input("اسم العمود الجديد:")
            default_value = st.text_input("القيمة الافتراضية لكل الصفوف (اختياري):", "")

            if st.button("💾 إضافة العمود الجديد", key=f"add_col_{sheet_name_col}"):
                if new_col_name:
                    df_col[new_col_name] = default_value
                    sheets_edit[sheet_name_col] = df_col.astype(object)
                    if not can_push:
                        with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
                            for name, sh in sheets_edit.items():
                                try:
                                    sh.to_excel(writer, sheet_name=name, index=False)
                                except:
                                    sh.astype(object).to_excel(writer, sheet_name=name, index=False)
                        reload_sheets_into_session()
                        st.success("✅ تم إضافة العمود محليًا (لم يتم رفعه إلى GitHub).")
                        st.rerun()
                    else:
                        _ = save_local_excel_and_push(
                            sheets_edit,
                            commit_message=f"Add new column '{new_col_name}' to {sheet_name_col} by {st.session_state.get('username')}"
                        )
                        reload_sheets_into_session()
                        st.success("✅ تم إضافة العمود الجديد بنجاح!")
                        st.rerun()
                else:
                    st.warning("⚠ الرجاء إدخال اسم العمود الجديد.")

        # Tab4 - حذف صف
        with tab4:
            st.subheader("🗑 حذف صف من الشيت")
            sheet_name_del = st.selectbox("اختر الشيت:", list(sheets_edit.keys()), key="delete_sheet")
            df_del = sheets_edit[sheet_name_del].astype(str).reset_index(drop=True)

            st.markdown("### 📋 بيانات الشيت الحالية")
            st.dataframe(df_del)

            st.markdown("### ✏ اختر الصفوف التي تريد حذفها (برقم الصف):")
            st.write("💡 ملاحظة: رقم الصف يبدأ من 0 (أول صف = 0)")

            rows_to_delete = st.text_input("أدخل أرقام الصفوف مفصولة بفاصلة (مثلاً: 0,2,5):")
            confirm_delete = st.checkbox("✅ أؤكد أني أريد حذف هذه الصفوف بشكل نهائي")

            if st.button("🗑 تنفيذ الحذف", key=f"delete_rows_{sheet_name_del}"):
                if rows_to_delete.strip() == "":
                    st.warning("⚠ الرجاء إدخال رقم الصف أو أكثر.")
                elif not confirm_delete:
                    st.warning("⚠ برجاء تأكيد الحذف أولاً بوضع علامة ✅ قبل التنفيذ.")
                else:
                    try:
                        rows_list = [int(x.strip()) for x in rows_to_delete.split(",") if x.strip().isdigit()]
                        rows_list = [r for r in rows_list if 0 <= r < len(df_del)]

                        if not rows_list:
                            st.warning("⚠ لم يتم العثور على صفوف صحيحة.")
                        else:
                            df_new = df_del.drop(rows_list).reset_index(drop=True)
                            sheets_edit[sheet_name_del] = df_new.astype(object)

                            if not can_push:
                                with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
                                    for name, sh in sheets_edit.items():
                                        try:
                                            sh.to_excel(writer, sheet_name=name, index=False)
                                        except:
                                            sh.astype(object).to_excel(writer, sheet_name=name, index=False)
                                reload_sheets_into_session()
                                st.success(f"✅ تم حذف الصفوف التالية محليًا: {rows_list}")
                                st.rerun()
                            else:
                                _ = save_local_excel_and_push(sheets_edit, commit_message=f"Delete rows {rows_list} from {sheet_name_del} by {st.session_state.get('username')}")
                                reload_sheets_into_session()
                                st.success(f"✅ تم حذف الصفوف التالية بنجاح: {rows_list}")
                                st.rerun()
                    except Exception as e:
                        st.error(f"حدث خطأ أثناء الحذف: {e}")

# -------------------------------
# Tab 3: إدارة المستخدمين
# -------------------------------
with tabs[2]:
    st.header("⚙ إدارة المستخدمين")
    users = load_users()
    username = st.session_state.get("username")

    if username != "admin":
        st.info("🛑 فقط المستخدم 'admin' يمكنه إدارة المستخدمين عبر هذه الواجهة. تواصل مع المدير لإجراء تغييرات.")
        st.markdown("المستخدمين الحاليين:")
        st.write(list(users.keys()))
    else:
        st.subheader("🔐 المستخدمين الموجودين")
        st.dataframe(pd.DataFrame([{"username": k, "password": v.get("password","")} for k,v in users.items()]))
        st.markdown("### ➕ إضافة مستخدم جديد")
        new_user = st.text_input("اسم المستخدم الجديد:")
        new_pass = st.text_input("كلمة المرور:", type="password")
        if st.button("إضافة مستخدم"):
            if new_user.strip() == "" or new_pass.strip() == "":
                st.warning("الرجاء إدخال اسم وكلمة مرور.")
            else:
                if new_user in users:
                    st.warning("هذا المستخدم موجود بالفعل.")
                else:
                    users[new_user] = {"password": new_pass}
                    save_users(users)
                    st.success("✅ تم إضافة المستخدم.")
                    st.rerun()

        st.markdown("### 🗑 حذف مستخدم")
        del_user = st.selectbox("اختر مستخدم للحذف:", [u for u in users.keys() if u != "admin"])
        if st.button("حذف المستخدم"):
            if del_user in users:
                users.pop(del_user, None)
                save_users(users)
                st.success("✅ تم الحذف.")
                st.rerun()
