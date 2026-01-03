import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List
import io
import base64

# ===========================================
# إعدادات التطبيق الأساسية
# ===========================================
st.set_page_config(
    page_title="نظام تحليل سجلات الماكينات - MTTR/MTBF",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===========================================
# تخصيص CSS للعربية
# ===========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');

* {
    font-family: 'Tajawal', sans-serif;
    direction: rtl;
    text-align: right;
}

.main-title {
    color: #2E86AB;
    text-align: center;
    font-size: 2.8rem;
    font-weight: 700;
    margin-bottom: 1rem;
}

.sub-title {
    color: #264653;
    border-right: 5px solid #2A9D8F;
    padding-right: 15px;
    margin-top: 2rem;
    margin-bottom: 1rem;
    font-size: 1.8rem;
}

.card {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 20px;
    margin: 10px 0;
    border-right: 5px solid #2A9D8F;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.upload-box {
    border: 3px dashed #2A9D8F;
    border-radius: 15px;
    padding: 40px;
    text-align: center;
    background: rgba(42, 157, 143, 0.05);
    margin: 20px 0;
}

.stButton > button {
    background-color: #2A9D8F;
    color: white;
    font-weight: bold;
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    width: 100%;
    font-size: 16px;
}

.stButton > button:hover {
    background-color: #238276;
    color: white;
}

.metric-box {
    background: linear-gradient(135deg, #2A9D8F 0%, #264653 100%);
    color: white;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    margin: 10px;
    box-shadow: 0 6px 12px rgba(0,0,0,0.15);
}

.error-box {
    background: #FF6B6B;
    color: white;
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
}

.success-box {
    background: #4ECDC4;
    color: white;
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
}

.tab-container .stTabs [data-baseweb="tab-list"] {
    gap: 2px;
}

.tab-container .stTabs [data-baseweb="tab"] {
    height: 60px;
    white-space: pre-wrap;
    background-color: #f0f2f6;
    border-radius: 8px 8px 0 0;
    padding: 20px 10px;
}
</style>
""", unsafe_allow_html=True)

# ===========================================
# الدوال الأساسية لتحليل البيانات
# ===========================================
def parse_log_file(file_content: str) -> pd.DataFrame:
    """تحليل محتوى الملف النصي وتحويله إلى DataFrame"""
    lines = file_content.strip().split('\n')
    data = []
    
    for line in lines:
        if line.startswith("=") or not line.strip():
            continue
            
        parts = line.split("\t")
        if len(parts) < 3:
            continue
            
        date = parts[0].strip() if len(parts) > 0 else ""
        time = parts[1].strip() if len(parts) > 1 else ""
        event = parts[2].strip() if len(parts) > 2 else ""
        details = parts[3].strip() if len(parts) > 3 else ""
        
        if not date or not time:
            continue
            
        try:
            dt_str = f"{date} {time}"
            dt_obj = pd.to_datetime(dt_str, format='%d.%m.%Y %H:%M:%S', errors='coerce')
            
            if pd.isna(dt_obj):
                continue
                
            data.append({
                'Date': date,
                'Time': time,
                'DateTime': dt_obj,
                'Event': event,
                'Details': details
            })
        except:
            continue
    
    if not data:
        return pd.DataFrame()
        
    df = pd.DataFrame(data)
    df = df.sort_values('DateTime').reset_index(drop=True)
    return df

def identify_failures(df: pd.DataFrame) -> pd.DataFrame:
    """تحديد أحداث الفشل في البيانات"""
    failure_patterns = [
        'E0', 'ERROR', 'FAIL', 'STOP', 'BREAK', 
        'ALARM', 'FAULT', 'SHUTDOWN', 'EMERGENCY',
        'Machine stopped', 'Sliver break', 'Drive block',
        'E0141', 'E0430', 'E0431', 'E0451', 'E0470'
    ]
    
    failure_mask = df['Event'].str.contains('|'.join(failure_patterns), case=False, na=False)
    return df[failure_mask].copy()

def identify_repairs(df: pd.DataFrame) -> pd.DataFrame:
    """تحديد أحداث الإصلاح والاستعادة"""
    repair_patterns = [
        'START', 'RESUME', 'RUNNING', 'OPERATIONAL',
        'OK', 'NORMAL', 'ACTIVE', 'ON', 'READY',
        'Starting speed', 'Automatic mode', 'DFK active',
        'Login', 'Service mode OFF'
    ]
    
    repair_mask = df['Event'].str.contains('|'.join(repair_patterns), case=False, na=False)
    return df[repair_mask].copy()

def calculate_mttr(df: pd.DataFrame) -> Dict:
    """حساب MTTR (متوسط وقت الإصلاح)"""
    failures = identify_failures(df)
    repairs = identify_repairs(df)
    
    if failures.empty or repairs.empty:
        return {
            'mttr_hours': 0,
            'mttr_minutes': 0,
            'total_repair_time': timedelta(0),
            'repair_count': 0,
            'repair_periods': pd.DataFrame(),
            'details': 'لا توجد بيانات كافية لحساب MTTR'
        }
    
    # دمج وترتيب الأحداث
    all_events = pd.concat([failures, repairs]).sort_values('DateTime')
    all_events['Type'] = all_events['Event'].apply(
        lambda x: 'Failure' if x in failures['Event'].values else 'Repair'
    )
    
    # البحث عن أزواج فشل-إصلاح
    repair_periods = []
    current_failure = None
    failure_time = None
    
    for idx, row in all_events.iterrows():
        if row['Type'] == 'Failure' and current_failure is None:
            current_failure = row['Event']
            failure_time = row['DateTime']
        
        elif row['Type'] == 'Repair' and current_failure is not None:
            repair_time = row['DateTime']
            repair_duration = repair_time - failure_time
            
            if repair_duration.total_seconds() > 0:
                repair_periods.append({
                    'Failure_Event': current_failure,
                    'Failure_Time': failure_time,
                    'Repair_Event': row['Event'],
                    'Repair_Time': repair_time,
                    'Repair_Duration': repair_duration,
                    'Repair_Minutes': repair_duration.total_seconds() / 60,
                    'Repair_Hours': repair_duration.total_seconds() / 3600
                })
            
            current_failure = None
            failure_time = None
    
    if not repair_periods:
        return {
            'mttr_hours': 0,
            'mttr_minutes': 0,
            'total_repair_time': timedelta(0),
            'repair_count': 0,
            'repair_periods': pd.DataFrame(),
            'details': 'لم يتم العثور على فترات إصلاح كاملة'
        }
    
    repair_df = pd.DataFrame(repair_periods)
    total_repair_time = repair_df['Repair_Duration'].sum()
    repair_count = len(repair_df)
    
    mttr_hours = total_repair_time.total_seconds() / 3600 / repair_count
    mttr_minutes = mttr_hours * 60
    
    return {
        'mttr_hours': mttr_hours,
        'mttr_minutes': mttr_minutes,
        'total_repair_time': total_repair_time,
        'repair_count': repair_count,
        'repair_periods': repair_df,
        'details': f'تم حساب MTTR بناءً على {repair_count} عملية إصلاح'
    }

def calculate_mtbf(df: pd.DataFrame) -> Dict:
    """حساب MTBF (متوسط الوقت بين الأعطال)"""
    failures = identify_failures(df)
    
    if failures.empty:
        return {
            'mtbf_hours': 0,
            'mtbf_days': 0,
            'total_operation_time': timedelta(0),
            'failure_count': 0,
            'failure_intervals': pd.DataFrame(),
            'availability': 0,
            'details': 'لا توجد أحداث فشل مسجلة'
        }
    
    # ترتيب أحداث الفشل
    failures_sorted = failures.sort_values('DateTime')
    
    # حساب الفترات بين الأعطال
    intervals = []
    prev_time = df['DateTime'].min()
    
    for idx, failure in failures_sorted.iterrows():
        current_time = failure['DateTime']
        operation_time = current_time - prev_time
        
        if operation_time.total_seconds() > 0:
            intervals.append({
                'Failure_Number': idx + 1,
                'Failure_Event': failure['Event'],
                'Failure_Time': current_time,
                'Operation_Time': operation_time,
                'Operation_Hours': operation_time.total_seconds() / 3600,
                'Operation_Days': operation_time.total_seconds() / (3600 * 24)
            })
        
        prev_time = current_time
    
    # الفترة الأخيرة بعد آخر عطل
    end_time = df['DateTime'].max()
    if prev_time < end_time:
        final_interval = end_time - prev_time
        intervals.append({
            'Failure_Number': len(intervals) + 1,
            'Failure_Event': 'نهاية الفترة',
            'Failure_Time': end_time,
            'Operation_Time': final_interval,
            'Operation_Hours': final_interval.total_seconds() / 3600,
            'Operation_Days': final_interval.total_seconds() / (3600 * 24)
        })
    
    intervals_df = pd.DataFrame(intervals)
    
    if intervals_df.empty:
        return {
            'mtbf_hours': 0,
            'mtbf_days': 0,
            'total_operation_time': timedelta(0),
            'failure_count': 0,
            'failure_intervals': pd.DataFrame(),
            'availability': 0,
            'details': 'لم يتم العثور على فترات تشغيل بين الأعطال'
        }
    
    # حساب MTBF
    total_operation_time = intervals_df['Operation_Time'].sum()
    failure_count = len(failures_sorted)
    
    if failure_count > 0:
        mtbf_hours = total_operation_time.total_seconds() / 3600 / failure_count
    else:
        mtbf_hours = total_operation_time.total_seconds() / 3600
    
    mtbf_days = mtbf_hours / 24
    
    # حساب نسبة التوفر
    total_period = df['DateTime'].max() - df['DateTime'].min()
    if total_period.total_seconds() > 0:
        availability = (total_operation_time.total_seconds() / total_period.total_seconds()) * 100
    else:
        availability = 0
    
    return {
        'mtbf_hours': mtbf_hours,
        'mtbf_days': mtbf_days,
        'total_operation_time': total_operation_time,
        'failure_count': failure_count,
        'failure_intervals': intervals_df,
        'availability': availability,
        'total_period': total_period,
        'details': f'تم تحليل {failure_count} حالة فشل'
    }

def calculate_oee(mttr_data: Dict, mtbf_data: Dict) -> Dict:
    """حساب مؤشرات الأداء الشاملة"""
    availability = mtbf_data.get('availability', 0)
    
    # تقدير نسبة الأداء والجودة (يمكن تعديلها)
    performance_rate = 95.0
    quality_rate = 97.0
    
    # حساب OEE
    oee = (availability * performance_rate * quality_rate) / 10000
    
    # حساب تكرار الأعطال
    failure_frequency = 0
    if mtbf_data['failure_count'] > 0 and mtbf_data['total_period'].total_seconds() > 0:
        failure_frequency = (mtbf_data['failure_count'] / mtbf_data['total_period'].total_seconds()) * 3600 * 24
    
    return {
        'availability': availability,
        'performance_rate': performance_rate,
        'quality_rate': quality_rate,
        'oee': oee,
        'failure_frequency_per_day': failure_frequency,
        'total_uptime_hours': mtbf_data['total_operation_time'].total_seconds() / 3600,
        'total_downtime_hours': (mtbf_data['total_period'].total_seconds() - mtbf_data['total_operation_time'].total_seconds()) / 3600
    }

def generate_reliability_report(df: pd.DataFrame) -> Dict:
    """إنشاء تقرير موثوقية شامل"""
    # حساب MTTR و MTBF
    mttr_results = calculate_mttr(df)
    mtbf_results = calculate_mtbf(df)
    oee_results = calculate_oee(mttr_results, mtbf_results)
    
    # تحليل توزيع الأعطال
    failures = identify_failures(df)
    failure_dist = failures['Event'].value_counts().head(10)
    
    # إنشاء التقرير
    report = {
        'summary': {
            'total_events': len(df),
            'total_failures': len(failures),
            'total_repairs': mttr_results['repair_count'],
            'analysis_period': mtbf_results['total_period'],
            'start_date': df['DateTime'].min(),
            'end_date': df['DateTime'].max()
        },
        'mttr_analysis': mttr_results,
        'mtbf_analysis': mtbf_results,
        'oee_metrics': oee_results,
        'failure_analysis': {
            'top_failures': failure_dist,
            'critical_events': len(failures[failures['Event'].str.contains('E0', na=False)])
        }
    }
    
    # توليد توصيات
    recommendations = []
    if mttr_results['mttr_hours'] > 4:
        recommendations.append("⏰ تقليل وقت الإصلاح من خلال تحسين إجراءات الصيانة")
    if mtbf_results['mtbf_hours'] < 24:
        recommendations.append("🔧 زيادة الفترات بين الأعطال بالصيانة الوقائية")
    if oee_results['availability'] < 90:
        recommendations.append("📈 تحسين نسبة التوفر بتقليل وقت التوقف")
    
    report['recommendations'] = recommendations if recommendations else ["✅ الأداء ضمن المستويات المقبولة"]
    
    return report

# ===========================================
# واجهات العرض
# ===========================================
def display_metrics_summary(report: Dict):
    """عرض ملخص المؤشرات"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric(
            "MTTR", 
            f"{report['mttr_analysis']['mttr_hours']:.2f} ساعة",
            f"{report['mttr_analysis']['repair_count']} عملية"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric(
            "MTBF",
            f"{report['mtbf_analysis']['mtbf_hours']:.1f} ساعة",
            f"{report['mtbf_analysis']['failure_count']} عطل"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric(
            "التوفر",
            f"{report['oee_metrics']['availability']:.1f}%",
            "وقت التشغيل"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric(
            "OEE",
            f"{report['oee_metrics']['oee']:.1f}%",
            "الكفاءة الشاملة"
        )
        st.markdown('</div>', unsafe_allow_html=True)

def display_detailed_analysis(report: Dict):
    """عرض التحليل التفصيلي"""
    tab1, tab2, tab3, tab4 = st.tabs(["📊 MTTR", "🔧 MTBF", "🎯 الأداء", "💡 التوصيات"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### إحصائيات MTTR")
            mttr_df = pd.DataFrame({
                'المعيار': ['MTTR المتوسط', 'عدد عمليات الإصلاح', 'إجمالي وقت الإصلاح'],
                'القيمة': [
                    f"{report['mttr_analysis']['mttr_hours']:.2f} ساعة",
                    f"{report['mttr_analysis']['repair_count']}",
                    f"{report['mttr_analysis']['total_repair_time']}"
                ]
            })
            st.dataframe(mttr_df, use_container_width=True, hide_index=True)
        
        with col2:
            if not report['mttr_analysis']['repair_periods'].empty:
                st.markdown("#### توزيع أوقات الإصلاح")
                fig = px.histogram(
                    report['mttr_analysis']['repair_periods'],
                    x='Repair_Hours',
                    nbins=15,
                    title='توزيع مدة الإصلاحات',
                    labels={'Repair_Hours': 'المدة (ساعات)'}
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### إحصائيات MTBF")
            mtbf_df = pd.DataFrame({
                'المعيار': ['MTBF المتوسط', 'عدد الأعطال', 'إجمالي وقت التشغيل', 'نسبة التوفر'],
                'القيمة': [
                    f"{report['mtbf_analysis']['mtbf_hours']:.1f} ساعة",
                    f"{report['mtbf_analysis']['failure_count']}",
                    f"{report['mtbf_analysis']['total_operation_time']}",
                    f"{report['mtbf_analysis']['availability']:.1f}%"
                ]
            })
            st.dataframe(mtbf_df, use_container_width=True, hide_index=True)
        
        with col2:
            if not report['mtbf_analysis']['failure_intervals'].empty:
                st.markdown("#### الفترات بين الأعطال")
                fig = px.line(
                    report['mtbf_analysis']['failure_intervals'].head(10),
                    x='Failure_Number',
                    y='Operation_Hours',
                    title='الفترات الزمنية بين الأعطال',
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.markdown("#### مؤشرات الأداء الشاملة")
        col1, col2 = st.columns(2)
        
        with col1:
            oee_df = pd.DataFrame({
                'المؤشر': ['التوفر', 'الأداء', 'الجودة', 'OEE الإجمالي'],
                'النسبة (%)': [
                    report['oee_metrics']['availability'],
                    report['oee_metrics']['performance_rate'],
                    report['oee_metrics']['quality_rate'],
                    report['oee_metrics']['oee']
                ]
            })
            
            fig = px.bar(
                oee_df,
                x='المؤشر',
                y='النسبة (%)',
                color='النسبة (%)',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            perf_df = pd.DataFrame({
                'المعيار': ['إجمالي وقت التشغيل', 'إجمالي وقت التوقف', 'تكرار الأعطال/يوم'],
                'القيمة': [
                    f"{report['oee_metrics']['total_uptime_hours']:.1f} ساعة",
                    f"{report['oee_metrics']['total_downtime_hours']:.1f} ساعة",
                    f"{report['oee_metrics']['failure_frequency_per_day']:.2f}"
                ]
            })
            st.dataframe(perf_df, use_container_width=True, hide_index=True)
    
    with tab4:
        st.markdown("#### التوصيات")
        
        summary = report['summary']
        st.markdown(f"""
        **ملخص الفترة:**
        - بداية التحليل: {summary['start_date']}
        - نهاية التحليل: {summary['end_date']}
        - إجمالي الأحداث: {summary['total_events']}
        - أحداث الفشل: {summary['total_failures']}
        - عمليات الإصلاح: {summary['total_repairs']}
        """)
        
        st.markdown("**توصيات التحسين:**")
        for i, rec in enumerate(report['recommendations'], 1):
            st.markdown(f"{i}. {rec}")

# ===========================================
# الوظيفة الرئيسية للتطبيق
# ===========================================
def main():
    """الوظيفة الرئيسية للتطبيق"""
    
    # عرض العنوان الرئيسي
    st.markdown('<h1 class="main-title">⚙️ نظام تحليل مؤشرات الموثوقية MTTR/MTBF</h1>', unsafe_allow_html=True)
    
    # الشريط الجانبي
    with st.sidebar:
        st.markdown("### 📂 تحميل البيانات")
        
        upload_option = st.radio(
            "اختر طريقة التحميل:",
            ["📤 رفع ملف", "📝 لصق النص", "🔗 رابط خارجي"]
        )
        
        file_content = None
        
        if upload_option == "📤 رفع ملف":
            uploaded_file = st.file_uploader(
                "اختر ملف السجل (TXT أو LOG)",
                type=['txt', 'log'],
                help="يمكنك رفع ملفات النصوص"
            )
            if uploaded_file:
                file_content = uploaded_file.getvalue().decode("utf-8")
                st.success(f"✅ تم تحميل الملف: {uploaded_file.name}")
        
        elif upload_option == "📝 لصق النص":
            file_content = st.text_area(
                "الصق محتوى السجل هنا:",
                height=200,
                placeholder="23.12.2024\t19:06:26\tStarting speed\tON\n23.12.2024\t19:06:56\tAutomatic mode\t"
            )
        
        elif upload_option == "🔗 رابط خارجي":
            url = st.text_input("أدخل رابط الملف:")
            if url:
                try:
                    import requests
                    response = requests.get(url)
                    if response.status_code == 200:
                        file_content = response.text
                        st.success("✅ تم تحميل الملف بنجاح!")
                    else:
                        st.error("❌ تعذر تحميل الملف")
                except:
                    st.error("❌ حدث خطأ أثناء تحميل الملف")
        
        st.markdown("---")
        st.markdown("### 📊 حول المؤشرات")
        st.markdown("""
        **MTTR:** متوسط وقت الإصلاح  
        **MTBF:** متوسط الوقت بين الأعطال  
        **التوفر:** نسبة وقت التشغيل  
        **OEE:** الكفاءة الشاملة
        """)
        
        st.markdown("---")
        st.markdown("### 🎯 الأهداف المرجعية")
        st.markdown("""
        - MTTR ممتاز: < 2 ساعة
        - MTBF ممتاز: > 168 ساعة
        - التوفر ممتاز: > 95%
        - OEE ممتاز: > 85%
        """)
    
    # المحتوى الرئيسي
    if file_content:
        try:
            with st.spinner("🔄 جاري معالجة البيانات وتحليل المؤشرات..."):
                # تحليل الملف
                df = parse_log_file(file_content)
                
                if df.empty:
                    st.error("❌ لم يتم العثور على بيانات صالحة في الملف")
                    st.info("تأكد من تنسيق البيانات:\n- التاريخ: DD.MM.YYYY\n- الوقت: HH:MM:SS\n- الفواصل: TAB")
                    return
                
                st.success(f"✅ تم تحميل {len(df)} حدث بنجاح")
                
                # إنشاء تقرير التحليل
                report = generate_reliability_report(df)
                
                # عرض النتائج
                st.markdown('<h2 class="sub-title">📈 نتائج التحليل</h2>', unsafe_allow_html=True)
                
                # عرض المؤشرات الرئيسية
                display_metrics_summary(report)
                
                # عرض التحليل التفصيلي
                st.markdown('<h2 class="sub-title">🔍 التحليل التفصيلي</h2>', unsafe_allow_html=True)
                display_detailed_analysis(report)
                
                # قسم التصدير
                st.markdown('<h2 class="sub-title">📥 تصدير النتائج</h2>', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("💾 حفظ التقرير كـ CSV"):
                        # تجهيز البيانات للتصدير
                        export_data = {
                            'المعيار': [
                                'MTTR (ساعة)', 'MTBF (ساعة)', 'نسبة التوفر %',
                                'OEE %', 'عدد الأعطال', 'عدد عمليات الإصلاح'
                            ],
                            'القيمة': [
                                report['mttr_analysis']['mttr_hours'],
                                report['mtbf_analysis']['mtbf_hours'],
                                report['oee_metrics']['availability'],
                                report['oee_metrics']['oee'],
                                report['mtbf_analysis']['failure_count'],
                                report['mttr_analysis']['repair_count']
                            ]
                        }
                        
                        export_df = pd.DataFrame(export_data)
                        csv = export_df.to_csv(index=False, encoding='utf-8-sig')
                        
                        st.download_button(
                            label="تحميل CSV",
                            data=csv,
                            file_name="reliability_report.csv",
                            mime="text/csv"
                        )
                
                with col2:
                    if st.button("📊 تصدير بيانات MTTR"):
                        if not report['mttr_analysis']['repair_periods'].empty:
                            csv = report['mttr_analysis']['repair_periods'].to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                label="تحميل بيانات MTTR",
                                data=csv,
                                file_name="mttr_data.csv",
                                mime="text/csv"
                            )
                
                with col3:
                    if st.button("🔧 تصدير بيانات MTBF"):
                        if not report['mtbf_analysis']['failure_intervals'].empty:
                            csv = report['mtbf_analysis']['failure_intervals'].to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                label="تحميل بيانات MTBF",
                                data=csv,
                                file_name="mtbf_data.csv",
                                mime="text/csv"
                            )
                
                # قسم البيانات الخام
                with st.expander("📋 عرض البيانات الخام"):
                    st.dataframe(df[['Date', 'Time', 'Event', 'Details']], use_container_width=True)
                
        except Exception as e:
            st.error(f"❌ حدث خطأ أثناء معالجة البيانات: {str(e)}")
            st.info("تأكد من تنسيق الملف واتبع التعليمات في الشريط الجانبي")
    
    else:
        # صفحة الترحيب
        st.markdown('<div class="upload-box">', unsafe_allow_html=True)
        st.markdown("## 📤 ابدأ بتحميل ملف السجل")
        st.markdown("""
        **لتشغيل النظام:**
        1. اختر طريقة تحميل البيانات من الشريط الجانبي
        2. قم برفع ملف السجل أو لصق محتواه
        3. انتظر تحليل البيانات وعرض النتائج
        4. استعرض التقارير وحمّلها
        
        **تنسيق الملف المدعوم:**
        - ملف نصي (.txt أو .log)
        - التاريخ: `DD.MM.YYYY`
        - الوقت: `HH:MM:SS`
        - الفواصل: TAB
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # عرض مثال
        st.markdown('<h3 class="sub-title">📝 مثال على تنسيق البيانات</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("**مثال للبيانات:**")
            st.code("""
23.12.2024\t19:06:26\tStarting speed\tON
23.12.2024\t19:06:56\tAutomatic mode\t
23.12.2024\t19:11:04\tThick spots\tW0547
23.12.2024\t19:13:18\tDFK deactivated\tW0534
23.12.2024\t19:29:45\tCode barred again\t
23.12.2024\t19:49:13\tCan magazine is empty\tW0523
            """)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("**المؤشرات التي يتم حسابها:**")
            
            metrics = [
                ("MTTR", "متوسط وقت الإصلاح", "< 2 ساعة"),
                ("MTBF", "متوسط الوقت بين الأعطال", "> 168 ساعة"),
                ("التوفر", "نسبة وقت التشغيل", "> 95%"),
                ("OEE", "الكفاءة الشاملة", "> 85%"),
                ("عدد الأعطال", "أحداث الفشل المسجلة", "-"),
                ("وقت الإصلاح", "إجمالي وقت التوقف", "-")
            ]
            
            for name, desc, target in metrics:
                st.markdown(f"**{name}:** {desc}")
                if target:
                    st.markdown(f"*الهدف: {target}*")
                st.markdown("---")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # توجيهات سريعة
        st.markdown('<h3 class="sub-title">🚀 نصائح سريعة</h3>', unsafe_allow_html=True)
        
        tips = [
            "✅ تأكد من صحة تنسيق التاريخ والوقت",
            "✅ استخدم الفواصل التاب (TAB) بين الحقول",
            "✅ احفظ التقارير لمتابعة الأداء عبر الزمن",
            "✅ استشر التوصيات لتحسين أداء المعدات"
        ]
        
        for tip in tips:
            st.markdown(f"- {tip}")

# ===========================================
# تشغيل التطبيق
# ===========================================
if __name__ == "__main__":
    main()
