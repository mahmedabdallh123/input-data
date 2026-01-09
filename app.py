import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    .st-emotion-cache-1c7yr2w {
        border: 1px solid #ddd;
    }
    .highlight-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 10px 0;
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
    - تصورات بيانية متقدمة
    - تصدير للعديد من الصيغ
    """)

# دالة لتحميل البيانات من GitHub
@st.cache_data
def load_data_from_github():
    """
    تحميل البيانات من GitHub أو المسار المحلي
    """
    try:
        # حاول تحميل من GitHub أولاً
        github_url = "https://raw.githubusercontent.com/username/repo/main/organized_logbook.xlsx"
        df = pd.read_excel(github_url)
        st.sidebar.success("✅ تم تحميل البيانات من GitHub")
        return df
    except:
        try:
            # إذا فشل، جرب المسار المحلي
            df = pd.read_excel("organized_logbook.xlsx")
            st.sidebar.success("✅ تم تحميل البيانات من الملف المحلي")
            return df
        except Exception as e:
            st.sidebar.error(f"❌ لم يتم العثور على ملف البيانات: {e}")
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
df = load_data_from_github()

# تحضير البيانات
if 'DateTime' not in df.columns and 'Date' in df.columns and 'Time' in df.columns:
    try:
        df['DateTime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
    except:
        df['DateTime'] = pd.to_datetime(df['Date'])

# قسم العرض الرئيسي - إضافة تبويب لحساب أوقات التوقف
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 عرض البيانات", "📊 الإحصائيات", "⏱ حساب التوقف", "📈 الرسوم البيانية", "📥 التصدير"])

# ... (الأقسام السابقة نفسها - tab1, tab2) ...

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
                                    fig = px.bar(
                                        periods_df,
                                        x='بداية التوقف',
                                        y='المدة (دقائق)',
                                        color='المدة (دقائق)',
                                        title=f"فترات التوقف لحدث: {selected_event}",
                                        color_continuous_scale='viridis'
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
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
                                        fig1 = px.bar(
                                            event_summary,
                                            x='الحدث',
                                            y='المدة (دقائق)',
                                            title="إجمالي مدة التوقف لكل حدث",
                                            color='المدة (دقائق)',
                                            color_continuous_scale='plasma'
                                        )
                                        fig1.update_layout(xaxis_tickangle=-45)
                                        st.plotly_chart(fig1, use_container_width=True)
                                        
                                        # رسم بياني دائري
                                        fig2 = px.pie(
                                            event_summary,
                                            values='المدة (دقائق)',
                                            names='الحدث',
                                            title="نسبة مدة التوقف لكل حدث"
                                        )
                                        st.plotly_chart(fig2, use_container_width=True)
                            else:
                                st.warning(f"⚠️ تم العثور على {event_count} حدث من المجموعة المختارة ولكن لا يمكن حساب مدة التوقف بسبب عدم وجود أحداث مرجعية بعدها.")
                        else:
                            st.error(f"❌ لم يتم العثور على أي حدث من المجموعة المختارة في البيانات.")
                    else:
                        st.warning("⚠️ يرجى اختيار حدث واحد على الأقل من القائمة.")
        
        else:
            st.warning("⚠️ البيانات لا تحتوي على عمود 'Event' لحساب التوقف.")
    
    # قسم التحليل المتقدم
    st.markdown("---")
    st.subheader("🔍 تحليل متقدم لأوقات التوقف")
    
    if 'Event' in df.columns and 'DateTime' in df.columns:
        # اختيار نطاق زمني للتحليل
        st.markdown("### تحليل التوقف خلال فترة محددة")
        
        col1, col2 = st.columns(2)
        
        with col1:
            min_date = df['DateTime'].min().date()
            max_date = df['DateTime'].max().date()
            
            analysis_start = st.date_input(
                "بداية فترة التحليل:",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                key="analysis_start"
            )
        
        with col2:
            analysis_end = st.date_input(
                "نهاية فترة التحليل:",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                key="analysis_end"
            )
        
        # تحويل التواريخ إلى datetime
        analysis_start_dt = pd.Timestamp(analysis_start)
        analysis_end_dt = pd.Timestamp(analysis_end) + pd.Timedelta(days=1)
        
        # تصفية البيانات للنطاق الزمني
        df_filtered_time = df[(df['DateTime'] >= analysis_start_dt) & (df['DateTime'] <= analysis_end_dt)]
        
        if st.button("📈 تحليل التوقف خلال الفترة", key="analyze_period"):
            if len(df_filtered_time) > 0:
                # حساب التوقف لجميع الأحداث في الفترة
                all_events_in_period = df_filtered_time['Event'].dropna().unique().tolist()
                
                downtime_summary = []
                
                for event in all_events_in_period[:10]:  # تحليل أول 10 أحداث فقط
                    minutes, count, _ = calculate_downtime(df_filtered_time, event)
                    if count > 0 and minutes > 0:
                        downtime_summary.append({
                            'الحدث': event,
                            'عدد المرات': count,
                            'إجمالي الدقائق': minutes,
                            'إجمالي الساعات': minutes / 60,
                            'المتوسط (دقائق)': minutes / count
                        })
                
                if downtime_summary:
                    summary_df = pd.DataFrame(downtime_summary).sort_values('إجمالي الدقائق', ascending=False)
                    
                    st.success(f"📊 تحليل التوقف للفترة من {analysis_start} إلى {analysis_end}")
                    st.dataframe(summary_df, use_container_width=True)
                    
                    # رسم بياني لأعلى 5 أحداث توقف
                    top_events = summary_df.head(5)
                    
                    fig = px.bar(
                        top_events,
                        x='الحدث',
                        y='إجمالي الدقائق',
                        title=f"أعلى 5 أحداث توقف خلال الفترة",
                        color='إجمالي الدقائق',
                        color_continuous_scale='sunset'
                    )
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("📭 لم يتم العثور على أي أحداث توقف قابلة للحساب خلال الفترة المحددة.")
            else:
                st.warning("⚠️ لا توجد بيانات خلال الفترة المحددة.")

# ... (الأقسام الباقية tab4, tab5 تبقى كما هي) ...
