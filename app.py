import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import io
import base64
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# إعداد صفحة Streamlit
st.set_page_config(
    page_title="تحليل سجلات الماكينات - MTTR/MTBF",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تخصيص التصميم مع إضافات جديدة
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
    
    .mttr-card {
        background: linear-gradient(135deg, #FF6B6B 0%, #C44569 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .mtbf-card {
        background: linear-gradient(135deg, #4ECDC4 0%, #44A08D 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .availability-card {
        background: linear-gradient(135deg, #FFD166 0%, #FF9E00 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .critical-event {
        background-color: #ffeaea;
        border-left: 5px solid #ff6b6b;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
    }
    
    .normal-event {
        background-color: #e8f4fd;
        border-left: 5px solid #2E86AB;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ===========================================
# وظائف حساب MTTR و MTBF الجديدة
# ============================================

def identify_failure_events(df: pd.DataFrame) -> pd.DataFrame:
    """
    تحديد أحداث الفشل من البيانات
    """
    # قائمة بأنماط أحداث الفشل الشائعة
    failure_patterns = [
        'E0', 'ERROR', 'FAIL', 'STOP', 'BREAK', 
        'ALARM', 'FAULT', 'SHUTDOWN', 'EMERGENCY',
        'E0141', 'E0430', 'E0431', 'E0451', 'E0470',
        'Machine stopped', 'Sliver break', 'Drive block'
    ]
    
    failure_events = []
    for pattern in failure_patterns:
        mask = df['Event'].str.contains(pattern, case=False, na=False)
        failure_events.extend(df[mask]['Event'].unique())
    
    # إزالة التكرارات
    failure_events = list(set(failure_events))
    
    # فلترة البيانات للأحداث الفشل فقط
    failure_df = df[df['Event'].isin(failure_events)].copy()
    
    return failure_df

def identify_repair_events(df: pd.DataFrame) -> pd.DataFrame:
    """
    تحديد أحداث الإصلاح والاستعادة
    """
    repair_patterns = [
        'START', 'RESUME', 'RUNNING', 'OPERATIONAL',
        'OK', 'NORMAL', 'ACTIVE', 'ON', 'READY',
        'Starting speed', 'Automatic mode', 'DFK active',
        'Login', 'Service mode OFF'
    ]
    
    repair_events = []
    for pattern in repair_patterns:
        mask = df['Event'].str.contains(pattern, case=False, na=False)
        repair_events.extend(df[mask]['Event'].unique())
    
    repair_events = list(set(repair_events))
    repair_df = df[df['Event'].isin(repair_events)].copy()
    
    return repair_df

def calculate_mttr(df: pd.DataFrame) -> Dict:
    """
    حساب MTTR (Mean Time To Repair)
    MTTR = مجموع أوقات الإصلاح / عدد عمليات الإصلاح
    """
    # تحديد أحداث الفشل والإصلاح
    failure_events = identify_failure_events(df)
    repair_events = identify_repair_events(df)
    
    if failure_events.empty or repair_events.empty:
        return {
            'mttr_hours': 0,
            'mttr_minutes': 0,
            'total_repair_time': timedelta(0),
            'repair_count': 0,
            'repair_periods': pd.DataFrame(),
            'details': 'لا توجد بيانات كافية لحساب MTTR'
        }
    
    # ترتيب الأحداث حسب الوقت
    all_events = pd.concat([failure_events, repair_events]).sort_values('DateTime')
    all_events = all_events.reset_index(drop=True)
    
    # البحث عن أزواج الفشل-إصلاح
    repair_periods = []
    current_failure = None
    failure_time = None
    
    for idx, row in all_events.iterrows():
        event_type = 'failure' if row['Event'] in failure_events['Event'].values else 'repair'
        
        if event_type == 'failure' and current_failure is None:
            current_failure = row['Event']
            failure_time = row['DateTime']
        
        elif event_type == 'repair' and current_failure is not None:
            repair_time = row['DateTime']
            repair_duration = repair_time - failure_time
            
            # التأكد من أن مدة الإصلاح معقولة (أقل من 24 ساعة)
            if repair_duration.total_seconds() > 0 and repair_duration.total_seconds() < 24 * 3600:
                repair_periods.append({
                    'failure_event': current_failure,
                    'failure_time': failure_time,
                    'repair_event': row['Event'],
                    'repair_time': repair_time,
                    'repair_duration': repair_duration,
                    'repair_duration_minutes': repair_duration.total_seconds() / 60,
                    'repair_duration_hours': repair_duration.total_seconds() / 3600
                })
            
            current_failure = None
            failure_time = None
    
    repair_periods_df = pd.DataFrame(repair_periods)
    
    if repair_periods_df.empty:
        return {
            'mttr_hours': 0,
            'mttr_minutes': 0,
            'total_repair_time': timedelta(0),
            'repair_count': 0,
            'repair_periods': pd.DataFrame(),
            'details': 'لم يتم العثور على فترات إصلاح كاملة'
        }
    
    # حساب MTTR
    total_repair_time = repair_periods_df['repair_duration'].sum()
    repair_count = len(repair_periods_df)
    mttr_hours = total_repair_time.total_seconds() / 3600 / repair_count if repair_count > 0 else 0
    mttr_minutes = mttr_hours * 60
    
    return {
        'mttr_hours': mttr_hours,
        'mttr_minutes': mttr_minutes,
        'total_repair_time': total_repair_time,
        'repair_count': repair_count,
        'repair_periods': repair_periods_df,
        'details': f'تم حساب MTTR بناءً على {repair_count} عملية إصلاح'
    }

def calculate_mtbf(df: pd.DataFrame) -> Dict:
    """
    حساب MTBF (Mean Time Between Failures)
    MTBF = إجمالي وقت التشغيل / عدد حالات الفشل
    """
    failure_events = identify_failure_events(df)
    
    if failure_events.empty:
        return {
            'mtbf_hours': 0,
            'mtbf_days': 0,
            'total_operation_time': timedelta(0),
            'failure_count': 0,
            'failure_intervals': pd.DataFrame(),
            'availability': 0,
            'details': 'لا توجد أحداث فشل مسجلة'
        }
    
    # تحديد وقت بداية ونهاية السجل
    start_time = df['DateTime'].min()
    end_time = df['DateTime'].max()
    total_period = end_time - start_time
    
    # ترتيب أحداث الفشل
    failures_sorted = failure_events.sort_values('DateTime')
    failures_sorted = failures_sorted.reset_index(drop=True)
    
    # حساب الفترات بين حالات الفشل
    failure_intervals = []
    prev_failure_time = start_time
    
    for idx, row in failures_sorted.iterrows():
        failure_time = row['DateTime']
        operation_time = failure_time - prev_failure_time
        
        # التأكد من أن الفترة موجبة ومعقولة
        if operation_time.total_seconds() > 0:
            failure_intervals.append({
                'failure_number': idx + 1,
                'failure_event': row['Event'],
                'failure_time': failure_time,
                'operation_time_since_last_failure': operation_time,
                'operation_hours': operation_time.total_seconds() / 3600,
                'operation_days': operation_time.total_seconds() / (3600 * 24)
            })
        
        prev_failure_time = failure_time
    
    # إضافة الفترة الأخيرة بعد آخر عطل
    if prev_failure_time < end_time:
        final_operation_time = end_time - prev_failure_time
        failure_intervals.append({
            'failure_number': len(failure_intervals) + 1,
            'failure_event': 'نهاية الفترة',
            'failure_time': end_time,
            'operation_time_since_last_failure': final_operation_time,
            'operation_hours': final_operation_time.total_seconds() / 3600,
            'operation_days': final_operation_time.total_seconds() / (3600 * 24)
        })
    
    failure_intervals_df = pd.DataFrame(failure_intervals)
    
    if failure_intervals_df.empty:
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
    total_operation_time = failure_intervals_df['operation_time_since_last_failure'].sum()
    failure_count = len(failures_sorted)
    
    if failure_count > 0:
        mtbf_hours = total_operation_time.total_seconds() / 3600 / failure_count
        mtbf_days = mtbf_hours / 24
    else:
        mtbf_hours = total_operation_time.total_seconds() / 3600
        mtbf_days = mtbf_hours / 24
    
    # حساب نسبة التوفر
    availability = (total_operation_time.total_seconds() / total_period.total_seconds()) * 100 if total_period.total_seconds() > 0 else 0
    
    return {
        'mtbf_hours': mtbf_hours,
        'mtbf_days': mtbf_days,
        'total_operation_time': total_operation_time,
        'failure_count': failure_count,
        'failure_intervals': failure_intervals_df,
        'availability': availability,
        'total_period': total_period,
        'details': f'تم تحليل {failure_count} حالة فشل على مدار {total_period}'
    }

def calculate_oee_metrics(df: pd.DataFrame, mttr_data: Dict, mtbf_data: Dict) -> Dict:
    """
    حساب مؤشرات الأداء الشاملة (OEE Metrics)
    """
    # حساب نسبة التوفر (Availability)
    availability = mtbf_data.get('availability', 0)
    
    # حساب نسبة الجودة (Quality Rate) - تقديرية
    # نفترض أن 95% من وقت التشغيل ينتج جودة مقبولة
    quality_rate = 95.0  # يمكن تعديلها بناءً على البيانات الفعلية
    
    # حساب نسبة الأداء (Performance Rate)
    total_time = mtbf_data.get('total_period', timedelta(0))
    operation_time = mtbf_data.get('total_operation_time', timedelta(0))
    
    if total_time.total_seconds() > 0:
        performance_rate = (operation_time.total_seconds() / total_time.total_seconds()) * 100
    else:
        performance_rate = 0
    
    # حساب OEE الإجمالي
    oee = (availability * quality_rate * performance_rate) / 10000
    
    # حساب تكرار الأعطال
    failure_frequency = 0
    if mtbf_data['failure_count'] > 0 and total_time.total_seconds() > 0:
        failure_frequency = (mtbf_data['failure_count'] / total_time.total_seconds()) * 3600 * 24  # أعطال/يوم
    
    return {
        'availability': availability,
        'performance_rate': performance_rate,
        'quality_rate': quality_rate,
        'oee': oee,
        'failure_frequency_per_day': failure_frequency,
        'mttr_hours': mttr_data.get('mttr_hours', 0),
        'mtbf_hours': mtbf_data.get('mtbf_hours', 0),
        'total_downtime_hours': (total_time - operation_time).total_seconds() / 3600,
        'total_uptime_hours': operation_time.total_seconds() / 3600
    }

def create_reliability_report(df: pd.DataFrame) -> Dict:
    """
    إنشاء تقرير موثوقية شامل
    """
    # حساب MTTR و MTBF
    mttr_results = calculate_mttr(df)
    mtbf_results = calculate_mtbf(df)
    
    # حساب مؤشرات OEE
    oee_metrics = calculate_oee_metrics(df, mttr_results, mtbf_results)
    
    # تحليل توزيع الأعطال
    failure_events = identify_failure_events(df)
    failure_distribution = failure_events['Event'].value_counts().head(10)
    
    # تحليل تأثير الأعطال
    critical_events = failure_events[failure_events['Event'].str.contains('E0', na=False)]
    
    report = {
        'summary': {
            'total_events': len(df),
            'total_failures': len(failure_events),
            'total_repairs': mttr_results['repair_count'],
            'analysis_period': mtbf_results.get('total_period', timedelta(0)),
            'start_date': df['DateTime'].min(),
            'end_date': df['DateTime'].max()
        },
        'mttr_analysis': mttr_results,
        'mtbf_analysis': mtbf_results,
        'oee_metrics': oee_metrics,
        'failure_analysis': {
            'top_failures': failure_distribution,
            'critical_events_count': len(critical_events),
            'failure_trend': analyze_failure_trend(failure_events)
        },
        'recommendations': generate_recommendations(mttr_results, mtbf_results, oee_metrics)
    }
    
    return report

def analyze_failure_trend(failure_df: pd.DataFrame) -> Dict:
    """
    تحليل اتجاهات الأعطال مع الوقت
    """
    if failure_df.empty:
        return {'trend': 'ثابت', 'change_percentage': 0}
    
    failure_df = failure_df.copy()
    failure_df['Date'] = failure_df['DateTime'].dt.date
    daily_failures = failure_df.groupby('Date').size()
    
    if len(daily_failures) > 1:
        # حساب الاتجاه
        x = np.arange(len(daily_failures))
        y = daily_failures.values
        slope, _ = np.polyfit(x, y, 1)
        
        if slope > 0.1:
            trend = 'تصاعدي'
        elif slope < -0.1:
            trend = 'تنازلي'
        else:
            trend = 'ثابت'
        
        change_percentage = ((daily_failures.iloc[-1] - daily_failures.iloc[0]) / daily_failures.iloc[0]) * 100
    else:
        trend = 'غير محدد'
        change_percentage = 0
    
    return {'trend': trend, 'change_percentage': change_percentage}

def generate_recommendations(mttr_data: Dict, mtbf_data: Dict, oee_data: Dict) -> List[str]:
    """
    توليد توصيات بناءً على نتائج التحليل
    """
    recommendations = []
    
    # تحليل MTTR
    mttr_hours = mttr_data.get('mttr_hours', 0)
    if mttr_hours > 4:
        recommendations.append("⏰ MTTR مرتفع: تقليل وقت الإصلاح من خلال تحسين إجراءات الصيانة والتدريب")
    elif mttr_hours < 1:
        recommendations.append("✅ وقت الإصلاح ممتاز: الحفاظ على مستويات الصيانة الحالية")
    
    # تحليل MTBF
    mtbf_hours = mtbf_data.get('mtbf_hours', 0)
    if mtbf_hours < 24:
        recommendations.append("⚠️ MTBF منخفض: زيادة الفترات بين الأعطال من خلال صيانة وقائية محسنة")
    elif mtbf_hours > 168:  # أكثر من أسبوع
        recommendations.append("🎯 أداء موثوقية ممتاز: الاستمرار في ممارسات الصيانة الحالية")
    
    # تحليل التوفر
    availability = oee_data.get('availability', 0)
    if availability < 90:
        recommendations.append("📉 نسبة التوفر منخفضة: تحسين برامج الصيانة وتقليل وقت التوقف")
    elif availability > 98:
        recommendations.append("🏆 نسبة توفر ممتازة: الوصول إلى معايير عالمية")
    
    # تحليل OEE
    oee = oee_data.get('oee', 0)
    if oee < 75:
        recommendations.append("🔧 OEE يحتاج تحسين: التركيز على الجودة والأداء بالإضافة إلى التوفر")
    elif oee > 85:
        recommendations.append("🚀 OEE ممتاز: الأداء يتجاوز معايير الصناعة")
    
    # توصيات إضافية بناءً على البيانات
    failure_count = mtbf_data.get('failure_count', 0)
    if failure_count > 10:
        recommendations.append("🔍 تحليل الأعطال المتكررة: تحديد الأسباب الجذرية وتطبيق حلول دائمة")
    
    if len(recommendations) == 0:
        recommendations.append("📋 البيانات ضمن المستويات المقبولة. الحفاظ على الممارسات الحالية.")
    
    return recommendations

# ===========================================
# واجهات عرض النتائج
# ============================================

def display_reliability_dashboard(report: Dict):
    """
    عرض لوحة تحكم مؤشرات الموثوقية
    """
    st.markdown('<h2 class="main-header">📈 لوحة تحكم مؤشرات الموثوقية</h2>', unsafe_allow_html=True)
    
    # قسم المقاييس الرئيسية
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="mttr-card">', unsafe_allow_html=True)
        st.metric(
            "MTTR", 
            f"{report['mttr_analysis']['mttr_hours']:.2f} ساعة",
            f"{report['mttr_analysis']['mttr_minutes']:.0f} دقيقة"
        )
        st.caption(f"{report['mttr_analysis']['repair_count']} عملية إصلاح")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="mtbf-card">', unsafe_allow_html=True)
        mtbf_days = report['mtbf_analysis']['mtbf_days']
        st.metric(
            "MTBF",
            f"{report['mtbf_analysis']['mtbf_hours']:.1f} ساعة",
            f"{mtbf_days:.1f} يوم" if mtbf_days > 24 else ""
        )
        st.caption(f"{report['mtbf_analysis']['failure_count']} حالة فشل")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="availability-card">', unsafe_allow_html=True)
        availability = report['oee_metrics']['availability']
        st.metric("التوفر", f"{availability:.1f}%")
        st.caption("نسبة وقت التشغيل")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="availability-card" style="background: linear-gradient(135deg, #06D6A0 0%, #048A81 100%);">', unsafe_allow_html=True)
        oee = report['oee_metrics']['oee']
        st.metric("OEE", f"{oee:.1f}%")
        st.caption("الكفاءة الشاملة للمعدات")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # قسم الرسوم البيانية
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        # مخطط MTTR Distribution
        if not report['mttr_analysis']['repair_periods'].empty:
            fig1 = px.histogram(
                report['mttr_analysis']['repair_periods'],
                x='repair_duration_hours',
                title='توزيع أوقات الإصلاح (MTTR)',
                labels={'repair_duration_hours': 'مدة الإصلاح (ساعات)'},
                nbins=20,
                color_discrete_sequence=['#FF6B6B']
            )
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # مخطط MTBF Distribution
        if not report['mtbf_analysis']['failure_intervals'].empty:
            fig2 = px.bar(
                report['mtbf_analysis']['failure_intervals'].head(10),
                x='failure_number',
                y='operation_hours',
                title='الفترات بين الأعطال (MTBF)',
                labels={'operation_hours': 'ساعات التشغيل', 'failure_number': 'رقم العطل'},
                color='operation_hours',
                color_continuous_scale='Viridis'
            )
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
    
    # قسم التحليل التفصيلي
    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["📊 تحليل MTTR", "🔧 تحليل MTBF", "🎯 مؤشرات الأداء", "💡 التوصيات"])
    
    with tab1:
        st.markdown('<h3 class="sub-header">تحليل MTTR التفصيلي</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### إحصائيات MTTR")
            mttr_stats = pd.DataFrame({
                'المعيار': ['MTTR المتوسط', 'أقصر وقت إصلاح', 'أطول وقت إصلاح', 'عدد عمليات الإصلاح', 'إجمالي وقت الإصلاح'],
                'القيمة': [
                    f"{report['mttr_analysis']['mttr_hours']:.2f} ساعة",
                    f"{report['mttr_analysis']['repair_periods']['repair_duration_hours'].min():.2f} ساعة" if not report['mttr_analysis']['repair_periods'].empty else 'N/A',
                    f"{report['mttr_analysis']['repair_periods']['repair_duration_hours'].max():.2f} ساعة" if not report['mttr_analysis']['repair_periods'].empty else 'N/A',
                    f"{report['mttr_analysis']['repair_count']}",
                    f"{report['mttr_analysis']['total_repair_time']}"
                ]
            })
            st.dataframe(mttr_stats, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### سجل عمليات الإصلاح")
            if not report['mttr_analysis']['repair_periods'].empty:
                display_df = report['mttr_analysis']['repair_periods'][[
                    'failure_event', 'failure_time', 'repair_time', 
                    'repair_duration_hours'
                ]].copy()
                display_df.columns = ['الحدث المعطل', 'وقت العطل', 'وقت الإصلاح', 'مدة الإصلاح (ساعة)']
                st.dataframe(display_df.head(10), use_container_width=True)
    
    with tab2:
        st.markdown('<h3 class="sub-header">تحليل MTBF التفصيلي</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### إحصائيات MTBF")
            mtbf_stats = pd.DataFrame({
                'المعيار': ['MTBF المتوسط', 'أقصر فترة تشغيل', 'أطول فترة تشغيل', 'عدد الأعطال', 'إجمالي وقت التشغيل', 'نسبة التوفر'],
                'القيمة': [
                    f"{report['mtbf_analysis']['mtbf_hours']:.2f} ساعة",
                    f"{report['mtbf_analysis']['failure_intervals']['operation_hours'].min():.2f} ساعة" if not report['mtbf_analysis']['failure_intervals'].empty else 'N/A',
                    f"{report['mtbf_analysis']['failure_intervals']['operation_hours'].max():.2f} ساعة" if not report['mtbf_analysis']['failure_intervals'].empty else 'N/A',
                    f"{report['mtbf_analysis']['failure_count']}",
                    f"{report['mtbf_analysis']['total_operation_time']}",
                    f"{report['mtbf_analysis']['availability']:.1f}%"
                ]
            })
            st.dataframe(mtbf_stats, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### توزيع الأعطال")
            if not report['failure_analysis']['top_failures'].empty:
                fig3 = px.pie(
                    values=report['failure_analysis']['top_failures'].values,
                    names=report['failure_analysis']['top_failures'].index,
                    title='أكثر أنواع الأعطال تكراراً',
                    hole=0.4
                )
                fig3.update_layout(height=400)
                st.plotly_chart(fig3, use_container_width=True)
    
    with tab3:
        st.markdown('<h3 class="sub-header">مؤشرات الأداء الشاملة</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # مخطط OEE Components
            components = pd.DataFrame({
                'المكون': ['التوفر', 'الأداء', 'الجودة', 'OEE الكلي'],
                'النسبة': [
                    report['oee_metrics']['availability'],
                    report['oee_metrics']['performance_rate'],
                    report['oee_metrics']['quality_rate'],
                    report['oee_metrics']['oee']
                ]
            })
            
            fig4 = px.bar(
                components,
                x='المكون',
                y='النسبة',
                title='مكونات مؤشر OEE',
                color='النسبة',
                color_continuous_scale='RdYlGn',
                text='النسبة'
            )
            fig4.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig4.update_layout(height=400)
            st.plotly_chart(fig4, use_container_width=True)
        
        with col2:
            # مؤشرات الأداء
            performance_df = pd.DataFrame({
                'المؤشر': [
                    'نسبة التوفر',
                    'نسبة الأداء', 
                    'نسبة الجودة',
                    'OEE الإجمالي',
                    'تكرار الأعطال/يوم',
                    'إجمالي وقت التشغيل',
                    'إجمالي وقت التوقف'
                ],
                'القيمة': [
                    f"{report['oee_metrics']['availability']:.1f}%",
                    f"{report['oee_metrics']['performance_rate']:.1f}%",
                    f"{report['oee_metrics']['quality_rate']:.1f}%",
                    f"{report['oee_metrics']['oee']:.1f}%",
                    f"{report['oee_metrics']['failure_frequency_per_day']:.2f}",
                    f"{report['oee_metrics']['total_uptime_hours']:.1f} ساعة",
                    f"{report['oee_metrics']['total_downtime_hours']:.1f} ساعة"
                ]
            })
            st.dataframe(performance_df, use_container_width=True, hide_index=True)
    
    with tab4:
        st.markdown('<h3 class="sub-header">التوصيات والتحسينات</h3>', unsafe_allow_html=True)
        
        st.markdown("### 📋 ملخص الأداء")
        summary_data = report['summary']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### نظرة عامة")
            summary_df = pd.DataFrame({
                'المعيار': ['فترة التحليل', 'إجمالي الأحداث', 'أحداث الفشل', 'عمليات الإصلاح', 'بداية التسجيل', 'نهاية التسجيل'],
                'القيمة': [
                    str(summary_data['analysis_period']),
                    str(summary_data['total_events']),
                    str(summary_data['total_failures']),
                    str(summary_data['total_repairs']),
                    summary_data['start_date'].strftime('%Y-%m-%d %H:%M'),
                    summary_data['end_date'].strftime('%Y-%m-%d %H:%M')
                ]
            })
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### تحليل الاتجاه")
            trend = report['failure_analysis']['failure_trend']
            st.metric("اتجاه الأعطال", trend['trend'], f"{trend['change_percentage']:.1f}%")
            
            if report['failure_analysis']['critical_events_count'] > 0:
                st.warning(f"⚠️ هناك {report['failure_analysis']['critical_events_count']} حدث حرج يتطلب اهتماماً عاجلاً")
        
        st.markdown("### 💡 التوصيات")
        recommendations = report['recommendations']
        
        for i, rec in enumerate(recommendations, 1):
            st.markdown(f"""
            <div class="{'critical-event' if 'منخفض' in rec or 'مرتفع' in rec or 'تحتاج' in rec else 'normal-event'}" style="margin: 10px 0; padding: 15px;">
                <strong>{i}. {rec}</strong>
            </div>
            """, unsafe_allow_html=True)
        
        # تصدير التقرير
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 تصدير تقرير MTTR/MTBF", use_container_width=True):
                # تحويل التقرير إلى CSV
                mttr_df = report['mttr_analysis']['repair_periods']
                mtbf_df = report['mtbf_analysis']['failure_intervals']
                
                if not mttr_df.empty:
                    csv1 = mttr_df.to_csv(index=False)
                    st.download_button(
                        label="تحميل بيانات MTTR",
                        data=csv1,
                        file_name="mttr_analysis.csv",
                        mime="text/csv"
                    )
        
        with col2:
            if not mtbf_df.empty:
                csv2 = mtbf_df.to_csv(index=False)
                st.download_button(
                    label="تحميل بيانات MTBF",
                    data=csv2,
                    file_name="mtbf_analysis.csv",
                    mime="text/csv"
                )
        
        with col3:
            # تقرير مختصر
            summary_report = f"""
            تقرير موثوقية المعدات
            =====================
            
            فترة التحليل: {summary_data['start_date']} إلى {summary_data['end_date']}
            إجمالي وقت التحليل: {summary_data['analysis_period']}
            
            مؤشرات الأداء:
            -------------
            MTTR: {report['mttr_analysis']['mttr_hours']:.2f} ساعة
            MTBF: {report['mtbf_analysis']['mtbf_hours']:.2f} ساعة
            نسبة التوفر: {report['oee_metrics']['availability']:.1f}%
            OEE الإجمالي: {report['oee_metrics']['oee']:.1f}%
            
            الإحصائيات:
            ---------
            إجمالي الأحداث: {summary_data['total_events']}
            أحداث الفشل: {summary_data['total_failures']}
            عمليات الإصلاح: {summary_data['total_repairs']}
            
            التوصيات:
            --------
            {chr(10).join(recommendations)}
            """
            
            st.download_button(
                label="📄 تقرير نصي",
                data=summary_report,
                file_name="reliability_report.txt",
                mime="text/plain"
            )

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
            date = parts[0].strip()
            time = parts[1].strip()
            event = parts[2].strip()
            details = parts[3].strip()
            
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

# ===========================================
# الوظيفة الرئيسية للتطبيق
# ===========================================

def main():
    """
    الوظيفة الرئيسية للتطبيق
    """
    # الشريط الجانبي
    with st.sidebar:
        st.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=100)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("### ⚙️ إعدادات التحليل")
        
        # خيارات التحليل
        analysis_type = st.radio(
            "نوع التحليل:",
            ["تحليل MTTR/MTBF", "تحليل شامل", "تحليل مخصص"],
            index=0
        )
        
        upload_option = st.radio(
            "مصدر البيانات:",
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
        
        # إعدادات متقدمة
        st.markdown("---")
        with st.expander("⚙️ الإعدادات المتقدمة"):
            mttr_threshold = st.number_input(
                "حد MTTR المستهدف (ساعات):",
                min_value=0.1,
                max_value=24.0,
                value=2.0,
                step=0.1
            )
            
            mtbf_threshold = st.number_input(
                "حد MTBF المستهدف (ساعات):",
                min_value=1.0,
                max_value=720.0,
                value=168.0,  # أسبوع
                step=1.0
            )
            
            availability_target = st.slider(
                "هدف نسبة التوفر %:",
                min_value=80,
                max_value=100,
                value=95
            )
        
        # معلومات
        st.markdown("---")
        st.markdown("### 📊 مؤشرات MTTR/MTBF")
        st.markdown("""
        - **MTTR**: متوسط وقت الإصلاح (كلما قل كان أفضل)
        - **MTBF**: متوسط الوقت بين الأعطال (كلما زاد كان أفضل)
        - **التوفر**: نسبة وقت تشغيل المعدة
        - **OEE**: الكفاءة الشاملة للمعدات
        """)
    
    # المحتوى الرئيسي
    if file_content:
        try:
            with st.spinner("جاري معالجة البيانات وتحليل الموثوقية..."):
                df = parse_log_file(file_content)
                
                if df.empty:
                    st.error("لم يتم العثور على بيانات صالحة في الملف")
                    return
                
                # إنشاء تقرير الموثوقية
                report = create_reliability_report(df)
                
                # عرض لوحة تحكم الموثوقية
                display_reliability_dashboard(report)
                
                # قسم التحليل الإضافي
                st.markdown("---")
                st.markdown('<h2 class="sub-header">🔍 تحليل إضافي</h2>', unsafe_allow_html=True)
                
                # تحليل المقارنة مع الأهداف
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    mttr_status = "✅ جيد" if report['mttr_analysis']['mttr_hours'] <= mttr_threshold else "⚠️ يحتاج تحسين"
                    st.metric("MTTR vs Target", 
                             f"{report['mttr_analysis']['mttr_hours']:.2f}h", 
                             mttr_status,
                             delta_color="inverse")
                
                with col2:
                    mtbf_status = "✅ جيد" if report['mtbf_analysis']['mtbf_hours'] >= mtbf_threshold else "⚠️ يحتاج تحسين"
                    st.metric("MTBF vs Target", 
                             f"{report['mtbf_analysis']['mtbf_hours']:.1f}h", 
                             mtbf_status)
                
                with col3:
                    availability_status = "✅ جيد" if report['oee_metrics']['availability'] >= availability_target else "⚠️ يحتاج تحسين"
                    st.metric("التوفر vs Target", 
                             f"{report['oee_metrics']['availability']:.1f}%", 
                             availability_status,
                             delta_color="inverse")
                
                # تحليل تأثير الأعطال
                st.markdown("### 📉 تحليل تأثير الأعطال")
                
                if report['failure_analysis']['critical_events_count'] > 0:
                    failure_events = identify_failure_events(df)
                    critical_failures = failure_events[failure_events['Event'].str.contains('E0', na=False)]
                    
                    if not critical_failures.empty:
                        st.dataframe(
                            critical_failures[['Date', 'Time', 'Event', 'Details']],
                            use_container_width=True,
                            height=300
                        )
                
                # محاكاة التحسين
                st.markdown("### 🎯 محاكاة التحسين")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    improvement_mttr = st.slider(
                        "تحسين MTTR بنسبة %:",
                        min_value=0,
                        max_value=50,
                        value=10,
                        step=5
                    )
                    
                    new_mttr = report['mttr_analysis']['mttr_hours'] * (1 - improvement_mttr/100)
                    st.metric("MTTR بعد التحسين", f"{new_mttr:.2f} ساعة")
                
                with col2:
                    improvement_mtbf = st.slider(
                        "تحسين MTBF بنسبة %:",
                        min_value=0,
                        max_value=100,
                        value=20,
                        step=5
                    )
                    
                    new_mtbf = report['mtbf_analysis']['mtbf_hours'] * (1 + improvement_mtbf/100)
                    st.metric("MTBF بعد التحسين", f"{new_mtbf:.1f} ساعة")
        
        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة البيانات: {str(e)}")
            st.exception(e)
    
    else:
        # صفحة الترحيب
        st.markdown('<h1 class="main-header">⚙️ نظام تحليل مؤشرات الموثوقية</h1>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            ## 📊 تحليل متقدم لـ MTTR و MTBF
            
            هذا النظام يحسب مؤشرات الموثوقية الرئيسية للمعدات الصناعية:
            
            ### مؤشرات يتم حسابها:
            
            1. **MTTR (Mean Time To Repair)**
               - متوسط وقت إصلاح الأعطال
               - كلما قل كان أفضل
            
            2. **MTBF (Mean Time Between Failures)**
               - متوسط الوقت بين الأعطال
               - كلما زاد كان أفضل
            
            3. **نسبة التوفر (Availability)**
               - نسبة وقت تشغيل المعدة
               - الهدف: فوق 95%
            
            4. **OEE (Overall Equipment Effectiveness)**
               - الكفاءة الشاملة للمعدات
               - مزيج من التوفر، الأداء، والجودة
            
            ### كيفية الاستخدام:
            1. رفع ملف سجلات الماكينة
            2. اختيار نوع التحليل
            3. استعراض النتائج والتوصيات
            4. تصدير التقارير
            
            ### تنسيق الملف المدعوم:
            - ملفات نصية (.txt, .log)
            - تنسيق التاريخ: DD.MM.YYYY
            - تنسيق الوقت: HH:MM:SS
            - فواصل: Tab
            """)
        
        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 📈 مؤشرات مرجعية")
            
            st.metric("MTTR ممتاز", "< 1 ساعة")
            st.metric("MTBF ممتاز", "> 168 ساعة")
            st.metric("توفر ممتاز", "> 98%")
            st.metric("OEE ممتاز", "> 85%")
            
            st.markdown("### 📋 مثال بيانات")
            st.code("""23.12.2024\t19:06:26\tStarting speed\tON
23.12.2024\t19:11:04\tThick spots\tW0547
23.12.2024\t19:13:18\tDFK deactivated\tW0534""")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # أمثلة تقارير
        st.markdown("---")
        st.markdown("## 📄 نماذج تقارير")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="mttr-card">', unsafe_allow_html=True)
            st.markdown("### تقرير MTTR")
            st.markdown("""
            - متوسط وقت الإصلاح: 1.8 ساعة
            - عدد عمليات الإصلاح: 12
            - أطول إصلاح: 4.2 ساعة
            - أقصر إصلاح: 0.5 ساعة
            """)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="mtbf-card">', unsafe_allow_html=True)
            st.markdown("### تقرير MTBF")
            st.markdown("""
            - متوسط الوقت بين الأعطال: 72 ساعة
            - عدد الأعطال: 8
            - أطول فترة تشغيل: 240 ساعة
            - أقصر فترة تشغيل: 12 ساعة
            """)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="availability-card">', unsafe_allow_html=True)
            st.markdown("### تقرير الأداء")
            st.markdown("""
            - نسبة التوفر: 96.2%
            - نسبة الأداء: 94.5%
            - نسبة الجودة: 97.8%
            - OEE الإجمالي: 89.1%
            """)
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
