import streamlit as st
import pandas as pd
from datetime import timedelta
from io import BytesIO
import base64

# تهيئة إعدادات الصفحة
st.set_page_config(
    page_title="عرض بيانات السجل التقني",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# إضافة CSS مخصص لتحسين المظهر
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1E3A8A;
        padding: 20px 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 30px;
    }
    .stDataFrame {
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .highlight-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 10px 0;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    .downtime-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .upload-box {
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        margin: 20px 0;
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# عنوان التطبيق
st.markdown('<div class="main-header"><h1>📋 نظام عرض وتحليل بيانات السجل التقني</h1><h3>عرض وتحليل بيانات أعطال المعدات + حساب أوقات التوقف</h3></div>', unsafe_allow_html=True)

# الشريط الجانبي لتحميل الملف
with st.sidebar:
    st.markdown("### 📁 تحميل البيانات")
    
    # خيار رفع الملف
    uploaded_file = st.file_uploader(
        "رفع ملف البيانات (Excel أو CSV)",
        type=['xlsx', 'xls', 'csv'],
        help="يمكنك رفع ملف Excel (.xlsx, .xls) أو ملف CSV"
    )
    
    # زر تحميل البيانات التجريبية
    use_sample_data = st.checkbox("استخدام بيانات تجريبية", value=False)
    
    # زر تحديث
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    st.markdown("#### ⚙️ إعدادات العرض")
    
    # خيارات عرض البيانات
    show_stats = st.checkbox("عرض الإحصائيات", value=True)
    show_downtime = st.checkbox("حساب أوقات التوقف", value=True)
    
    st.markdown("---")
    st.markdown("#### ℹ️ معلومات:")
    st.info("""
    **مميزات التطبيق:**
    - رفع ملفات Excel أو CSV
    - عرض كامل للبيانات
    - إحصائيات تفصيلية
    - حساب أوقات التوقف
    - تصدير للعديد من الصيغ
    """)

# دالة لتحميل البيانات من الملف المرفوع
@st.cache_data
def load_data(uploaded_file=None, use_sample=False):
    """
    تحميل البيانات من الملف المرفوع أو استخدام بيانات تجريبية
    """
    if uploaded_file is not None:
        try:
            # تحديد نوع الملف وتحويله
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:  # Excel files
                df = pd.read_excel(uploaded_file)
            
            st.sidebar.success(f"✅ تم تحميل {len(df)} سجل من {uploaded_file.name}")
            return df
            
        except Exception as e:
            st.sidebar.error(f"❌ خطأ في تحميل الملف: {e}")
            return None
    
    elif use_sample:
        # إنشاء بيانات تجريبية للعرض
        num_records = 100
        sample_data = {
            "Date": pd.date_range(start="2024-01-01", periods=num_records, freq='H').strftime('%Y-%m-%d'),
            "Time": [f"{i%24:02d}:{(i*30)%60:02d}" for i in range(num_records)],
            "Event": (["Automatic mode", "Manual mode", "Error 001", "Maintenance", 
                     "System Reset", "Error 002", "Calibration", "Error 003"] * 13)[:num_records],
            "Details": [f"تفاصيل السجل رقم {i+1}" for i in range(num_records)]
        }
        df = pd.DataFrame(sample_data)
        st.sidebar.warning("⚠️ يتم عرض بيانات تجريبية")
        return df
    
    else:
        return None

# دالة لتحضير البيانات
def prepare_data(df):
    """
    تحضير البيانات وإنشاء عمود DateTime
    """
    if df is None or len(df) == 0:
        return None
    
    df_clean = df.copy()
    
    # محاولة إنشاء عمود DateTime من Date و Time
    try:
        if 'DateTime' in df_clean.columns:
            df_clean['DateTime'] = pd.to_datetime(df_clean['DateTime'], errors='coerce')
        elif 'Date' in df_clean.columns and 'Time' in df_clean.columns:
            df_clean['DateTime'] = pd.to_datetime(
                df_clean['Date'].astype(str) + ' ' + df_clean['Time'].astype(str),
                errors='coerce'
            )
        elif 'Date' in df_clean.columns:
            df_clean['DateTime'] = pd.to_datetime(df_clean['Date'], errors='coerce')
        
        # إزالة الصفوف التي تحتوي على قيم ناقصة في DateTime
        df_clean = df_clean.dropna(subset=['DateTime']).copy()
        
    except Exception as e:
        st.warning(f"⚠️ تعذر إنشاء عمود التاريخ والوقت: {e}")
    
    return df_clean

# دالة لحساب مدة التوقف
def calculate_downtime(df, event_name, reference_event="Automatic mode"):
    """
    حساب إجمالي مدة التوقف لحدث معين
    """
    if df is None or 'DateTime' not in df.columns:
        return 0, 0, []
    
    # فرز البيانات حسب الوقت
    df_sorted = df.sort_values('DateTime').reset_index(drop=True)
    
    # البحث عن أحداث التوقف وأحداث المرجع
    downtime_events = df_sorted[df_sorted['Event'].str.contains(event_name, case=False, na=False)]
    reference_events = df_sorted[df_sorted['Event'].str.contains(reference_event, case=False, na=False)]
    
    if len(downtime_events) == 0 or len(reference_events) == 0:
        return 0, len(downtime_events), []
    
    # حساب مدة كل توقف
    downtime_periods = []
    total_downtime = timedelta()
    
    for idx, event in downtime_events.iterrows():
        # البحث عن أقرب حدث مرجعي بعد حدث التوقف
        next_ref = reference_events[reference_events['DateTime'] > event['DateTime']]
        
        if not next_ref.empty:
            downtime_start = event['DateTime']
            downtime_end = next_ref.iloc[0]['DateTime']
            duration = downtime_end - downtime_start
            
            downtime_periods.append({
                'بداية التوقف': downtime_start,
                'نهاية التوقف': downtime_end,
                'المدة (دقائق)': duration.total_seconds() / 60,
                'الحدث': event['Event'],
                'التفاصيل': event.get('Details', '')
            })
            
            total_downtime += duration
    
    return total_downtime.total_seconds() / 60, len(downtime_events), downtime_periods

# دالة لحساب مدة التوقف لمجموعة أحداث
def calculate_group_downtime(df, event_list, reference_event="Automatic mode"):
    """
    حساب إجمالي مدة التوقف لمجموعة أحداث
    """
    if df is None or 'DateTime' not in df.columns:
        return 0, 0, []
    
    # فرز البيانات حسب الوقت
    df_sorted = df.sort_values('DateTime').reset_index(drop=True)
    
    # البحث عن أحداث التوقف (أي من الأحداث في القائمة)
    downtime_events = df_sorted[df_sorted['Event'].apply(lambda x: any(str(event) in str(x) for event in event_list))]
    reference_events = df_sorted[df_sorted['Event'].str.contains(reference_event, case=False, na=False)]
    
    if len(downtime_events) == 0 or len(reference_events) == 0:
        return 0, len(downtime_events), []
    
    # حساب مدة كل توقف
    downtime_periods = []
    total_downtime = timedelta()
    
    for idx, event in downtime_events.iterrows():
        # البحث عن أقرب حدث مرجعي بعد حدث التوقف
        next_ref = reference_events[reference_events['DateTime'] > event['DateTime']]
        
        if not next_ref.empty:
            downtime_start = event['DateTime']
            downtime_end = next_ref.iloc[0]['DateTime']
            duration = downtime_end - downtime_start
            
            downtime_periods.append({
                'بداية التوقف': downtime_start,
                'نهاية التوقف': downtime_end,
                'المدة (دقائق)': duration.total_seconds() / 60,
                'الحدث': event['Event'],
                'التفاصيل': event.get('Details', '')
            })
            
            total_downtime += duration
    
    return total_downtime.total_seconds() / 60, len(downtime_events), downtime_periods

# تحميل البيانات
df_raw = load_data(uploaded_file, use_sample_data)

# تحضير البيانات
if df_raw is not None:
    df = prepare_data(df_raw)
else:
    df = None

# الرسالة الرئيسية إذا لم يتم تحميل بيانات
if df is None or len(df) == 0:
    st.markdown("""
    <div class="upload-box">
        <h3>📁 لم يتم تحميل أي بيانات</h3>
        <p>يرجى رفع ملف بيانات (Excel أو CSV) من الشريط الجانبي</p>
        <p>أو تفعيل خيار "استخدام بيانات تجريبية"</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# قسم العرض الرئيسي
tab1, tab2, tab3, tab4 = st.tabs(["📋 عرض البيانات", "📊 الإحصائيات", "⏱ حساب التوقف", "📥 التصدير"])

# إنشاء df_filtered كنسخة من df للاستخدام في جميع الأقسام
df_filtered = df.copy()

with tab1:
    st.header("📋 عرض البيانات التفصيلي")
    
    # إعدادات عرض البيانات
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rows_to_show = st.slider("عدد الصفوف للعرض:", 10, 1000, 100, 10)
    
    with col2:
        # الحصول على أسماء الأعمدة المتاحة
        available_columns = df.columns.tolist()
        sort_column = st.selectbox("ترتيب البيانات حسب:", available_columns)
    
    with col3:
        sort_order = st.radio("نوع الترتيب:", ["تصاعدي", "تنازلي"], horizontal=True)
    
    # تصفية حسب التاريخ إذا كان موجوداً
    if 'DateTime' in df.columns and len(df) > 0:
        st.markdown("### ⏰ تصفية حسب التاريخ")
        date_col1, date_col2 = st.columns(2)
        
        with date_col1:
            try:
                min_date = df['DateTime'].min().date()
                max_date = df['DateTime'].max().date()
                start_date = st.date_input("من تاريخ:", 
                                          value=min_date,
                                          min_value=min_date,
                                          max_value=max_date)
            except:
                start_date = st.date_input("من تاريخ:", value=pd.Timestamp.now().date())
        
        with date_col2:
            try:
                end_date = st.date_input("إلى تاريخ:", 
                                        value=max_date,
                                        min_value=min_date,
                                        max_value=max_date)
            except:
                end_date = st.date_input("إلى تاريخ:", value=pd.Timestamp.now().date())
        
        # تطبيق التصفية
        try:
            df_filtered = df[(df['DateTime'].dt.date >= start_date) & 
                            (df['DateTime'].dt.date <= end_date)].copy()
        except:
            df_filtered = df.copy()
            st.warning("⚠️ تعذر تطبيق التصفية التاريخية")
    
    # تصفية حسب الحدث
    if 'Event' in df_filtered.columns and len(df_filtered) > 0:
        st.markdown("### 🔍 تصفية حسب الحدث")
        unique_events = df_filtered['Event'].dropna().unique().tolist()
        if unique_events:
            selected_events = st.multiselect("اختر الأحداث:", unique_events)
            
            if selected_events:
                df_filtered = df_filtered[df_filtered['Event'].isin(selected_events)]
        else:
            st.info("لا توجد أحداث للتصفية")
    
    # ترتيب البيانات
    ascending_order = True if sort_order == "تصاعدي" else False
    try:
        df_display = df_filtered.sort_values(by=sort_column, ascending=ascending_order).head(rows_to_show)
    except:
        df_display = df_filtered.head(rows_to_show)
        st.warning(f"⚠️ تعذر الترتيب حسب العمود '{sort_column}'")
    
    # عرض البيانات
    st.markdown(f"### 📄 عرض البيانات ({len(df_display)} من {len(df_filtered)} سجل)")
    
    # تكوين أعمدة العرض
    column_config = {}
    if 'DateTime' in df_display.columns:
        column_config["DateTime"] = st.column_config.DatetimeColumn("التاريخ والوقت")
    if 'Date' in df_display.columns:
        column_config["Date"] = st.column_config.TextColumn("التاريخ")
    if 'Time' in df_display.columns:
        column_config["Time"] = st.column_config.TextColumn("الوقت")
    if 'Event' in df_display.columns:
        column_config["Event"] = st.column_config.TextColumn("الحدث")
    if 'Details' in df_display.columns:
        column_config["Details"] = st.column_config.TextColumn("التفاصيل", width="large")
    
    # عرض البيانات
    st.dataframe(
        df_display,
        use_container_width=True,
        height=600,
        column_config=column_config if column_config else None
    )
    
    # عرض ملخص سريع
    st.markdown(f"""
    <div class="metric-card">
        <h4>📊 ملخص البيانات</h4>
        <p>• عدد السجلات الكلي: <strong>{len(df):,}</strong></p>
        <p>• عدد السجلات بعد التصفية: <strong>{len(df_filtered):,}</strong></p>
        <p>• عدد السجلات المعروضة: <strong>{len(df_display):,}</strong></p>
    </div>
    """, unsafe_allow_html=True)

with tab2:
    st.header("📊 الإحصائيات التحليلية")
    
    if len(df_filtered) > 0:
        # مؤشرات سريعة
        st.subheader("📈 مؤشرات سريعة")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("إجمالي السجلات", f"{len(df_filtered):,}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if 'DateTime' in df_filtered.columns:
                try:
                    date_range = (df_filtered['DateTime'].max() - df_filtered['DateTime'].min()).days
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.metric("المدة الزمنية (أيام)", f"{date_range:,}")
                    st.markdown('</div>', unsafe_allow_html=True)
                except:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.metric("المدة الزمنية", "غير متاح")
                    st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            if 'Event' in df_filtered.columns:
                unique_events = df_filtered['Event'].nunique()
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("عدد أنواع الأحداث", f"{unique_events:,}")
                st.markdown('</div>', unsafe_allow_html=True)
        
        # إحصائيات الأحداث
        if 'Event' in df_filtered.columns:
            st.subheader("📋 توزيع الأحداث")
            event_stats = df_filtered['Event'].value_counts().reset_index()
            event_stats.columns = ['الحدث', 'التكرار']
            
            # عرض جدول التكرارات
            st.dataframe(
                event_stats,
                use_container_width=True,
                height=400
            )
            
            # عرض إجماليات
            st.subheader("📊 إجماليات الأحداث")
            
            # أعلى 5 أحداث
            if len(event_stats) > 0:
                top_5_events = event_stats.head(5)
                for idx, row in top_5_events.iterrows():
                    percentage = (row['التكرار'] / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
                    st.markdown(f"""
                    <div class="metric-card">
                        <strong>{row['الحدث']}</strong>: {row['التكرار']} مرة 
                        ({percentage:.1f}% من إجمالي الأحداث)
                    </div>
                    """, unsafe_allow_html=True)
        
        # البحث في التفاصيل
        if 'Details' in df_filtered.columns:
            st.subheader("🔍 البحث في التفاصيل")
            search_term = st.text_input("ابحث في التفاصيل:")
            
            if search_term:
                try:
                    search_results = df_filtered[df_filtered['Details'].str.contains(search_term, case=False, na=False)]
                    st.write(f"نتائج البحث ({len(search_results)} سجل):")
                    st.dataframe(search_results.head(20), use_container_width=True)
                except:
                    st.warning("⚠️ تعذر البحث في التفاصيل")

with tab3:
    st.header("⏱ حساب إجمالي مدة التوقف")
    
    if 'Event' not in df.columns:
        st.warning("⚠️ البيانات لا تحتوي على عمود 'Event' لحساب التوقف.")
        st.stop()
    
    # قسمين: لحساب توقف حدث واحد و لمجموعة أحداث
    downtime_tab1, downtime_tab2 = st.tabs(["📊 توقف حدث واحد", "📈 توقف مجموعة أحداث"])
    
    with downtime_tab1:
        st.markdown("### حساب مدة التوقف لحدث معين")
        
        # اختيار الحدث
        all_events = sorted(df['Event'].dropna().unique().tolist())
        
        if not all_events:
            st.warning("⚠️ لا توجد أحداث في البيانات.")
            st.stop()
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_event = st.selectbox(
                "اختر حدث التوقف:",
                options=all_events,
                key="single_event_select"
            )
        
        with col2:
            # البحث عن حدث مرجعي مناسب
            ref_options = all_events
            ref_index = 0
            if 'Automatic mode' in all_events:
                ref_index = all_events.index('Automatic mode')
            elif 'Manual mode' in all_events:
                ref_index = all_events.index('Manual mode')
            
            reference_event = st.selectbox(
                "اختر حدث التشغيل (المرجع):",
                options=all_events,
                index=ref_index,
                key="single_ref_select"
            )
        
        # زر الحساب
        if st.button("🧮 حساب مدة التوقف", type="primary", key="calculate_single"):
            with st.spinner("جاري حساب مدة التوقف..."):
                total_minutes, event_count, periods = calculate_downtime(df, selected_event, reference_event)
                
                if event_count > 0:
                    if periods:
                        # عرض النتائج
                        st.markdown(f"""
                        <div class="highlight-box">
                            <h2>📊 نتائج حساب التوقف</h2>
                            <h3>إجمالي مدة التوقف: <span style="color: #FFD700">{total_minutes:.2f} دقيقة</span></h3>
                            <p>عدد مرات التوقف: {event_count} مرة</p>
                            <p>متوسط مدة التوقف: {total_minutes/event_count:.2f} دقيقة</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # تحويل المدة إلى ساعات وأيام
                        hours = total_minutes / 60
                        days = hours / 24
                        
                        # عرض بتنسيق جميل
                        col_a, col_b, col_c = st.columns(3)
                        
                        with col_a:
                            st.markdown('<div class="downtime-card">', unsafe_allow_html=True)
                            st.markdown(f"**إجمالي الدقائق**")
                            st.markdown(f"# {total_minutes:.2f}")
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        with col_b:
                            st.markdown('<div class="downtime-card">', unsafe_allow_html=True)
                            st.markdown(f"**إجمالي الساعات**")
                            st.markdown(f"# {hours:.2f}")
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        with col_c:
                            st.markdown('<div class="downtime-card">', unsafe_allow_html=True)
                            st.markdown(f"**إجمالي الأيام**")
                            st.markdown(f"# {days:.2f}")
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        # عرض تفاصيل فترات التوقف
                        st.subheader("📋 تفاصيل فترات التوقف")
                        
                        if periods:
                            periods_df = pd.DataFrame(periods)
                            st.dataframe(
                                periods_df,
                                use_container_width=True,
                                column_config={
                                    "بداية التوقف": st.column_config.DatetimeColumn("بداية التوقف"),
                                    "نهاية التوقف": st.column_config.DatetimeColumn("نهاية التوقف"),
                                    "المدة (دقائق)": st.column_config.NumberColumn("المدة (دقائق)", format="%.2f"),
                                    "الحدث": st.column_config.TextColumn("الحدث"),
                                    "التفاصيل": st.column_config.TextColumn("التفاصيل", width="large")
                                }
                            )
                            
                            # ملخص فترات التوقف
                            st.subheader("📊 ملخص فترات التوقف")
                            
                            min_duration = periods_df['المدة (دقائق)'].min()
                            max_duration = periods_df['المدة (دقائق)'].max()
                            avg_duration = periods_df['المدة (دقائق)'].mean()
                            
                            col_d, col_e, col_f = st.columns(3)
                            
                            with col_d:
                                st.metric("أقل مدة توقف", f"{min_duration:.2f} دقيقة")
                            
                            with col_e:
                                st.metric("أكثر مدة توقف", f"{max_duration:.2f} دقيقة")
                            
                            with col_f:
                                st.metric("المتوسط", f"{avg_duration:.2f} دقيقة")
                    else:
                        st.warning(f"⚠️ تم العثور على {event_count} حدث من نوع '{selected_event}' ولكن لا يمكن حساب مدة التوقف بسبب عدم وجود أحداث مرجعية بعدها.")
                else:
                    st.error(f"❌ لم يتم العثور على أي حدث من نوع '{selected_event}' في البيانات.")
    
    with downtime_tab2:
        st.markdown("### حساب مدة التوقف لمجموعة أحداث")
        
        # اختيار مجموعة الأحداث
        all_events = sorted(df['Event'].dropna().unique().tolist())
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_events = st.multiselect(
                "اختر مجموعة أحداث التوقف:",
                options=all_events,
                default=all_events[:2] if len(all_events) >= 2 else all_events,
                key="group_events_select"
            )
        
        with col2:
            # البحث عن حدث مرجعي مناسب
            ref_options = all_events
            ref_index = 0
            if 'Automatic mode' in all_events:
                ref_index = all_events.index('Automatic mode')
            elif 'Manual mode' in all_events:
                ref_index = all_events.index('Manual mode')
            
            reference_event = st.selectbox(
                "اختر حدث التشغيل (المرجع):",
                options=all_events,
                index=ref_index,
                key="group_ref_select"
            )
        
        # زر الحساب للمجموعة
        if st.button("🧮 حساب مدة توقف المجموعة", type="primary", key="calculate_group"):
            with st.spinner("جاري حساب مدة توقف المجموعة..."):
                if selected_events:
                    total_minutes, event_count, periods = calculate_group_downtime(df, selected_events, reference_event)
                    
                    if event_count > 0:
                        if periods:
                            # عرض النتائج
                            events_str = ", ".join(selected_events)
                            st.markdown(f"""
                            <div class="highlight-box">
                                <h2>📊 نتائج حساب توقف المجموعة</h2>
                                <h3>إجمالي مدة التوقف: <span style="color: #FFD700">{total_minutes:.2f} دقيقة</span></h3>
                                <p>عدد مرات التوقف: {event_count} مرة</p>
                                <p>متوسط مدة التوقف: {total_minutes/event_count:.2f} دقيقة</p>
                                <p>الأحداث المختارة: {events_str}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # تحويل المدة إلى ساعات وأيام
                            hours = total_minutes / 60
                            days = hours / 24
                            
                            # عرض بتنسيق جميل
                            col_a, col_b, col_c = st.columns(3)
                            
                            with col_a:
                                st.markdown('<div class="downtime-card">', unsafe_allow_html=True)
                                st.markdown(f"**إجمالي الدقائق**")
                                st.markdown(f"# {total_minutes:.2f}")
                                st.markdown('</div>', unsafe_allow_html=True)
                            
                            with col_b:
                                st.markdown('<div class="downtime-card">', unsafe_allow_html=True)
                                st.markdown(f"**إجمالي الساعات**")
                                st.markdown(f"# {hours:.2f}")
                                st.markdown('</div>', unsafe_allow_html=True)
                            
                            with col_c:
                                st.markdown('<div class="downtime-card">', unsafe_allow_html=True)
                                st.markdown(f"**إجمالي الأيام**")
                                st.markdown(f"# {days:.2f}")
                                st.markdown('</div>', unsafe_allow_html=True)
                            
                            # عرض تفاصيل فترات التوقف
                            st.subheader("📋 تفاصيل فترات التوقف")
                            
                            if periods:
                                periods_df = pd.DataFrame(periods)
                                st.dataframe(
                                    periods_df,
                                    use_container_width=True,
                                    column_config={
                                        "بداية التوقف": st.column_config.DatetimeColumn("بداية التوقف"),
                                        "نهاية التوقف": st.column_config.DatetimeColumn("نهاية التوقف"),
                                        "المدة (دقائق)": st.column_config.NumberColumn("المدة (دقائق)", format="%.2f"),
                                        "الحدث": st.column_config.TextColumn("الحدث"),
                                        "التفاصيل": st.column_config.TextColumn("التفاصيل", width="large")
                                    }
                                )
                        else:
                            st.warning(f"⚠️ تم العثور على {event_count} حدث من المجموعة المختارة ولكن لا يمكن حساب مدة التوقف بسبب عدم وجود أحداث مرجعية بعدها.")
                    else:
                        st.error(f"❌ لم يتم العثور على أي حدث من المجموعة المختارة في البيانات.")
                else:
                    st.warning("⚠️ يرجى اختيار حدث واحد على الأقل من القائمة.")

with tab4:
    st.header("📥 خيارات التصدير")
    
    st.info("""
    يمكنك تصدير البيانات المصفاة إلى عدة صيغ مختلفة.
    اختر الصيغة المناسبة واحفظ البيانات على جهازك.
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 📄 Excel")
        st.markdown("صيغة جدول بيانات متقدمة")
        
        # زر التصدير إلى Excel
        if st.button("💾 تصدير إلى Excel", use_container_width=True):
            try:
                output = BytesIO()
                df_filtered.to_excel(output, index=False)
                excel_data = output.getvalue()
                
                b64 = base64.b64encode(excel_data).decode()
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="data_export.xlsx">📥 انقر للتحميل</a>'
                st.markdown(href, unsafe_allow_html=True)
                st.success("✅ تم تجهيز ملف Excel للتحميل")
            except Exception as e:
                st.error(f"❌ خطأ في تصدير Excel: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 📊 CSV")
        st.markdown("صيغة نصية بسيطة")
        
        # زر التصدير إلى CSV
        if st.button("📊 تصدير إلى CSV", use_container_width=True):
            try:
                csv_data = df_filtered.to_csv(index=False, encoding='utf-8-sig')
                b64 = base64.b64encode(csv_data.encode('utf-8-sig')).decode()
                href = f'<a href="data:text/csv;charset=utf-8-sig;base64,{b64}" download="data_export.csv">📥 انقر للتحميل</a>'
                st.markdown(href, unsafe_allow_html=True)
                st.success("✅ تم تجهيز ملف CSV للتحميل")
            except Exception as e:
                st.error(f"❌ خطأ في تصدير CSV: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # إحصائيات التصدير
    st.markdown("### 📈 ملخص البيانات المصدَّرة")
    st.write(f"**عدد السجلات:** {len(df_filtered):,}")
    st.write(f"**عدد الأعمدة:** {len(df_filtered.columns)}")
    
    # عرض أسماء الأعمدة
    if len(df_filtered.columns) > 0:
        st.write(f"**الأعمدة:** {', '.join(df_filtered.columns.tolist())}")
    
    # معاينة البيانات قبل التصدير
    with st.expander("👁️ معاينة البيانات قبل التصدير"):
        if len(df_filtered) > 0:
            st.dataframe(df_filtered.head(10), use_container_width=True)
        else:
            st.info("لا توجد بيانات للمعاينة")

# تذييل الصفحة
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>📋 نظام عرض وتحليل بيانات السجل التقني | إصدار 2.0</p>
    <p>تم التطوير باستخدام Streamlit | للاستخدام التقني والتحليلي</p>
</div>
""", unsafe_allow_html=True)
