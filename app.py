import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

# ==================== تحميل وتحليل البيانات ====================
def parse_log_file(content):
    lines = content.split('\n')
    data = []
    current_date = None
    
    for line in lines:
        if line.startswith("===") or not line.strip():
            continue
        
        parts = re.split(r'\t+', line.strip())
        if len(parts) < 3:
            continue
        
        # إذا كان السطر يحتوي على تاريخ جديد
        if re.match(r'\d{2}\.\d{2}\.\d{4}', parts[0]):
            current_date = parts[0]
            time = parts[1]
            event = parts[2]
            code = parts[3] if len(parts) > 3 else ""
        else:
            time = parts[0]
            event = parts[1]
            code = parts[2] if len(parts) > 2 else ""
        
        if current_date:
            datetime_str = f"{current_date} {time}"
            try:
                dt = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M:%S")
            except:
                continue
            
            # استخراج نوع العطل (W/E/T) ورقمه
            fault_type = ""
            fault_code = ""
            if code:
                match = re.match(r'([WET])(\d+)', code)
                if match:
                    fault_type = match.group(1)
                    fault_code = match.group(2)
            
            data.append({
                'datetime': dt,
                'date': dt.date(),
                'time': dt.time(),
                'event': event,
                'code': code,
                'fault_type': fault_type,
                'fault_code': fault_code
            })
    
    return pd.DataFrame(data)

# ==================== واجهة Streamlit ====================
st.set_page_config(page_title="محلل أعطال الماكينة", layout="wide")
st.title("🛠️ محلل أعطال الماكينة - من أي مكان")
st.markdown("تحميل ملف السجلات وتحليل الأعطال بسهولة")

# ==================== رفع الملف ====================
uploaded_file = st.file_uploader("📤 رفع ملف السجلات (Logbook_*.txt)", type=['txt'])

if uploaded_file is not None:
    content = uploaded_file.read().decode('utf-8')
    df = parse_log_file(content)
    
    if df.empty:
        st.error("لم يتم العثور على بيانات صالحة في الملف")
    else:
        st.success(f"✅ تم تحميل {len(df)} حدث بنجاح")
        
        # ==================== معلومات عامة ====================
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("الفترة الزمنية", 
                     f"{df['datetime'].min().date()} إلى {df['datetime'].max().date()}")
        with col2:
            st.metric("عدد الأحداث", len(df))
        with col3:
            faults = df[df['fault_type'].isin(['W', 'E', 'T'])]
            st.metric("عدد الأعطال", len(faults))
        with col4:
            st.metric("عدد الأيام", df['date'].nunique())
        
        # ==================== تحليل الأعطال ====================
        st.header("📊 تحليل الأعطال")
        
        # اختيار نوع العطل
        fault_types = st.multiselect(
            "اختر نوع العطل",
            options=['W (تحذير)', 'E (خطأ)', 'T (مهمة)', 'كل الأنواع'],
            default=['كل الأنواع']
        )
        
        # تحويل الاختيار
        selected_types = []
        if 'كل الأنواع' in fault_types or not fault_types:
            selected_types = ['W', 'E', 'T']
        else:
            type_map = {'W (تحذير)': 'W', 'E (خطأ)': 'E', 'T (مهمة)': 'T'}
            selected_types = [type_map[t] for t in fault_types]
        
        # تصفية البيانات
        filtered_df = df[df['fault_type'].isin(selected_types)] if selected_types else df
        
        # ==================== إحصائيات الأعطال ====================
        if not filtered_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🔝 أكثر الأعطال تكراراً")
                top_faults = filtered_df['code'].value_counts().head(10)
                fig1 = px.bar(
                    x=top_faults.values,
                    y=top_faults.index,
                    orientation='h',
                    labels={'x': 'عدد التكرارات', 'y': 'رمز العطل'},
                    title="أكثر 10 أعطال تكراراً"
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                st.subheader("📈 توزيع الأعطال خلال اليوم")
                filtered_df['hour'] = filtered_df['datetime'].dt.hour
                hourly_counts = filtered_df['hour'].value_counts().sort_index()
                fig2 = px.line(
                    x=hourly_counts.index,
                    y=hourly_counts.values,
                    markers=True,
                    labels={'x': 'ساعة اليوم', 'y': 'عدد الأحداث'},
                    title="الأعطال حسب الساعة"
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # ==================== تحليل الوقت بين الأعطال ====================
            st.subheader("⏱️ تحليل الوقت بين الأعطال المتشابهة")
            
            selected_fault = st.selectbox(
                "اختر عطلاً لتحليل الفترة الزمنية بين تكراراته",
                options=sorted(filtered_df['code'].unique())
            )
            
            if selected_fault:
                fault_events = df[df['code'] == selected_fault].sort_values('datetime')
                
                if len(fault_events) > 1:
                    fault_events['time_diff'] = fault_events['datetime'].diff()
                    fault_events['time_diff_min'] = fault_events['time_diff'].dt.total_seconds() / 60
                    
                    st.write(f"**العطل:** {selected_fault}")
                    st.write(f"**عدد التكرارات:** {len(fault_events)}")
                    st.write(f"**المتوسط الزمني بين التكرارات:** {fault_events['time_diff_min'].mean():.1f} دقيقة")
                    st.write(f"**أقصر فترة:** {fault_events['time_diff_min'].min():.1f} دقيقة")
                    st.write(f"**أطول فترة:** {fault_events['time_diff_min'].max():.1f} دقيقة")
                    
                    # رسم بياني للفترات الزمنية
                    fig3 = px.line(
                        x=fault_events['datetime'].iloc[1:],
                        y=fault_events['time_diff_min'].iloc[1:],
                        markers=True,
                        labels={'x': 'تاريخ العطل', 'y': 'الدقائق منذ العطل السابق'},
                        title=f"الفترات الزمنية بين تكرارات {selected_fault}"
                    )
                    st.plotly_chart(fig3, use_container_width=True)
                    
                    # ==================== تنبيهات ====================
                    st.subheader("🚨 نظام التنبيهات")
                    
                    threshold_min = st.number_input(
                        "حدد الحد الأدنى للدقائق بين التكرارات للتنبيه",
                        min_value=1,
                        value=30,
                        help="سيتم التنبيه إذا حدث العطل مرتين خلال هذه الدقائق"
                    )
                    
                    alert_events = fault_events[fault_events['time_diff_min'] < threshold_min]
                    if len(alert_events) > 0:
                        st.warning(f"⚠️ **تنبيه:** العطل {selected_fault} تكرر {len(alert_events)} مرة خلال أقل من {threshold_min} دقيقة")
                        st.dataframe(alert_events[['datetime', 'event', 'code']])
                    else:
                        st.success(f"✅ لا توجد تكرارات سريعة للعطل {selected_fault}")
            
            # ==================== جدول تفصيلي ====================
            st.subheader("📋 جدول الأحداث التفصيلي")
            
            # خيارات التصفية
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("من تاريخ", value=df['date'].min())
            with col2:
                end_date = st.date_input("إلى تاريخ", value=df['date'].max())
            
            filtered_by_date = filtered_df[
                (filtered_df['date'] >= start_date) & 
                (filtered_df['date'] <= end_date)
            ]
            
            st.dataframe(
                filtered_by_date.sort_values('datetime', ascending=False)[
                    ['datetime', 'event', 'code', 'fault_type']
                ].head(100),
                use_container_width=True
            )
            
            # ==================== تصدير النتائج ====================
            st.subheader("💾 تصدير النتائج")
            
            if st.button("تحميل التقرير كملف Excel"):
                with pd.ExcelWriter('fault_analysis_report.xlsx') as writer:
                    df.to_excel(writer, sheet_name='كل البيانات', index=False)
                    filtered_by_date.to_excel(writer, sheet_name='البيانات المصفاة', index=False)
                    
                    # إحصائيات
                    stats_df = pd.DataFrame({
                        'المؤشر': ['عدد الأحداث', 'عدد الأعطال', 'الفترة الزمنية', 'عدد الأيام'],
                        'القيمة': [
                            len(df),
                            len(faults),
                            f"{df['datetime'].min()} إلى {df['datetime'].max()}",
                            df['date'].nunique()
                        ]
                    })
                    stats_df.to_excel(writer, sheet_name='الإحصائيات', index=False)
                
                with open('fault_analysis_report.xlsx', 'rb') as f:
                    st.download_button(
                        label="📥 انقر لتحميل ملف Excel",
                        data=f,
                        file_name="fault_analysis_report.xlsx",
                        mime="application/vnd.ms-excel"
                    )
        else:
            st.info("⚠️ لا توجد أعطال مطابقة للاختيار")
else:
    st.info("👆 يرجى رفع ملف سجلات الماكينة لبدء التحليل")

# ==================== تعليمات التشغيل ====================
with st.expander("📖 تعليمات الاستخدام"):
    st.markdown("""
    ### كيفية استخدام النظام:
    1. **رفع الملف**: انقر على زر رفع الملف واختر ملف السجلات (`Logbook_*.txt`)
    2. **تحليل الأعطال**: النظام سيقوم تلقائياً بتحليل البيانات وعرض الإحصائيات
    3. **التصفية**: يمكنك تصفية الأعطال حسب النوع (W/E/T) أو الفترة الزمنية
    4. **تحليل التكرار**: اختر عطلاً معيناً لتحليل الفترة الزمنية بين تكراراته
    5. **التنبيهات**: حدد الحد الزمني للتنبيه عند تكرار العطل بسرعة
    6. **تحميل التقرير**: يمكنك تحميل جميع النتائج كملف Excel

    ### رموز الأعطال:
    - **W**: تحذير (Warning)
    - **E**: خطأ (Error)
    - **T**: مهمة/إجراء (Task)
    
    ### المتطلبات:
    - Python 3.8+
    - تثبيت المكتبات: `pip install streamlit pandas plotly`
    - تشغيل التطبيق: `streamlit run fault_analyzer.py`
    """)

# ==================== تذييل الصفحة ====================
st.markdown("---")
st.markdown("🛠️ **محلل أعطال الماكينة** | تم التطوير باستخدام Streamlit | يمكن الوصول من أي مكان")
