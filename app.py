import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
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
</style>
""", unsafe_allow_html=True)

# عنوان التطبيق
st.markdown('<div class="main-header"><h1>📋 نظام عرض وتحليل بيانات السجل التقني</h1><h3>عرض وتحليل بيانات أعطال المعدات + حساب أوقات التوقف</h3></div>', unsafe_allow_html=True)

# الشريط الجانبي
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/data-configuration.png", width=100)
    st.markdown("### ⚙️ إعدادات العرض")
    
    # خيارات عرض البيانات
    st.markdown("#### خيارات البيانات:")
    show_raw_data = st.checkbox("عرض البيانات الخام", value=True)
    show_stats = st.checkbox("عرض الإحصائيات", value=True)
    show_downtime = st.checkbox("حساب أوقات التوقف", value=True)
    show_charts = st.checkbox("عرض الرسوم البيانية", value=True)
    
    st.markdown("---")
    st.markdown("#### معلومات:")
    st.info("""
    **مميزات التطبيق:**
    - عرض كامل للبيانات
    - إحصائيات تفصيلية
    - حساب أوقات التوقف
    - تصورات بيانية
    - تصدير للعديد من الصيغ
    """)

# دالة لتحميل البيانات
@st.cache_data
def load_data():
    """
    تحميل البيانات من ملف Excel
    """
    try:
        # جرب تحميل من مسار محدد
        df = pd.read_excel("organized_logbook.xlsx")
        st.sidebar.success("✅ تم تحميل البيانات بنجاح")
        return df
    except Exception as e:
        st.sidebar.error(f"❌ خطأ في تحميل البيانات: {e}")
        # إنشاء بيانات تجريبية للعرض
        sample_data = {
            "Date": pd.date_range(start="2024-01-01", periods=100, freq='H'),
            "Time": [f"{i%24:02d}:{(i*30)%60:02d}" for i in range(100)],
            "Event": ["Automatic mode", "Manual mode", "Error 001", "Maintenance", 
                     "System Reset", "Error 002", "Calibration", "Error 003"] * 12 + ["Automatic mode", "Manual mode"],
            "Details": [f"Detail {i}" for i in range(100)]
        }
        df = pd.DataFrame(sample_data)
        st.sidebar.warning("⚠️ يتم عرض بيانات تجريبية")
        return df

# دالة لحساب مدة التوقف
def calculate_downtime(df, event_name, reference_event="Automatic mode"):
    """
    حساب إجمالي مدة التوقف لحدث معين
    """
    if 'DateTime' not in df.columns:
        return 0, 0, []
    
    # فرز البيانات حسب الوقت
    df = df.sort_values('DateTime').reset_index(drop=True)
    
    # البحث عن أحداث التوقف وأحداث المرجع
    downtime_events = df[df['Event'].str.contains(event_name, case=False, na=False)]
    reference_events = df[df['Event'].str.contains(reference_event, case=False, na=False)]
    
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
    if 'DateTime' not in df.columns:
        return 0, 0, []
    
    # فرز البيانات حسب الوقت
    df = df.sort_values('DateTime').reset_index(drop=True)
    
    # البحث عن أحداث التوقف (أي من الأحداث في القائمة)
    downtime_events = df[df['Event'].apply(lambda x: any(event in str(x) for event in event_list))]
    reference_events = df[df['Event'].str.contains(reference_event, case=False, na=False)]
    
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
df = load_data()

# تحضير البيانات
if 'DateTime' not in df.columns and 'Date' in df.columns and 'Time' in df.columns:
    try:
        df['DateTime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
    except:
        df['DateTime'] = pd.to_datetime(df['Date'])

# قسم العرض الرئيسي
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 عرض البيانات", "📊 الإحصائيات", "⏱ حساب التوقف", "📈 الرسوم البيانية", "📥 التصدير"])

with tab1:
    st.header("📋 عرض البيانات التفصيلي")
    
    # إعدادات عرض البيانات
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rows_to_show = st.slider("عدد الصفوف للعرض:", 10, 1000, 100, 10)
    
    with col2:
        sort_column = st.selectbox("ترتيب البيانات حسب:", 
                                  ['DateTime', 'Date', 'Time', 'Event'] if 'DateTime' in df.columns else df.columns.tolist())
    
    with col3:
        sort_order = st.radio("نوع الترتيب:", ["تصاعدي", "تنازلي"], horizontal=True)
    
    # تصفية حسب التاريخ إذا كان موجوداً
    if 'DateTime' in df.columns:
        st.markdown("### ⏰ تصفية حسب التاريخ")
        date_col1, date_col2 = st.columns(2)
        
        with date_col1:
            start_date = st.date_input("من تاريخ:", 
                                      value=df['DateTime'].min().date(),
                                      min_value=df['DateTime'].min().date(),
                                      max_value=df['DateTime'].max().date())
        
        with date_col2:
            end_date = st.date_input("إلى تاريخ:", 
                                    value=df['DateTime'].max().date(),
                                    min_value=df['DateTime'].min().date(),
                                    max_value=df['DateTime'].max().date())
        
        # تطبيق التصفية
        df_filtered = df[(df['DateTime'].dt.date >= start_date) & 
                        (df['DateTime'].dt.date <= end_date)].copy()
    else:
        df_filtered = df.copy()
    
    # تصفية حسب الحدث
    if 'Event' in df_filtered.columns:
        st.markdown("### 🔍 تصفية حسب الحدث")
        all_events = ['الكل'] + sorted(df_filtered['Event'].dropna().unique().tolist())
        selected_events = st.multiselect("اختر الأحداث:", 
                                        all_events[1:], 
                                        default=all_events[1] if len(all_events) > 1 else [])
        
        if selected_events:
            df_filtered = df_filtered[df_filtered['Event'].isin(selected_events)]
    
    # ترتيب البيانات
    ascending_order = True if sort_order == "تصاعدي" else False
    df_display = df_filtered.sort_values(by=sort_column, ascending=ascending_order).head(rows_to_show)
    
    # عرض البيانات
    st.markdown(f"### 📄 عرض البيانات ({len(df_display)} من {len(df_filtered)} سجل)")
    
    # استخدام ميزة Data Editor للعرض التفاعلي
    st.dataframe(
        df_display,
        use_container_width=True,
        height=600,
        column_config={
            "DateTime": st.column_config.DatetimeColumn("التاريخ والوقت"),
            "Date": st.column_config.TextColumn("التاريخ"),
            "Time": st.column_config.TextColumn("الوقت"),
            "Event": st.column_config.TextColumn("الحدث"),
            "Details": st.column_config.TextColumn("التفاصيل", width="large")
        }
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
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("إجمالي السجلات", f"{len(df_filtered):,}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if 'DateTime' in df_filtered.columns:
                date_range = (df_filtered['DateTime'].max() - df_filtered['DateTime'].min()).days
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("المدة الزمنية (أيام)", f"{date_range:,}")
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
            
            col4, col5 = st.columns([3, 2])
            
            with col4:
                st.dataframe(
                    event_stats,
                    use_container_width=True,
                    height=400
                )
            
            with col5:
                # رسم بياني دائري بسيط
                fig, ax = plt.subplots()
                top_events = event_stats.head(10)
                ax.pie(top_events['التكرار'], labels=top_events['الحدث'], autopct='%1.1f%%')
                ax.set_title("توزيع أهم 10 أحداث")
                st.pyplot(fig)
        
        # إحصائيات زمنية
        if 'DateTime' in df_filtered.columns:
            st.subheader("⏰ إحصائيات زمنية")
            
            # استخراج الساعة واليوم
            df_filtered['Hour'] = df_filtered['DateTime'].dt.hour
            df_filtered['DayOfWeek'] = df_filtered['DateTime'].dt.day_name()
            df_filtered['Month'] = df_filtered['DateTime'].dt.month_name()
            
            col6, col7, col8 = st.columns(3)
            
            with col6:
                hourly_stats = df_filtered['Hour'].value_counts().sort_index()
                st.bar_chart(hourly_stats)
                st.caption("التوزيع على مدار الساعة")
            
            with col7:
                daily_stats = df_filtered['DayOfWeek'].value_counts()
                st.bar_chart(daily_stats)
                st.caption("التوزيع على أيام الأسبوع")
            
            with col8:
                monthly_stats = df_filtered['Month'].value_counts()
                st.bar_chart(monthly_stats)
                st.caption("التوزيع على الأشهر")

with tab3:
    st.header("⏱ حساب إجمالي مدة التوقف")
    
    # قسمين: لحساب توقف حدث واحد و لمجموعة أحداث
    downtime_tab1, downtime_tab2 = st.tabs(["📊 توقف حدث واحد", "📈 توقف مجموعة أحداث"])
    
    with downtime_tab1:
        st.markdown("### حساب مدة التوقف لحدث معين")
        
        if 'Event' in df.columns:
            # اختيار الحدث
            all_events = sorted(df['Event'].dropna().unique().tolist())
            
            col1, col2 = st.columns(2)
            
            with col1:
                selected_event = st.selectbox(
                    "اختر حدث التوقف:",
                    options=all_events,
                    key="single_event_select"
                )
            
            with col2:
                reference_event = st.selectbox(
                    "اختر حدث التشغيل (المرجع):",
                    options=all_events,
                    index=all_events.index('Automatic mode') if 'Automatic mode' in all_events else 0,
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
                                st.metric("إجمالي الدقائق", f"{total_minutes:.2f}")
                            
                            with col_b:
                                st.metric("إجمالي الساعات", f"{hours:.2f}")
                            
                            with col_c:
                                st.metric("إجمالي الأيام", f"{days:.2f}")
                            
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
                                
                                # رسم بياني لفترات التوقف
                                st.subheader("📈 توزيع فترات التوقف")
                                
                                if len(periods_df) > 0:
                                    fig, ax = plt.subplots(figsize=(10, 6))
                                    ax.bar(range(len(periods_df)), periods_df['المدة (دقائق)'])
                                    ax.set_xlabel('رقم فترة التوقف')
                                    ax.set_ylabel('المدة (دقائق)')
                                    ax.set_title(f"فترات التوقف لحدث: {selected_event}")
                                    ax.grid(True, alpha=0.3)
                                    st.pyplot(fig)
                        else:
                            st.warning(f"⚠️ تم العثور على {event_count} حدث من نوع '{selected_event}' ولكن لا يمكن حساب مدة التوقف بسبب عدم وجود أحداث مرجعية بعدها.")
                    else:
                        st.error(f"❌ لم يتم العثور على أي حدث من نوع '{selected_event}' في البيانات.")
        
        else:
            st.warning("⚠️ البيانات لا تحتوي على عمود 'Event' لحساب التوقف.")
    
    with downtime_tab2:
        st.markdown("### حساب مدة التوقف لمجموعة أحداث")
        
        if 'Event' in df.columns:
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
                reference_event = st.selectbox(
                    "اختر حدث التشغيل (المرجع):",
                    options=all_events,
                    index=all_events.index('Automatic mode') if 'Automatic mode' in all_events else 0,
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
                                    st.metric("إجمالي الدقائق", f"{total_minutes:.2f}")
                                
                                with col_b:
                                    st.metric("إجمالي الساعات", f"{hours:.2f}")
                                
                                with col_c:
                                    st.metric("إجمالي الأيام", f"{days:.2f}")
                                
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
                                    
                                    # رسم بياني لفترات التوقف حسب النوع
                                    st.subheader("📈 توزيع فترات التوقف حسب الحدث")
                                    
                                    if len(periods_df) > 0:
                                        # تجميع حسب الحدث
                                        event_summary = periods_df.groupby('الحدث').agg({
                                            'المدة (دقائق)': 'sum',
                                            'بداية التوقف': 'count'
                                        }).rename(columns={'بداية التوقف': 'عدد المرات'}).reset_index()
                                        
                                        # رسم بياني شريطي
                                        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
                                        
                                        # الرسم البياني الأول: إجمالي مدة التوقف
                                        ax1.bar(event_summary['الحدث'], event_summary['المدة (دقائق)'])
                                        ax1.set_xlabel('الحدث')
                                        ax1.set_ylabel('المدة (دقائق)')
                                        ax1.set_title("إجمالي مدة التوقف لكل حدث")
                                        ax1.tick_params(axis='x', rotation=45)
                                        ax1.grid(True, alpha=0.3)
                                        
                                        # الرسم البياني الثاني: عدد المرات
                                        ax2.bar(event_summary['الحدث'], event_summary['عدد المرات'])
                                        ax2.set_xlabel('الحدث')
                                        ax2.set_ylabel('عدد المرات')
                                        ax2.set_title("عدد مرات التوقف لكل حدث")
                                        ax2.tick_params(axis='x', rotation=45)
                                        ax2.grid(True, alpha=0.3)
                                        
                                        plt.tight_layout()
                                        st.pyplot(fig)
                            else:
                                st.warning(f"⚠️ تم العثور على {event_count} حدث من المجموعة المختارة ولكن لا يمكن حساب مدة التوقف بسبب عدم وجود أحداث مرجعية بعدها.")
                        else:
                            st.error(f"❌ لم يتم العثور على أي حدث من المجموعة المختارة في البيانات.")
                    else:
                        st.warning("⚠️ يرجى اختيار حدث واحد على الأقل من القائمة.")
        
        else:
            st.warning("⚠️ البيانات لا تحتوي على عمود 'Event' لحساب التوقف.")

with tab4:
    st.header("📈 الرسوم البيانية التفاعلية")
    
    if len(df_filtered) > 0:
        chart_type = st.selectbox("نوع الرسم البياني:", 
                                 ["عمودي", "دائري", "خطي", "مبعثر"])
        
        if 'Event' in df_filtered.columns:
            # تحضير بيانات الأحداث
            event_data = df_filtered['Event'].value_counts().reset_index()
            event_data.columns = ['Event', 'Count']
            
            if chart_type == "عمودي":
                st.subheader("📊 توزيع الأحداث (رسم عمودي)")
                
                fig, ax = plt.subplots(figsize=(10, 6))
                bars = ax.bar(event_data.head(15)['Event'], event_data.head(15)['Count'])
                ax.set_xlabel('الحدث')
                ax.set_ylabel('التكرار')
                ax.set_title("توزيع الأحداث (أعلى 15)")
                ax.tick_params(axis='x', rotation=45)
                ax.grid(True, alpha=0.3)
                
                # إضافة أرقام على الأعمدة
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                            f'{int(height)}', ha='center', va='bottom')
                
                st.pyplot(fig)
            
            elif chart_type == "دائري":
                st.subheader("📊 توزيع الأحداث (رسم دائري)")
                
                fig, ax = plt.subplots(figsize=(8, 8))
                wedges, texts, autotexts = ax.pie(
                    event_data.head(10)['Count'],
                    labels=event_data.head(10)['Event'],
                    autopct='%1.1f%%',
                    startangle=90
                )
                ax.set_title("نسبة الأحداث (أعلى 10)")
                st.pyplot(fig)
            
            elif chart_type == "خطي":
                if 'DateTime' in df_filtered.columns:
                    st.subheader("📈 اتجاه الأحداث عبر الزمن")
                    
                    timeline_data = df_filtered.groupby(df_filtered['DateTime'].dt.date).size().reset_index()
                    timeline_data.columns = ['Date', 'Count']
                    
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(timeline_data['Date'], timeline_data['Count'], marker='o')
                    ax.set_xlabel('التاريخ')
                    ax.set_ylabel('عدد الأحداث')
                    ax.set_title("اتجاه الأحداث عبر الزمن")
                    ax.grid(True, alpha=0.3)
                    ax.tick_params(axis='x', rotation=45)
                    st.pyplot(fig)
            
            elif chart_type == "مبعثر":
                if 'DateTime' in df_filtered.columns and 'Event' in df_filtered.columns:
                    st.subheader("📊 توزيع الأحداث خلال اليوم والشهر")
                    
                    scatter_data = df_filtered.copy()
                    scatter_data['Hour'] = scatter_data['DateTime'].dt.hour
                    scatter_data['Day'] = scatter_data['DateTime'].dt.day
                    
                    fig, ax = plt.subplots(figsize=(10, 6))
                    
                    # تلوين النقاط حسب الحدث (أول 5 أحداث فقط)
                    events_to_plot = scatter_data['Event'].value_counts().head(5).index.tolist()
                    
                    for event in events_to_plot:
                        event_data = scatter_data[scatter_data['Event'] == event]
                        ax.scatter(event_data['Day'], event_data['Hour'], label=event, alpha=0.7)
                    
                    ax.set_xlabel('يوم الشهر')
                    ax.set_ylabel('ساعة اليوم')
                    ax.set_title("توزيع الأحداث خلال اليوم والشهر")
                    ax.legend()
                    ax.grid(True, alpha=0.3)
                    st.pyplot(fig)

with tab5:
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
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_filtered.to_excel(writer, index=False, sheet_name='Data')
            excel_data = output.getvalue()
            
            b64 = base64.b64encode(excel_data).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="data_export.xlsx">📥 انقر للتحميل</a>'
            st.markdown(href, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 📊 CSV")
        st.markdown("صيغة نصية بسيطة")
        
        # زر التصدير إلى CSV
        if st.button("📊 تصدير إلى CSV", use_container_width=True):
            csv_data = df_filtered.to_csv(index=False, encoding='utf-8-sig')
            b64 = base64.b64encode(csv_data.encode('utf-8-sig')).decode()
            href = f'<a href="data:text/csv;charset=utf-8-sig;base64,{b64}" download="data_export.csv">📥 انقر للتحميل</a>'
            st.markdown(href, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 📝 JSON")
        st.markdown("صيغة تبادل بيانات")
        
        # زر التصدير إلى JSON
        if st.button("🔤 تصدير إلى JSON", use_container_width=True):
            json_data = df_filtered.to_json(orient='records', indent=2, force_ascii=False)
            b64 = base64.b64encode(json_data.encode('utf-8')).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="data_export.json">📥 انقر للتحميل</a>'
            st.markdown(href, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # إحصائيات التصدير
    st.markdown("### 📈 ملخص البيانات المصدَّرة")
    st.write(f"**عدد السجلات:** {len(df_filtered):,}")
    st.write(f"**عدد الأعمدة:** {len(df_filtered.columns)}")
    st.write(f"**الأعمدة:** {', '.join(df_filtered.columns.tolist())}")
    
    # معاينة البيانات قبل التصدير
    with st.expander("👁️ معاينة البيانات قبل التصدير"):
        st.dataframe(df_filtered.head(10), use_container_width=True)

# تذييل الصفحة
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>📋 نظام عرض بيانات السجل التقني | إصدار 1.0</p>
    <p>تم التطوير باستخدام Streamlit | للاستخدام التقني والتحليلي</p>
</div>
""", unsafe_allow_html=True)
