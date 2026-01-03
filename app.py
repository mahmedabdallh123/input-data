import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import io
import base64
from pathlib import Path

# إعداد صفحة Streamlit
st.set_page_config(
    page_title="تحليل سجلات الماكينات",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تخصيص التصميم مع دعم اللغة العربية
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    
    * {
        font-family: 'Cairo', sans-serif;
    }
    
    .main-header {
        text-align: center;
        color: #2E86AB;
        margin-bottom: 2rem;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .sub-header {
        color: #264653;
        border-right: 5px solid #2A9D8F;
        padding-right: 15px;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    
    .card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-right: 4px solid #E76F51;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #2A9D8F 0%, #264653 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 10px;
    }
    
    .stButton > button {
        width: 100%;
        background-color: #2A9D8F;
        color: white;
        font-weight: bold;
        border: none;
        padding: 10px;
        border-radius: 5px;
    }
    
    .stButton > button:hover {
        background-color: #238276;
    }
    
    .upload-section {
        border: 2px dashed #2A9D8F;
        border-radius: 10px;
        padding: 30px;
        text-align: center;
        margin: 20px 0;
        background-color: rgba(42, 157, 143, 0.05);
    }
</style>
""", unsafe_allow_html=True)

# عنوان التطبيق
st.markdown('<h1 class="main-header">📊 نظام تحليل سجلات الماكينات</h1>', unsafe_allow_html=True)

def parse_log_file(file_content):
    """
    تحليل ملف السجل وتحويله إلى DataFrame
    """
    lines = file_content.split('\n')
    data = []
    
    for line in lines:
        if line.startswith("=") or line.strip() == "":
            continue
        
        parts = line.split("\t")
        while len(parts) < 4:
            parts.append("")
        
        if len(parts) >= 4:
            # تنظيف البيانات
            date = parts[0].strip()
            time = parts[1].strip()
            event = parts[2].strip()
            details = parts[3].strip()
            
            # التحقق من صحة التاريخ والوقت
            try:
                if date and time:
                    datetime_str = f"{date} {time}"
                    datetime_obj = pd.to_datetime(datetime_str, format='%d.%m.%Y %H:%M:%S')
                    data.append({
                        'Date': date,
                        'Time': time,
                        'DateTime': datetime_obj,
                        'Event': event,
                        'Details': details
                    })
            except:
                continue
    
    df = pd.DataFrame(data)
    return df

def calculate_time_analysis(df):
    """
    تحليل الوقت بين الأحداث
    """
    analysis_results = {}
    
    # حساب الفترات بين الأحداث المتشابهة
    df_sorted = df.sort_values('DateTime')
    df_sorted['TimeDiff'] = df_sorted['DateTime'].diff()
    df_sorted['PrevEvent'] = df_sorted['Event'].shift(1)
    
    # الفترات للأحداث المتشابهة المتتالية
    same_events = df_sorted[df_sorted['Event'] == df_sorted['PrevEvent']]
    
    if not same_events.empty:
        same_events_summary = same_events.groupby('Event').agg({
            'TimeDiff': ['count', 'mean', 'min', 'max']
        }).round(2)
        analysis_results['same_events'] = same_events_summary
    
    # الفترات بين أزواج الأحداث المختلفة
    event_sequences = []
    for i in range(len(df_sorted) - 1):
        start_event = df_sorted.iloc[i]['Event']
        end_event = df_sorted.iloc[i + 1]['Event']
        time_diff = df_sorted.iloc[i + 1]['DateTime'] - df_sorted.iloc[i]['DateTime']
        
        event_sequences.append({
            'From': start_event,
            'To': end_event,
            'Duration': time_diff,
            'Duration_Minutes': time_diff.total_seconds() / 60
        })
    
    analysis_results['sequences'] = pd.DataFrame(event_sequences)
    
    return analysis_results

def create_dashboard(df):
    """
    إنشاء لوحة تحكم تفاعلية
    """
    # قسم المقاييس الرئيسية
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("إجمالي الأحداث", len(df))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("أنواع الأحداث", df['Event'].nunique())
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        duration = (df['DateTime'].max() - df['DateTime'].min()).days
        st.metric("المدة الزمنية (أيام)", duration)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        avg_events = len(df) / max(duration, 1)
        st.metric("متوسط الأحداث/يوم", f"{avg_events:.1f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # تخطيط المحتوى
    tab1, tab2, tab3, tab4 = st.tabs(["📈 نظرة عامة", "🔄 تحليل الأحداث", "⏱️ تحليل الوقت", "📋 التقارير"])
    
    with tab1:
        st.markdown('<h3 class="sub-header">نظرة عامة على البيانات</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # توزيع الأحداث حسب النوع
            event_counts = df['Event'].value_counts().head(10)
            fig1 = px.bar(
                event_counts, 
                x=event_counts.values,
                y=event_counts.index,
                orientation='h',
                title="أكثر 10 أحداث تكراراً",
                labels={'x': 'عدد التكرارات', 'y': 'الحدث'},
                color=event_counts.values,
                color_continuous_scale='Viridis'
            )
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # جدول البيانات
            st.markdown('<h4>عينة من البيانات</h4>', unsafe_allow_html=True)
            st.dataframe(
                df[['Date', 'Time', 'Event', 'Details']].head(20),
                height=400,
                use_container_width=True
            )
    
    with tab2:
        st.markdown('<h3 class="sub-header">تحليل تفصيلي للأحداث</h3>', unsafe_allow_html=True)
        
        # فلتر الأحداث
        selected_events = st.multiselect(
            "اختر الأحداث للتحليل:",
            options=df['Event'].unique(),
            default=df['Event'].value_counts().head(5).index.tolist()
        )
        
        if selected_events:
            filtered_df = df[df['Event'].isin(selected_events)]
            
            col1, col2 = st.columns(2)
            
            with col1:
                # مخطط توزيع الأحداث المحددة
                fig2 = px.pie(
                    filtered_df,
                    names='Event',
                    title='توزيع الأحداث المحددة',
                    hole=0.4
                )
                fig2.update_layout(height=400)
                st.plotly_chart(fig2, use_container_width=True)
            
            with col2:
                # جدول تفصيلي
                event_summary = filtered_df.groupby('Event').agg({
                    'DateTime': ['count', 'min', 'max']
                }).round(2)
                event_summary.columns = ['العدد', 'أول ظهور', 'آخر ظهور']
                st.dataframe(event_summary, use_container_width=True)
    
    with tab3:
        st.markdown('<h3 class="sub-header">تحليل الفترات الزمنية</h3>', unsafe_allow_html=True)
        
        # حساب التحليلات الزمنية
        analysis = calculate_time_analysis(df)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<h4>الفترات بين الأحداث المتشابهة</h4>', unsafe_allow_html=True)
            if 'same_events' in analysis:
                st.dataframe(analysis['same_events'], use_container_width=True)
        
        with col2:
            st.markdown('<h4>تحليل تسلسل الأحداث</h4>', unsafe_allow_html=True)
            # اختيار تسلسل محدد
            unique_events = df['Event'].unique()
            from_event = st.selectbox("من الحدث:", unique_events)
            to_event = st.selectbox("إلى الحدث:", unique_events)
            
            if from_event and to_event:
                sequences = analysis['sequences']
                specific_seq = sequences[
                    (sequences['From'] == from_event) & 
                    (sequences['To'] == to_event)
                ]
                
                if not specific_seq.empty:
                    st.write(f"**المدة المتوسطة:** {specific_seq['Duration_Minutes'].mean():.2f} دقيقة")
                    st.write(f"**عدد المرات:** {len(specific_seq)}")
                    
                    # مخطط التوزيع
                    fig3 = px.histogram(
                        specific_seq,
                        x='Duration_Minutes',
                        title=f'توزيع المدة بين {from_event} و {to_event}',
                        nbins=20
                    )
                    fig3.update_layout(height=300)
                    st.plotly_chart(fig3, use_container_width=True)
    
    with tab4:
        st.markdown('<h3 class="sub-header">التقارير والتصدير</h3>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 تصدير البيانات الكاملة", use_container_width=True):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="تحميل CSV",
                    data=csv,
                    file_name="machine_logs_complete.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("📊 تصدير الإحصائيات", use_container_width=True):
                stats = df.groupby('Event').agg({
                    'DateTime': ['count', 'min', 'max']
                })
                stats_csv = stats.to_csv()
                st.download_button(
                    label="تحميل الإحصائيات",
                    data=stats_csv,
                    file_name="machine_logs_stats.csv",
                    mime="text/csv"
                )
        
        with col3:
            if st.button("⏱️ تصدير تحليل الوقت", use_container_width=True):
                analysis = calculate_time_analysis(df)
                time_csv = analysis['sequences'].to_csv(index=False)
                st.download_button(
                    label="تحميل تحليل الوقت",
                    data=time_csv,
                    file_name="time_analysis.csv",
                    mime="text/csv"
                )
        
        # تقرير مخصص
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📋 تقرير مخصص")
        
        report_type = st.radio(
            "نوع التقرير:",
            ["ملخص الأحداث", "تحليل الزمن", "المشاكل الشائعة", "جميع البيانات"]
        )
        
        if st.button("إنشاء التقرير", use_container_width=True):
            with st.spinner("جاري إنشاء التقرير..."):
                if report_type == "ملخص الأحداث":
                    summary = df['Event'].value_counts().reset_index()
                    summary.columns = ['الحدث', 'التكرار']
                    st.dataframe(summary, use_container_width=True)
                
                elif report_type == "تحليل الزمن":
                    analysis = calculate_time_analysis(df)
                    st.dataframe(analysis['sequences'].head(50), use_container_width=True)
                
                elif report_type == "المشاكل الشائعة":
                    errors = df[df['Event'].str.contains('E0|W0', na=False)]
                    st.dataframe(errors, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

def main():
    """
    الوظيفة الرئيسية للتطبيق
    """
    # الشريط الجانبي
    with st.sidebar:
        st.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=100)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("### ⚙️ إعدادات التطبيق")
        
        upload_option = st.radio(
            "طريقة تحميل البيانات:",
            ["رفع ملف", "إدخال النص", "رابط مباشر"]
        )
        
        uploaded_file = None
        file_content = None
        
        if upload_option == "رفع ملف":
            st.markdown('<div class="upload-section">', unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "اختر ملف السجل",
                type=['txt', 'log', 'csv'],
                help="يمكنك رفع ملفات TXT أو LOG"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            if uploaded_file is not None:
                file_content = uploaded_file.getvalue().decode("utf-8")
        
        elif upload_option == "إدخال النص":
            file_content = st.text_area(
                "الصق محتوى السجل هنا:",
                height=200,
                help="الصق محتوى الملف النصي هنا"
            )
        
        else:  # رابط مباشر
            url = st.text_input("أدخل رابط الملف:")
            if url:
                try:
                    import requests
                    response = requests.get(url)
                    if response.status_code == 200:
                        file_content = response.text
                        st.success("تم تحميل الملف بنجاح!")
                except:
                    st.error("تعذر تحميل الملف من الرابط")
        
        # معلومات إضافية
        st.markdown("---")
        st.markdown("### ℹ️ معلومات")
        st.markdown("""
        - يدعم ملفات سجلات الماكينات
        - تحليل الفترات الزمنية بين الأحداث
        - تصدير التقارير بصيغة CSV
        - واجهة باللغة العربية
        """)
    
    # المحتوى الرئيسي
    if file_content:
        try:
            with st.spinner("جاري معالجة البيانات..."):
                df = parse_log_file(file_content)
                
                if df.empty:
                    st.error("لم يتم العثور على بيانات صالحة في الملف")
                    return
                
                # عرض لوحة التحكم
                create_dashboard(df)
                
                # قسم التحليل المتقدم
                st.markdown("---")
                st.markdown('<h2 class="sub-header">🔍 تحليل متقدم</h2>', unsafe_allow_html=True)
                
                advanced_tab1, advanced_tab2 = st.tabs(["بحث متقدم", "مقارنة"])
                
                with advanced_tab1:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        search_term = st.text_input("بحث في الأحداث:")
                        if search_term:
                            results = df[df['Event'].str.contains(search_term, case=False, na=False)]
                            st.write(f"عدد النتائج: {len(results)}")
                            st.dataframe(results[['Date', 'Time', 'Event', 'Details']], use_container_width=True)
                    
                    with col2:
                        date_range = st.date_input(
                            "اختر نطاق تاريخي:",
                            value=(df['DateTime'].min().date(), df['DateTime'].max().date())
                        )
                        
                        if len(date_range) == 2:
                            mask = (df['DateTime'].dt.date >= date_range[0]) & \
                                   (df['DateTime'].dt.date <= date_range[1])
                            filtered = df[mask]
                            st.write(f"الأحداث في النطاق المحدد: {len(filtered)}")
                
                with advanced_tab2:
                    st.markdown("### مقارنة بين الأحداث")
                    event1, event2 = st.columns(2)
                    
                    with event1:
                        e1 = st.selectbox("الحدث الأول:", df['Event'].unique())
                    
                    with event2:
                        e2 = st.selectbox("الحدث الثاني:", df['Event'].unique())
                    
                    if e1 and e2:
                        df1 = df[df['Event'] == e1]
                        df2 = df[df['Event'] == e2]
                        
                        comparison = pd.DataFrame({
                            'المعيار': ['التكرار', 'أول ظهور', 'آخر ظهور', 'المتوسط الزمني'],
                            e1: [
                                len(df1),
                                df1['DateTime'].min(),
                                df1['DateTime'].max(),
                                df1['DateTime'].diff().mean().total_seconds() / 60 if len(df1) > 1 else 0
                            ],
                            e2: [
                                len(df2),
                                df2['DateTime'].min(),
                                df2['DateTime'].max(),
                                df2['DateTime'].diff().mean().total_seconds() / 60 if len(df2) > 1 else 0
                            ]
                        })
                        
                        st.dataframe(comparison, use_container_width=True)
        
        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة البيانات: {str(e)}")
    
    else:
        # صفحة الترحيب
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("""
        ## 🚀 مرحباً بك في نظام تحليل سجلات الماكينات
        
        ### كيفية الاستخدام:
        1. **رفع ملف السجل** من الشريط الجانبي
        2. **اختيار طريقة التحليل** المطلوبة
        3. **استعراض النتائج** والرسوم البيانية
        4. **تصدير التقارير** بصيغة CSV
        
        ### المميزات:
        - 📊 تحليل الفترات الزمنية بين الأحداث
        - 📈 رسوم بيانية تفاعلية
        - 🔍 بحث متقدم في البيانات
        - 📥 تصدير التقارير بسهولة
        - 📱 متوافق مع جميع الأجهزة
        
        ### أنواع الملفات المدعومة:
        - ملفات نصية (.txt)
        - سجلات النظام (.log)
        - ملفات CSV
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # أمثلة
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 📋 مثال للبيانات")
            st.code("""23.12.2024\t19:06:26\tStarting speed\tON
23.12.2024\t19:06:56\tAutomatic mode\t
23.12.2024\t19:11:04\tThick spots\tW0547""")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### ⏱️ مثال للتحليل")
            st.metric("المدة المتوسطة بين الأحداث", "15.2 دقيقة")
            st.metric("عدد أحداث التشغيل", "48 مرة")
            st.metric("المشاكل المسجلة", "12 حالة")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 💡 نصائح سريعة")
            st.markdown("""
            1. تأكد من تنسيق التاريخ
            2. استخدم الفواصل بين الحقول
            3. احفظ التقارير بانتظام
            4. استخدم البحث للتصفية
            """)
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
