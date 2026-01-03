import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import io

# إعداد واجهة Streamlit
st.set_page_config(page_title="نظام تحليل سجلات الماكينة", layout="wide")
st.title("🏭 نظام تحليل سجلات الماكينة الشامل")
st.markdown("### تحليل مفصل للإحصائيات والوقت بين الأحداث")

# متغيرات عامة
df = None
filtered_df = None
mttr_results = None
mtbf_results = None

# دالة لتحميل البيانات
def load_data(uploaded_file):
    lines = uploaded_file.read().decode('utf-8').splitlines()
    
    data = []
    for line in lines:
        if line.startswith("=") or line.strip() == "":
            continue
        parts = line.split("\t")
        while len(parts) < 4:
            parts.append("")
        data.append([part.strip() for part in parts])
    
    df = pd.DataFrame(data, columns=["Date", "Time", "Event", "Details"])
    
    # تنظيف البيانات
    df = df[(df['Date'].str.strip() != '') & (df['Time'].str.strip() != '')]
    df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%d.%m.%Y %H:%M:%S')
    
    return df

# دالة لحساب الوقت بين حدثين
def calculate_time_between_events(df, event1_list, event2, start_date, end_date):
    """
    حساب الوقت بين قائمة أحداث (event1_list) وحدث محدد (event2)
    """
    # تصفية البيانات حسب الفترة الزمنية
    mask = (df['DateTime'] >= start_date) & (df['DateTime'] <= end_date)
    filtered = df[mask].copy().sort_values('DateTime')
    
    results = []
    total_time = timedelta()
    
    for event1 in event1_list:
        # الحصول على أحداث event1
        event1_occurrences = filtered[filtered['Event'] == event1]
        
        for _, row in event1_occurrences.iterrows():
            event1_time = row['DateTime']
            
            # البحث عن أول event2 بعد event1
            next_event2 = filtered[
                (filtered['Event'] == event2) & 
                (filtered['DateTime'] > event1_time)
            ]
            
            if not next_event2.empty:
                event2_time = next_event2.iloc[0]['DateTime']
                time_diff = event2_time - event1_time
                
                results.append({
                    'الحدث الأول': event1,
                    'الوقت': event1_time,
                    'الحدث الثاني': event2,
                    'الوقت الثاني': event2_time,
                    'المدة': time_diff,
                    'المدة بالدقائق': time_diff.total_seconds() / 60
                })
                
                total_time += time_diff
    
    results_df = pd.DataFrame(results) if results else pd.DataFrame()
    
    return results_df, total_time

# دالة لحساب MTTR
def calculate_mttr(df, failure_events, recovery_event, start_date, end_date):
    """
    حساب متوسط وقت الإصلاح (MTTR) للأعطال
    """
    mttr_data, total_downtime = calculate_time_between_events(df, failure_events, recovery_event, start_date, end_date)
    
    if mttr_data.empty:
        return mttr_data, total_downtime, pd.DataFrame()
    
    # حساب MTTR لكل نوع عطل
    mttr_by_event = mttr_data.groupby('الحدث الأول').agg({
        'المدة بالدقائق': ['count', 'mean', 'sum']
    }).round(2)
    
    mttr_by_event.columns = ['عدد المرات', 'متوسط MTTR (دقيقة)', 'إجمالي الوقت (دقيقة)']
    mttr_by_event = mttr_by_event.reset_index()
    
    # حساب MTTR العام
    total_failures = mttr_data.shape[0]
    overall_mttr = mttr_data['المدة بالدقائق'].mean() if total_failures > 0 else 0
    
    summary = pd.DataFrame({
        'المؤشر': ['إجمالي الأعطال', 'إجمالي وقت التوقف', 'متوسط MTTR', 
                   'أطول توقف', 'أقصر توقف'],
        'القيمة': [
            f"{total_failures}",
            f"{total_downtime.total_seconds() / 60:.1f} دقيقة",
            f"{overall_mttr:.1f} دقيقة",
            f"{mttr_data['المدة بالدقائق'].max():.1f} دقيقة",
            f"{mttr_data['المدة بالدقائق'].min():.1f} دقيقة"
        ]
    })
    
    return mttr_data, total_downtime, summary

# دالة لحساب MTBF
def calculate_mtbf(df, failure_event, start_date, end_date):
    """
    حساب متوسط الوقت بين أعطال من نفس النوع
    """
    # تصفية البيانات حسب الفترة الزمنية ونوع العطل
    mask = (df['DateTime'] >= start_date) & (df['DateTime'] <= end_date) & (df['Event'] == failure_event)
    filtered = df[mask].copy().sort_values('DateTime')
    
    if len(filtered) < 2:
        return pd.DataFrame(), pd.DataFrame()
    
    results = []
    total_time_between = timedelta()
    
    # حساب الوقت بين كل عطلين متتاليين من نفس النوع
    for i in range(1, len(filtered)):
        time1 = filtered.iloc[i-1]['DateTime']
        time2 = filtered.iloc[i]['DateTime']
        time_between = time2 - time1
        
        results.append({
            'نوع العطل': failure_event,
            'العطل الأول': time1,
            'العطل التالي': time2,
            'الوقت بين العطلين': time_between,
            'المدة بالساعات': time_between.total_seconds() / 3600
        })
        
        total_time_between += time_between
    
    results_df = pd.DataFrame(results)
    
    # حساب MTBF
    total_intervals = len(results_df)
    overall_mtbf = total_time_between.total_seconds() / (3600 * total_intervals) if total_intervals > 0 else 0
    
    summary = pd.DataFrame({
        'المؤشر': ['عدد الفترات', 'إجمالي الوقت بين الأعطال', 'متوسط MTBF', 
                   'أطول فترة بين أعطال', 'أقصر فترة بين أعطال'],
        'القيمة': [
            f"{total_intervals}",
            f"{total_time_between.total_seconds() / 3600:.1f} ساعة",
            f"{overall_mtbf:.1f} ساعة",
            f"{results_df['المدة بالساعات'].max():.1f} ساعة",
            f"{results_df['المدة بالساعات'].min():.1f} ساعة"
        ]
    })
    
    return results_df, summary

# دالة لحساب الإحصائيات العامة
def calculate_general_stats(df, start_date, end_date):
    """
    حساب الإحصائيات العامة للبيانات
    """
    mask = (df['DateTime'] >= start_date) & (df['DateTime'] <= end_date)
    filtered = df[mask].copy()
    
    stats = {
        'إجمالي الأحداث': filtered.shape[0],
        'عدد أنواع الأحداث': filtered['Event'].nunique(),
        'الفترة الزمنية': f"{start_date:%Y-%m-%d} إلى {end_date:%Y-%m-%d}",
        'المدة الزمنية': str(end_date - start_date).split('.')[0],
        'أول حدث': filtered['DateTime'].min(),
        'آخر حدث': filtered['DateTime'].max()
    }
    
    return pd.DataFrame(list(stats.items()), columns=['المؤشر', 'القيمة'])

# -------------------------------------------------------------------------
# الواجهة الرئيسية
# -------------------------------------------------------------------------

# القائمة المنسدلة الرئيسية
analysis_options = [
    "اختر نوع التحليل...",
    "معاينة البيانات",
    "احصائيات عامة",
    "أنواع الأحداث",
    "تكرارات الأحداث",
    "MTBF (متوسط الوقت بين أعطال)",
    "MTTR (متوسط وقت الإصلاح)",
    "حساب الوقت بين الأحداث"
]

selected_analysis = st.selectbox("📊 اختر نوع التحليل:", analysis_options)

# قسم رفع الملف
st.subheader("📁 رفع ملف السجل")
uploaded_file = st.file_uploader("اختر ملف السجل (Logbook_YYYYMMDD.txt)", type=["txt"])

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    # قسم اختيار الفترة الزمنية
    st.subheader("📅 تحديد الفترة الزمنية")
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("من تاريخ", df['DateTime'].min().date())
    with col2:
        end_date = st.date_input("إلى تاريخ", df['DateTime'].max().date())
    
    # تحويل التواريخ
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    # تصفية البيانات حسب الفترة
    filtered_df = df[(df['DateTime'] >= start_dt) & (df['DateTime'] <= end_dt)].copy()
    
    # -----------------------------------------------------------------
    # 1. معاينة البيانات
    # -----------------------------------------------------------------
    if selected_analysis == "معاينة البيانات":
        st.subheader("📄 معاينة البيانات الأصلية")
        
        # خيارات العرض
        col1, col2 = st.columns(2)
        with col1:
            rows_to_show = st.number_input("عدد الصفوف المعروضة", min_value=10, max_value=1000, value=50)
        with col2:
            sort_by = st.selectbox("ترتيب حسب", ['الأحدث', 'الأقدم'])
        
        # عرض البيانات
        display_df = filtered_df.copy()
        if sort_by == 'الأحدث':
            display_df = display_df.sort_values('DateTime', ascending=False)
        else:
            display_df = display_df.sort_values('DateTime', ascending=True)
        
        st.dataframe(display_df.head(rows_to_show), use_container_width=True)
        
        # إحصائيات سريعة
        st.subheader("📊 إحصائيات سريعة")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("إجمالي الصفوف", filtered_df.shape[0])
        with col2:
            st.metric("عدد أنواع الأحداث", filtered_df['Event'].nunique())
        with col3:
            st.metric("المدة الزمنية", f"{(end_dt - start_dt).days} يوم")
    
    # -----------------------------------------------------------------
    # 2. احصائيات عامة
    # -----------------------------------------------------------------
    elif selected_analysis == "احصائيات عامة":
        st.subheader("📈 الإحصائيات العامة")
        
        stats_df = calculate_general_stats(df, start_dt, end_dt)
        st.dataframe(stats_df, use_container_width=True)
        
        # مخطط تفصيلي للأحداث
        st.subheader("📋 تفصيل الأحداث حسب الوقت")
        
        # إضافة أعمدة للتاريخ والوقت
        filtered_df['Date_Only'] = filtered_df['DateTime'].dt.date
        filtered_df['Hour'] = filtered_df['DateTime'].dt.hour
        
        # الأحداث حسب اليوم
        daily_counts = filtered_df.groupby('Date_Only').size().reset_index()
        daily_counts.columns = ['اليوم', 'عدد الأحداث']
        
        # الأحداث حسب الساعة
        hourly_counts = filtered_df.groupby('Hour').size().reset_index()
        hourly_counts.columns = ['الساعة', 'عدد الأحداث']
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**الأحداث حسب اليوم:**")
            st.dataframe(daily_counts, use_container_width=True)
        with col2:
            st.write("**الأحداث حسب الساعة:**")
            st.dataframe(hourly_counts, use_container_width=True)
    
    # -----------------------------------------------------------------
    # 3. أنواع الأحداث
    # -----------------------------------------------------------------
    elif selected_analysis == "أنواع الأحداث":
        st.subheader("🔍 أنواع الأحداث المختلفة")
        
        # الحصول على جميع أنواع الأحداث
        all_events = sorted(filtered_df['Event'].unique().tolist())
        
        # عرض عدد الأحداث لكل نوع
        event_counts = filtered_df['Event'].value_counts().reset_index()
        event_counts.columns = ['نوع الحدث', 'عدد التكرارات']
        
        st.dataframe(event_counts, use_container_width=True)
        
        # اختيار حدث لعرض تفاصيله
        st.subheader("🔎 تفاصيل حدث معين")
        selected_event = st.selectbox("اختر الحدث لعرض تفاصيله:", all_events)
        
        if selected_event:
            event_details = filtered_df[filtered_df['Event'] == selected_event]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("عدد مرات الحدوث", event_details.shape[0])
            with col2:
                st.metric("أول مرة", event_details['DateTime'].min().strftime('%Y-%m-%d %H:%M'))
            with col3:
                st.metric("آخر مرة", event_details['DateTime'].max().strftime('%Y-%m-%d %H:%M'))
            
            # عرض 10 أحداث عشوائية
            st.write(f"**عرض 10 أحداث عشوائية من {selected_event}:**")
            st.dataframe(event_details.sample(min(10, len(event_details))), use_container_width=True)
    
    # -----------------------------------------------------------------
    # 4. تكرارات الأحداث
    # -----------------------------------------------------------------
    elif selected_analysis == "تكرارات الأحداث":
        st.subheader("🔄 تحليل تكرارات الأحداث")
        
        # حساب التكرارات
        frequency_df = filtered_df['Event'].value_counts().reset_index()
        frequency_df.columns = ['الحدث', 'عدد التكرارات', 'النسبة %']
        
        # حساب النسبة المئوية
        total_events = frequency_df['عدد التكرارات'].sum()
        frequency_df['النسبة %'] = (frequency_df['عدد التكرارات'] / total_events * 100).round(2)
        
        st.dataframe(frequency_df, use_container_width=True)
        
        # تحليل التكرار اليومي
        st.subheader("📅 التكرار اليومي للأحداث")
        
        # اختيار حدث لتحليل تكراره اليومي
        all_events = sorted(filtered_df['Event'].unique().tolist())
        selected_event_freq = st.selectbox("اختر الحدث لتحليل تكراره اليومي:", all_events)
        
        if selected_event_freq:
            # إضافة عمود اليوم
            filtered_df['Day'] = filtered_df['DateTime'].dt.date
            
            # حساب التكرار اليومي
            daily_freq = filtered_df[filtered_df['Event'] == selected_event_freq].groupby('Day').size().reset_index()
            daily_freq.columns = ['اليوم', 'عدد المرات']
            
            if not daily_freq.empty:
                # إحصائيات التكرار اليومي
                col1, col2, col3 = st.columns(3)
                with col1:
                    avg_daily = daily_freq['عدد المرات'].mean()
                    st.metric("متوسط التكرار اليومي", f"{avg_daily:.1f}")
                with col2:
                    max_daily = daily_freq['عدد المرات'].max()
                    st.metric("أعلى تكرار يومي", max_daily)
                with col3:
                    days_with_event = len(daily_freq)
                    total_days = (end_date - start_date).days + 1
                    st.metric("أيام الحدوث", f"{days_with_event} من {total_days}")
                
                st.write("**التكرار اليومي التفصيلي:**")
                st.dataframe(daily_freq, use_container_width=True)
            else:
                st.warning(f"الحدث '{selected_event_freq}' لم يحدث في الفترة المحددة")
    
    # -----------------------------------------------------------------
    # 5. MTBF (متوسط الوقت بين أعطال)
    # -----------------------------------------------------------------
    elif selected_analysis == "MTBF (متوسط الوقت بين أعطال)":
        st.subheader("🔄 حساب MTBF (Mean Time Between Failures)")
        
        # اختيار نوع العطل لتحليل MTBF
        all_events = sorted(filtered_df['Event'].unique().tolist())
        selected_mtbf_event = st.selectbox("اختر نوع العطل لحساب MTBF:", all_events)
        
        if selected_mtbf_event:
            mtbf_data, mtbf_summary = calculate_mtbf(df, selected_mtbf_event, start_dt, end_dt)
            
            if not mtbf_data.empty:
                st.write(f"**MTBF للعطل: {selected_mtbf_event}**")
                
                # عرض البيانات التفصيلية
                st.write("**البيانات التفصيلية:**")
                st.dataframe(mtbf_data, use_container_width=True)
                
                # عرض الإحصائيات
                st.write("**الإحصائيات:**")
                st.dataframe(mtbf_summary, use_container_width=True)
                
                # تحميل البيانات
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    mtbf_data.to_excel(writer, sheet_name='MTBF_تفصيلي', index=False)
                    mtbf_summary.to_excel(writer, sheet_name='ملخص_MTBF', index=False)
                
                output.seek(0)
                
                st.download_button(
                    label="📥 تحميل تقرير MTBF",
                    data=output,
                    file_name=f"MTBF_{selected_mtbf_event}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning(f"الحدث '{selected_mtbf_event}' لم يحدث مرتين على الأقل في الفترة المحددة لحساب MTBF")
    
    # -----------------------------------------------------------------
    # 6. MTTR (متوسط وقت الإصلاح)
    # -----------------------------------------------------------------
    elif selected_analysis == "MTTR (متوسط وقت الإصلاح)":
        st.subheader("🔧 حساب MTTR (Mean Time To Repair)")
        
        # قسم اختيار الأعطال
        st.write("**اختر الأحداث التي تمثل الأعطال:**")
        all_events = sorted(filtered_df['Event'].unique().tolist())
        
        col1, col2 = st.columns(2)
        with col1:
            # اختيار متعدد للأعطال
            selected_failures = st.multiselect(
                "اختر أحداث الأعطال:",
                all_events,
                default=['Sliver break', 'Machine stopped']
            )
        with col2:
            # اختيار حدث الاستعادة (عادة Automatic mode)
            recovery_event = st.selectbox(
                "اختر حدث الاستعادة/التشغيل:",
                all_events,
                index=all_events.index('Automatic mode') if 'Automatic mode' in all_events else 0
            )
        
        if selected_failures and recovery_event:
            mttr_data, total_downtime, mttr_summary = calculate_mttr(df, selected_failures, recovery_event, start_dt, end_dt)
            
            if not mttr_data.empty:
                st.write("**نتائج حساب MTTR:**")
                
                # عرض البيانات التفصيلية
                st.write("**البيانات التفصيلية:**")
                st.dataframe(mttr_data, use_container_width=True)
                
                # عرض الإحصائيات
                st.write("**إحصائيات MTTR:**")
                st.dataframe(mttr_summary, use_container_width=True)
                
                # إحصائيات إضافية
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("إجمالي وقت التوقف", f"{total_downtime.total_seconds() / 60:.1f} دقيقة")
                with col2:
                    avg_mttr = mttr_data['المدة بالدقائق'].mean()
                    st.metric("متوسط MTTR", f"{avg_mttr:.1f} دقيقة")
                
                # تحميل البيانات
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    mttr_data.to_excel(writer, sheet_name='MTTR_تفصيلي', index=False)
                    mttr_summary.to_excel(writer, sheet_name='ملخص_MTTR', index=False)
                
                output.seek(0)
                
                st.download_button(
                    label="📥 تحميل تقرير MTTR",
                    data=output,
                    file_name=f"MTTR_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning(f"لم يتم العثور على الأحداث المحددة أو حدث الاستعادة بعدها في الفترة المحددة")
    
    # -----------------------------------------------------------------
    # 7. حساب الوقت بين الأحداث
    # -----------------------------------------------------------------
    elif selected_analysis == "حساب الوقت بين الأحداث":
        st.subheader("⏱️ حساب الوقت بين الأحداث")
        
        # قسم إدخال الأحداث
        st.write("**حدد الأحداث المراد حساب الوقت بينها:**")
        
        all_events = sorted(filtered_df['Event'].unique().tolist())
        
        col1, col2 = st.columns(2)
        with col1:
            # اختيار متعدد للأحداث الأولية
            selected_events1 = st.multiselect(
                "اختر الحدث/الأحداث الأولية:",
                all_events,
                default=['Sliver break']
            )
        
        with col2:
            # اختيار الحدث الثاني
            selected_event2 = st.selectbox(
                "اختر الحدث الثاني:",
                all_events,
                index=all_events.index('Automatic mode') if 'Automatic mode' in all_events else 0
            )
        
        if selected_events1 and selected_event2:
            # حساب الوقت بين الأحداث
            time_between_data, total_time = calculate_time_between_events(
                df, selected_events1, selected_event2, start_dt, end_dt
            )
            
            if not time_between_data.empty:
                st.write("**نتائج حساب الوقت بين الأحداث:**")
                
                # عرض البيانات التفصيلية
                st.write("**البيانات التفصيلية:**")
                st.dataframe(time_between_data, use_container_width=True)
                
                # إحصائيات إجمالية
                st.subheader("📊 الإحصائيات الإجمالية")
                
                # حسب الحدث الأول
                if len(selected_events1) > 1:
                    stats_by_event = time_between_data.groupby('الحدث الأول').agg({
                        'المدة بالدقائق': ['count', 'mean', 'sum']
                    }).round(2)
                    
                    stats_by_event.columns = ['عدد المرات', 'المتوسط (دقيقة)', 'الإجمالي (دقيقة)']
                    stats_by_event = stats_by_event.reset_index()
                    
                    st.write("**حسب نوع الحدث الأول:**")
                    st.dataframe(stats_by_event, use_container_width=True)
                
                # الإحصائيات الكلية
                total_occurrences = len(time_between_data)
                avg_time = time_between_data['المدة بالدقائق'].mean()
                max_time = time_between_data['المدة بالدقائق'].max()
                min_time = time_between_data['المدة بالدقائق'].min()
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("إجمالي التكرارات", total_occurrences)
                with col2:
                    st.metric("متوسط الوقت", f"{avg_time:.1f} دقيقة")
                with col3:
                    st.metric("إجمالي الوقت", f"{total_time.total_seconds() / 60:.1f} دقيقة")
                with col4:
                    st.metric("نطاق الوقت", f"{min_time:.1f} - {max_time:.1f} دقيقة")
                
                # خيارات إضافية
                st.subheader("⚙️ خيارات إضافية")
                
                # حساب إجمالي الوقت لحدث معين
                if len(selected_events1) > 1:
                    selected_for_total = st.selectbox(
                        "اختر حدث لحساب إجمالي وقته:",
                        selected_events1
                    )
                    
                    if selected_for_total:
                        event_total_time = time_between_data[
                            time_between_data['الحدث الأول'] == selected_for_total
                        ]['المدة بالدقائق'].sum()
                        
                        st.info(f"**إجمالي وقت {selected_for_total}: {event_total_time:.1f} دقيقة**")
                
                # تحميل البيانات
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    time_between_data.to_excel(writer, sheet_name='الوقت_بين_الأحداث', index=False)
                    
                    if len(selected_events1) > 1:
                        stats_by_event.to_excel(writer, sheet_name='الإحصائيات', index=False)
                
                output.seek(0)
                
                st.download_button(
                    label="📥 تحميل تقرير الوقت بين الأحداث",
                    data=output,
                    file_name=f"الوقت_بين_الأحداث_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning(f"لم يتم العثور على الأحداث المحددة أو الحدث الثاني بعدها في الفترة المحددة")

else:
    st.info("👆 الرجاء رفع ملف السجل للبدء في التحليل")
    
    # دليل الاستخدام
    with st.expander("📋 دليل الاستخدام"):
        st.markdown("""
        ### كيفية استخدام النظام:
        
        1. **رفع الملف**: اختر ملف السجل من الماكينة (Logbook_YYYYMMDD.txt)
        2. **اختيار التحليل**: اختر نوع التحليل من القائمة المنسدلة
        3. **تحديد الفترة**: حدد الفترة الزمنية المراد تحليلها
        4. **تخصيص التحليل**: ضبط الإعدادات حسب نوع التحليل المختار
        5. **تحميل النتائج**: يمكنك تحميل النتائج كملف Excel
        
        ### أنواع التحاليل المتاحة:
        
        **1. معاينة البيانات**
        - عرض البيانات الأصلية
        - إحصائيات سريعة
        - خيارات ترتيب وعرض
        
        **2. احصائيات عامة**
        - إجمالي الأحداث وأنواعها
        - المدة الزمنية
        - توزيع الأحداث حسب اليوم والساعة
        
        **3. أنواع الأحداث**
        - عرض جميع أنواع الأحداث
        - تفاصيل حدث معين
        - إحصائيات كل حدث
        
        **4. تكرارات الأحداث**
        - تكرار كل نوع حدث
        - النسبة المئوية
        - تحليل التكرار اليومي
        
        **5. MTBF (متوسط الوقت بين أعطال)**
        - حساب الوقت بين أعطال من نفس النوع
        - إحصائيات MTBF
        - تحميل تقرير مفصل
        
        **6. MTTR (متوسط وقت الإصلاح)**
        - حساب الوقت بين العطل والعودة للتشغيل
        - تحديد أحداث الأعطال والاستعادة
        - إحصائيات MTTR مفصلة
        
        **7. حساب الوقت بين الأحداث**
        - حساب الوقت بين أي حدثين أو مجموعات
        - إجمالي الوقت حسب نوع الحدث
        - خيارات متقدمة للتحليل
        """)

# تذييل الصفحة
st.markdown("---")
st.markdown("⚙️ *نظام تحليل سجلات الماكينة - إصدار 2.0*")
