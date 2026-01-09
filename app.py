import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time as dtime
import os

st.set_page_config(page_title="Fault Card Analyzer", layout="wide")

# ------------------------
# وظيفة تحميل البيانات من ملف النص
# ------------------------
@st.cache_data
def load_text_file(file_path):
    """
    تحميل البيانات من ملف النص مع تخطي الخطوط غير الضرورية
    """
    data = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as file:
            lines = file.readlines()
    
    for line in lines:
        # تخطي الخطوط الفارغة أو التي تبدأ بـ "=" أو لا تحتوي على بيانات
        if line.startswith("=") or line.strip() == "":
            continue
        
        # تقسيم البيانات (يمكن تعديل الفاصل حسب تنسيق ملفك)
        parts = line.split("\t") if "\t" in line else line.split(",")
        
        # تأكد من أن لدينا 4 أعمدة على الأقل
        while len(parts) < 4:
            parts.append("")
        
        # تنظيف البيانات
        cleaned_parts = [part.strip() for part in parts[:4]]
        data.append(cleaned_parts)
    
    # إنشاء DataFrame
    df = pd.DataFrame(data, columns=["Date", "Time", "Event", "Details"])
    
    # دمج التاريخ والوقت في عمود DateTime
    df['DateTime'] = pd.to_datetime(
        df['Date'].astype(str) + ' ' + df['Time'].astype(str),
        dayfirst=True,
        errors='coerce'
    )
    
    # حذف الصفوف التي تحتوي على قيم ناقصة في DateTime
    df = df.dropna(subset=['DateTime']).sort_values('DateTime').reset_index(drop=True)
    
    return df

# ------------------------
# واجهة رفع الملف
# ------------------------
st.title("🧾 Fault Card Analyzer - تحليل تفاعلي (MTTR / MTBF)")

st.sidebar.header("📁 تحميل البيانات")
upload_option = st.sidebar.radio("اختر مصدر البيانات:", 
                                  ["رفع ملف جديد", "استخدام ملف محفوظ مسبقاً"])

if upload_option == "رفع ملف جديد":
    uploaded_file = st.sidebar.file_uploader("اختر ملف السجل (txt أو csv أو xlsx)", 
                                           type=['txt', 'csv', 'xlsx'])
    
    if uploaded_file is not None:
        # حفظ الملف المؤقت
        temp_path = f"temp_uploaded_file.{uploaded_file.name.split('.')[-1]}"
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        # تحميل البيانات حسب نوع الملف
        if uploaded_file.name.endswith('.txt'):
            df = load_text_file(temp_path)
        elif uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(temp_path)
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(temp_path)
        
        # إنشاء عمود DateTime إذا لم يكن موجوداً
        if 'DateTime' not in df.columns:
            if 'Date' in df.columns and 'Time' in df.columns:
                df['DateTime'] = pd.to_datetime(
                    df['Date'].astype(str) + ' ' + df['Time'].astype(str),
                    dayfirst=True,
                    errors='coerce'
                )
            else:
                st.error("الملف يجب أن يحتوي على أعمدة التاريخ والوقت")
                st.stop()
        
        st.sidebar.success(f"✅ تم تحميل {len(df)} سجل")
        
        # حفظ البيانات في الجلسة
        st.session_state['dataframe'] = df
        
        # تنظيف الملف المؤقت
        if os.path.exists(temp_path):
            os.remove(temp_path)
else:
    # استخدام مسار افتراضي
    default_path = r"C:\Users\LAP ME\Desktop\داتا ساينس دبلومه\projects\card12 data\Logbook_20241225.txt"
    
    if st.sidebar.button("تحميل من المسار الافتراضي"):
        if os.path.exists(default_path):
            df = load_text_file(default_path)
            st.session_state['dataframe'] = df
            st.sidebar.success(f"✅ تم تحميل {len(df)} سجل")
        else:
            st.sidebar.error("❌ الملف الافتراضي غير موجود")

# التحقق من وجود البيانات
if 'dataframe' not in st.session_state:
    st.warning("⚠️ يرجى تحميل ملف البيانات أولاً من الشريط الجانبي")
    st.stop()

df = st.session_state['dataframe']

# ------------------------
# عرض عينة من البيانات
# ------------------------
with st.expander("👁️ عرض عينة من البيانات", expanded=False):
    st.write(f"عدد السجلات الكلي: {len(df)}")
    st.dataframe(df.head(100))
    
    # إحصائيات عن الأحداث
    st.subheader("📊 إحصائيات الأحداث")
    event_counts = df['Event'].value_counts().head(20)
    st.bar_chart(event_counts)

# ------------------------
# واجهة اختيار الحدث
# ------------------------
st.header("🔧 إعدادات التحليل")

col1, col2 = st.columns([2, 1])

with col1:
    all_events = sorted(df['Event'].dropna().unique().tolist())
    selected_event = st.selectbox("اختر نوع العطل من القائمة:", 
                                 options=all_events,
                                 help="اختر الحدث الذي تريد تحليل تكراراته وأوقات الإصلاح")
    
    manual_event = st.text_input("أو اكتب اسم العطل يدويًا:", 
                                value="",
                                help="يمكنك كتابة اسم عطل غير موجود في القائمة")

with col2:
    reference_event = st.selectbox("اختر الحدث المرجعي (وضع التشغيل):", 
                                  options=all_events, 
                                  index=all_events.index('Automatic mode') if 'Automatic mode' in all_events else 0,
                                  help="الحدث الذي يدل على انتهاء الإصلاح والعودة للتشغيل")

# اختيار الحدث للتحليل
event_to_use = manual_event.strip() if manual_event.strip() != "" else selected_event

# ------------------------
# نطاق زمني للتحليل
# ------------------------
st.markdown("### ⏰ تحديد النطاق الزمني")
col3, col4 = st.columns(2)

with col3:
    min_date = df['DateTime'].dt.date.min()
    max_date = df['DateTime'].dt.date.max()
    
    date_from = st.date_input("من تاريخ:", 
                             value=min_date,
                             min_value=min_date,
                             max_value=max_date)

with col4:
    date_to = st.date_input("إلى تاريخ:", 
                           value=max_date,
                           min_value=min_date,
                           max_value=max_date)

# اختيار وقت إضافي
col5, col6 = st.columns(2)
with col5:
    time_from = st.time_input("وقت البداية (اختياري):", 
                             value=dtime(0, 0))
with col6:
    time_to = st.time_input("وقت النهاية (اختياري):", 
                           value=dtime(23, 59))

# بناء تواريخ كاملة
dt_from = datetime.combine(date_from, time_from)
dt_to = datetime.combine(date_to, time_to)

st.info(f"**النطاق الزمني:** {dt_from.strftime('%Y-%m-%d %H:%M')} → {dt_to.strftime('%Y-%m-%d %H:%M')}")

# ------------------------
# زر التنفيذ
# ------------------------
if st.button("🔎 بدء التحليل", type="primary", use_container_width=True):
    
    with st.spinner("جاري تحليل البيانات..."):
        # تصفية النطاق الزمني
        df_range = df[(df['DateTime'] >= dt_from) & (df['DateTime'] <= dt_to)].copy()
        
        if df_range.empty:
            st.error("لا توجد سجلات داخل النطاق الزمني المختار.")
            st.stop()
        
        # استخراج الأعطال والأحداث المرجعية
        failures = df_range[df_range['Event'].str.contains(event_to_use, 
                                                          case=False, 
                                                          na=False)].copy()
        refs = df_range[df_range['Event'] == reference_event].copy()
        
        st.write(f"""
        **ملخص العينات:**
        - السجلات الكلية في النطاق: **{len(df_range)}**
        - حالات العطل المختار ('{event_to_use}'): **{len(failures)}**
        - أحداث المرجع ('{reference_event}'): **{len(refs)}**
        """)
        
        if failures.empty:
            st.warning("لم يتم العثور على أي حالات للعطل المحدد ضمن النطاق.")
            st.stop()
        
        # ------------------------
        # حساب MTTR
        # ------------------------
        if not refs.empty:
            # ربط كل عطل بأقرب مرجع بعده
            failures = failures.sort_values('DateTime').reset_index(drop=True)
            
            def find_next_ref(failure_time):
                later_refs = refs[refs['DateTime'] > failure_time]
                if not later_refs.empty:
                    return later_refs['DateTime'].min()
                return pd.NaT
            
            failures['Next_Ref_Time'] = failures['DateTime'].apply(find_next_ref)
            failures['Repair_Min'] = (failures['Next_Ref_Time'] - failures['DateTime']).dt.total_seconds() / 60
            
            # MTTR: متوسط وقت الإصلاح
            valid_repairs = failures['Repair_Min'].dropna()
            if not valid_repairs.empty:
                mttr = valid_repairs.mean()
                mttr_median = valid_repairs.median()
                mttr_std = valid_repairs.std()
            else:
                mttr = mttr_median = mttr_std = np.nan
        else:
            st.warning(f"⚠️ لا توجد سجلات للحدث المرجعي '{reference_event}' داخل النطاق.")
            failures['Repair_Min'] = np.nan
            mttr = mttr_median = mttr_std = np.nan
        
        # ------------------------
        # حساب MTBF
        # ------------------------
        failures = failures.sort_values('DateTime').reset_index(drop=True)
        failures['Prev_Failure'] = failures['DateTime'].shift(1)
        failures['Time_Between_Min'] = (failures['DateTime'] - failures['Prev_Failure']).dt.total_seconds() / 60
        
        # MTBF: متوسط الوقت بين الأعطال
        valid_between = failures['Time_Between_Min'].dropna()
        if not valid_between.empty:
            mtbf = valid_between.mean()
            mtbf_median = valid_between.median()
            mtbf_std = valid_between.std()
        else:
            mtbf = mtbf_median = mtbf_std = np.nan
        
        # ------------------------
        # عرض النتائج
        # ------------------------
        st.success("✅ تم الانتهاء من التحليل!")
        
        # مؤشرات الأداء
        st.header("📊 مؤشرات الأداء الرئيسية")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if not np.isnan(mttr):
                st.metric("⏱ MTTR (متوسط وقت الإصلاح)", 
                         f"{mttr:.1f} دقيقة",
                         delta=f"الوسيط: {mttr_median:.1f} دقيقة")
                st.caption(f"الانحراف المعياري: {mttr_std:.1f} دقيقة")
            else:
                st.metric("⏱ MTTR", "غير متاح")
        
        with col_b:
            if not np.isnan(mtbf):
                st.metric("⚙ MTBF (متوسط الوقت بين الأعطال)", 
                         f"{mtbf:.1f} دقيقة",
                         delta=f"الوسيط: {mtbf_median:.1f} دقيقة")
                st.caption(f"الانحراف المعياري: {mtbf_std:.1f} دقيقة")
            else:
                st.metric("⚙ MTBF", "غير متاح")
        
        # ------------------------
        # إحصائيات إضافية
        # ------------------------
        st.header("📈 إحصائيات تفصيلية")
        
        col_c, col_d, col_e = st.columns(3)
        
        with col_c:
            st.info(f"**عدد الأعطال:** {len(failures)}")
        
        with col_d:
            if not failures['Repair_Min'].isna().all():
                min_repair = failures['Repair_Min'].min()
                max_repair = failures['Repair_Min'].max()
                st.info(f"**أقل/أكثر وقت إصلاح:** {min_repair:.1f} / {max_repair:.1f} دقيقة")
        
        with col_e:
            if 'Time_Between_Min' in failures.columns and not failures['Time_Between_Min'].isna().all():
                min_between = failures['Time_Between_Min'].min()
                max_between = failures['Time_Between_Min'].max()
                st.info(f"**أقل/أكثر وقت بين الأعطال:** {min_between:.1f} / {max_between:.1f} دقيقة")
        
        # ------------------------
        # عرض جدول التفاصيل
        # ------------------------
        st.header("🧾 تفاصيل الأعطال")
        
        # تنسيق الأعمدة للعرض
        display_df = failures.copy()
        display_df['DateTime'] = display_df['DateTime'].dt.strftime('%Y-%m-%d %H:%M')
        display_df['Next_Ref_Time'] = display_df['Next_Ref_Time'].dt.strftime('%Y-%m-%d %H:%M')
        
        # أعمدة للعرض
        show_cols = []
        for col in ['DateTime', 'Event', 'Details', 'Next_Ref_Time', 'Repair_Min', 'Time_Between_Min']:
            if col in display_df.columns:
                show_cols.append(col)
        
        st.dataframe(
            display_df[show_cols].head(100),
            use_container_width=True,
            height=400
        )
        
        # ------------------------
        # خيارات التصدير
        # ------------------------
        st.header("💾 حفظ النتائج")
        
        col_f, col_g = st.columns(2)
        
        with col_f:
            # تصدير إلى Excel
            if st.button("📥 حفظ إلى Excel", use_container_width=True):
                try:
                    output_path = "fault_analysis_results.xlsx"
                    failures.to_excel(output_path, index=False)
                    st.success(f"تم الحفظ بنجاح: {output_path}")
                    
                    # عرض رابط التحميل
                    with open(output_path, "rb") as file:
                        st.download_button(
                            label="📥 تنزيل الملف",
                            data=file,
                            file_name="fault_analysis_results.xlsx",
                            mime="application/vnd.ms-excel"
                        )
                except Exception as e:
                    st.error(f"خطأ في الحفظ: {e}")
        
        with col_g:
            # تصدير إلى CSV
            if st.button("📊 حفظ إلى CSV", use_container_width=True):
                try:
                    output_path = "fault_analysis_results.csv"
                    failures.to_csv(output_path, index=False, encoding='utf-8-sig')
                    st.success(f"تم الحفظ بنجاح: {output_path}")
                    
                    with open(output_path, "rb") as file:
                        st.download_button(
                            label="📥 تنزيل الملف",
                            data=file,
                            file_name="fault_analysis_results.csv",
                            mime="text/csv"
                        )
                except Exception as e:
                    st.error(f"خطأ في الحفظ: {e}")
        
        # ------------------------
        # تصور بياني
        # ------------------------
        st.header("📊 تصور بياني للبيانات")
        
        if len(failures) > 1:
            tab1, tab2, tab3 = st.tabs(["أوقات الإصلاح", "الوقت بين الأعطال", "توزيع الأعطال"])
            
            with tab1:
                if not failures['Repair_Min'].isna().all():
                    st.bar_chart(failures.set_index('DateTime')['Repair_Min'])
            
            with tab2:
                if 'Time_Between_Min' in failures.columns and not failures['Time_Between_Min'].isna().all():
                    st.line_chart(failures.set_index('DateTime')['Time_Between_Min'])
            
            with tab3:
                # توزيع الأعطال على مدار اليوم
                failures['Hour'] = pd.to_datetime(failures['DateTime']).dt.hour
                hourly_counts = failures['Hour'].value_counts().sort_index()
                st.bar_chart(hourly_counts)
