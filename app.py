import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import io

# إعداد واجهة Streamlit الأساسية
st.set_page_config(page_title="نظام تحليل سجلات الماكينة", layout="wide")
st.title("🏭 نظام تحليل سجلات الماكينة")
st.markdown("### تحليل سجلات الماكينة وإحصائيات الأعطال")

# -------------------------------------------------------------
# دالة لتحميل البيانات
# -------------------------------------------------------------
def load_data(uploaded_file):
    """تحميل ومعالجة ملف السجل"""
    lines = uploaded_file.read().decode('utf-8').splitlines()
    
    data = []
    for line in lines:
        # تخطي الأسطر الفارغة أو التي تبدأ بـ "="
        if line.startswith("=") or line.strip() == "":
            continue
        
        # تقسيم البيانات بعلامات التبويب
        parts = line.split("\t")
        
        # التأكد من أن لدينا 4 أعمدة على الأقل
        while len(parts) < 4:
            parts.append("")
        
        data.append([part.strip() for part in parts])
    
    # إنشاء DataFrame
    df = pd.DataFrame(data, columns=["Date", "Time", "Event", "Details"])
    
    # تنظيف البيانات
    df = df[(df['Date'].str.strip() != '') & (df['Time'].str.strip() != '')]
    
    # دمج التاريخ والوقت
    df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%d.%m.%Y %H:%M:%S')
    
    return df

# -------------------------------------------------------------
# دالة لحساب الوقت بين حدثين
# -------------------------------------------------------------
def calculate_time_between(df, start_event_list, end_event, start_date, end_date):
    """حساب الوقت بين قائمة من الأحداث وحدث معين"""
    
    # تصفية البيانات حسب الفترة
    filtered_df = df[(df['DateTime'] >= start_date) & (df['DateTime'] <= end_date)]
    
    if filtered_df.empty:
        return pd.DataFrame(), timedelta()
    
    # ترتيب البيانات حسب الوقت
    sorted_df = filtered_df.sort_values('DateTime')
    
    results = []
    total_time = timedelta()
    
    # معالجة كل حدث في القائمة
    for start_event in start_event_list:
        # الحصول على جميع تكرارات الحدث الأول
        start_events = sorted_df[sorted_df['Event'] == start_event]
        
        for idx, row in start_events.iterrows():
            start_time = row['DateTime']
            
            # البحث عن الحدث الثاني بعد الحدث الأول
            end_events = sorted_df[
                (sorted_df['Event'] == end_event) & 
                (sorted_df['DateTime'] > start_time)
            ]
            
            if not end_events.empty:
                end_time = end_events.iloc[0]['DateTime']
                time_difference = end_time - start_time
                
                # تخزين النتائج
                results.append({
                    'الحدث الأول': start_event,
                    'وقت الحدث الأول': start_time,
                    'الحدث الثاني': end_event,
                    'وقت الحدث الثاني': end_time,
                    'المدة': time_difference,
                    'المدة (دقيقة)': time_difference.total_seconds() / 60
                })
                
                total_time += time_difference
    
    # تحويل النتائج إلى DataFrame
    if results:
        results_df = pd.DataFrame(results)
        return results_df, total_time
    else:
        return pd.DataFrame(), timedelta()

# -------------------------------------------------------------
# دالة لحساب MTBF
# -------------------------------------------------------------
def calculate_mtbf(df, event, start_date, end_date):
    """حساب متوسط الوقت بين أعطال من نفس النوع"""
    
    # تصفية البيانات للحدث المحدد
    filtered_df = df[
        (df['Event'] == event) & 
        (df['DateTime'] >= start_date) & 
        (df['DateTime'] <= end_date)
    ].sort_values('DateTime')
    
    if len(filtered_df) < 2:
        return pd.DataFrame(), pd.DataFrame()
    
    results = []
    total_time_between = timedelta()
    
    # حساب الوقت بين كل حدثين متتاليين
    for i in range(1, len(filtered_df)):
        event1_time = filtered_df.iloc[i-1]['DateTime']
        event2_time = filtered_df.iloc[i]['DateTime']
        time_between = event2_time - event1_time
        
        results.append({
            'الحدث': event,
            'التكرار الأول': i,
            'وقت التكرار الأول': event1_time,
            'وقت التكرار الثاني': event2_time,
            'الوقت بين التكرارين': time_between,
            'المدة (ساعة)': time_between.total_seconds() / 3600
        })
        
        total_time_between += time_between
    
    # إنشاء DataFrame للنتائج
    results_df = pd.DataFrame(results)
    
    # حساب إحصائيات MTBF
    if not results_df.empty:
        avg_mtbf = results_df['المدة (ساعة)'].mean()
        min_mtbf = results_df['المدة (ساعة)'].min()
        max_mtbf = results_df['المدة (ساعة)'].max()
        total_intervals = len(results_df)
        
        stats_df = pd.DataFrame({
            'المؤشر': ['متوسط MTBF', 'أقصر فترة', 'أطول فترة', 'عدد الفترات'],
            'القيمة': [
                f"{avg_mtbf:.2f} ساعة",
                f"{min_mtbf:.2f} ساعة",
                f"{max_mtbf:.2f} ساعة",
                f"{total_intervals}"
            ]
        })
    else:
        stats_df = pd.DataFrame()
    
    return results_df, stats_df

# -------------------------------------------------------------
# دالة لحساب الإحصائيات العامة
# -------------------------------------------------------------
def calculate_general_stats(df, start_date, end_date):
    """حساب الإحصائيات العامة"""
    
    filtered_df = df[(df['DateTime'] >= start_date) & (df['DateTime'] <= end_date)]
    
    stats = {
        'إجمالي الأحداث': len(filtered_df),
        'عدد أنواع الأحداث': filtered_df['Event'].nunique(),
        'الفترة الزمنية': f"{start_date.date()} إلى {end_date.date()}",
        'المدة الإجمالية': str(end_date - start_date).split('.')[0],
        'أول حدث': filtered_df['DateTime'].min() if not filtered_df.empty else 'N/A',
        'آخر حدث': filtered_df['DateTime'].max() if not filtered_df.empty else 'N/A'
    }
    
    return pd.DataFrame(stats.items(), columns=['المؤشر', 'القيمة'])

# -------------------------------------------------------------
# الواجهة الرئيسية
# -------------------------------------------------------------

# قائمة منسدلة لاختيار نوع التحليل
analysis_options = [
    "اختر نوع التحليل...",
    "معاينة البيانات",
    "احصائيات عامة",
    "أنواع الأحداث",
    "تكرارات الأحداث",
    "MTBF - متوسط الوقت بين أعطال",
    "MTTR - متوسط وقت الإصلاح",
    "حساب الوقت بين الأحداث"
]

selected_option = st.selectbox("اختر نوع التحليل:", analysis_options)

# قسم رفع الملف
uploaded_file = st.file_uploader("رفع ملف السجل", type=["txt"])

if uploaded_file is not None:
    # تحميل البيانات
    df = load_data(uploaded_file)
    
    # قسم اختيار الفترة الزمنية
    st.subheader("تحديد الفترة الزمنية")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date_input = st.date_input("من تاريخ", df['DateTime'].min().date())
    with col2:
        end_date_input = st.date_input("إلى تاريخ", df['DateTime'].max().date())
    
    # تحويل التواريخ
    start_datetime = datetime.combine(start_date_input, datetime.min.time())
    end_datetime = datetime.combine(end_date_input, datetime.max.time())
    
    # تصفية البيانات حسب الفترة
    filtered_df = df[
        (df['DateTime'] >= start_datetime) & 
        (df['DateTime'] <= end_datetime)
    ]
    
    # ------------------------------------------------------------------
    # 1. معاينة البيانات
    # ------------------------------------------------------------------
    if selected_option == "معاينة البيانات":
        st.subheader("📄 معاينة البيانات")
        
        # خيارات العرض
        col1, col2 = st.columns(2)
        with col1:
            show_rows = st.number_input("عدد الصفوف المعروضة", 10, 500, 100)
        with col2:
            sort_order = st.radio("ترتيب البيانات", ["الأحدث أولاً", "الأقدم أولاً"])
        
        # تحضير البيانات للعرض
        display_df = filtered_df.copy()
        
        if sort_order == "الأحدث أولاً":
            display_df = display_df.sort_values('DateTime', ascending=False)
        else:
            display_df = display_df.sort_values('DateTime', ascending=True)
        
        # عرض البيانات
        st.dataframe(display_df.head(show_rows))
        
        # معلومات إضافية
        st.info(f"إجمالي الصفوف في الفترة المحددة: {len(filtered_df)}")
    
    # ------------------------------------------------------------------
    # 2. احصائيات عامة
    # ------------------------------------------------------------------
    elif selected_option == "احصائيات عامة":
        st.subheader("📊 الإحصائيات العامة")
        
        stats_df = calculate_general_stats(df, start_datetime, end_datetime)
        st.table(stats_df)
        
        # إحصائيات إضافية
        st.subheader("معلومات إضافية")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("إجمالي الأحداث", len(filtered_df))
        with col2:
            st.metric("أنواع الأحداث", filtered_df['Event'].nunique())
        with col3:
            days_diff = (end_datetime - start_datetime).days
            st.metric("المدة بالأيام", days_diff)
    
    # ------------------------------------------------------------------
    # 3. أنواع الأحداث
    # ------------------------------------------------------------------
    elif selected_option == "أنواع الأحداث":
        st.subheader("🔍 أنواع الأحداث المختلفة")
        
        # الحصول على جميع أنواع الأحداث
        unique_events = filtered_df['Event'].unique().tolist()
        
        # عرض عدد الأحداث لكل نوع
        event_counts = filtered_df['Event'].value_counts().reset_index()
        event_counts.columns = ['نوع الحدث', 'العدد']
        
        st.write(f"**إجمالي أنواع الأحداث: {len(unique_events)}**")
        st.table(event_counts)
        
        # خيار لعرض تفاصيل حدث معين
        selected_event = st.selectbox("اختر حدث لعرض تفاصيله:", unique_events)
        
        if selected_event:
            event_data = filtered_df[filtered_df['Event'] == selected_event]
            
            st.write(f"**تفاصيل الحدث: {selected_event}**")
            st.write(f"عدد مرات الحدوث: {len(event_data)}")
            st.write(f"أول مرة: {event_data['DateTime'].min()}")
            st.write(f"آخر مرة: {event_data['DateTime'].max()}")
            
            # عرض 5 أحداث عشوائية
            st.write("أمثلة على الأحداث:")
            st.table(event_data.head(5)[['DateTime', 'Details']])
    
    # ------------------------------------------------------------------
    # 4. تكرارات الأحداث
    # ------------------------------------------------------------------
    elif selected_option == "تكرارات الأحداث":
        st.subheader("🔄 تكرارات الأحداث")
        
        # حساب التكرارات
        frequency_df = filtered_df['Event'].value_counts().reset_index()
        frequency_df.columns = ['الحدث', 'التكرار']
        
        # حساب النسبة المئوية
        total_events = frequency_df['التكرار'].sum()
        frequency_df['النسبة %'] = (frequency_df['التكرار'] / total_events * 100).round(2)
        
        st.table(frequency_df)
        
        # تحليل تكرار حدث معين
        all_events = filtered_df['Event'].unique().tolist()
        selected_for_analysis = st.selectbox("اختر حدث لتحليل تكراره:", all_events)
        
        if selected_for_analysis:
            # الحصول على بيانات الحدث المحدد
            event_data = filtered_df[filtered_df['Event'] == selected_for_analysis]
            
            # إضافة عمود اليوم
            event_data['اليوم'] = event_data['DateTime'].dt.date
            
            # حساب التكرار اليومي
            daily_freq = event_data.groupby('اليوم').size().reset_index()
            daily_freq.columns = ['اليوم', 'التكرار']
            
            st.write(f"**التكرار اليومي للحدث: {selected_for_analysis}**")
            st.table(daily_freq)
            
            # إحصائيات التكرار اليومي
            if not daily_freq.empty:
                st.write("**إحصائيات التكرار اليومي:**")
                st.write(f"متوسط التكرار اليومي: {daily_freq['التكرار'].mean():.2f}")
                st.write(f"أعلى تكرار يومي: {daily_freq['التكرار'].max()}")
                st.write(f"أقل تكرار يومي: {daily_freq['التكرار'].min()}")
    
    # ------------------------------------------------------------------
    # 5. MTBF - متوسط الوقت بين أعطال
    # ------------------------------------------------------------------
    elif selected_option == "MTBF - متوسط الوقت بين أعطال":
        st.subheader("🔄 MTBF - متوسط الوقت بين أعطال")
        
        # اختيار نوع العطل
        all_events = filtered_df['Event'].unique().tolist()
        selected_failure = st.selectbox("اختر نوع العطل لحساب MTBF:", all_events)
        
        if selected_failure:
            # حساب MTBF
            mtbf_data, mtbf_stats = calculate_mtbf(df, selected_failure, start_datetime, end_datetime)
            
            if not mtbf_data.empty:
                st.write(f"**MTBF للعطل: {selected_failure}**")
                
                # عرض البيانات التفصيلية
                st.write("البيانات التفصيلية:")
                st.table(mtbf_data)
                
                # عرض الإحصائيات
                st.write("إحصائيات MTBF:")
                st.table(mtbf_stats)
                
                # خيار لتحميل البيانات
                csv = mtbf_data.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="تحميل بيانات MTBF",
                    data=csv,
                    file_name=f"mtbf_{selected_failure}.csv",
                    mime="text/csv"
                )
            else:
                st.warning(f"العطل '{selected_failure}' لم يحدث مرتين على الأقل في الفترة المحددة")
    
    # ------------------------------------------------------------------
    # 6. MTTR - متوسط وقت الإصلاح
    # ------------------------------------------------------------------
    elif selected_option == "MTTR - متوسط وقت الإصلاح":
        st.subheader("🔧 MTTR - متوسط وقت الإصلاح")
        
        # قسم اختيار الأحداث
        st.write("**اختر الأحداث التي تمثل الأعطال:**")
        all_events = filtered_df['Event'].unique().tolist()
        
        # اختيار متعدد للأعطال
        selected_failures = st.multiselect(
            "اختر أحداث الأعطال:",
            all_events,
            default=['Sliver break', 'Machine stopped'] if 'Sliver break' in all_events else []
        )
        
        # اختيار حدث الاستعادة
        recovery_event = st.selectbox(
            "اختر حدث الاستعادة/التشغيل:",
            all_events,
            index=all_events.index('Automatic mode') if 'Automatic mode' in all_events else 0
        )
        
        if selected_failures and recovery_event:
            # حساب MTTR
            mttr_data, total_downtime = calculate_time_between(
                df, selected_failures, recovery_event, start_datetime, end_datetime
            )
            
            if not mttr_data.empty:
                st.write("**نتائج حساب MTTR:**")
                
                # عرض البيانات التفصيلية
                st.table(mttr_data)
                
                # إحصائيات MTTR
                st.write("**إحصائيات MTTR:**")
                
                # حسب نوع العطل
                if len(selected_failures) > 1:
                    stats_by_event = mttr_data.groupby('الحدث الأول').agg({
                        'المدة (دقيقة)': ['count', 'mean', 'sum']
                    }).round(2)
                    
                    stats_by_event.columns = ['عدد المرات', 'متوسط MTTR (دقيقة)', 'إجمالي الوقت (دقيقة)']
                    st.table(stats_by_event)
                
                # الإحصائيات الإجمالية
                total_failures = len(mttr_data)
                avg_mttr = mttr_data['المدة (دقيقة)'].mean()
                total_downtime_minutes = total_downtime.total_seconds() / 60
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("إجمالي الأعطال", total_failures)
                with col2:
                    st.metric("متوسط MTTR", f"{avg_mttr:.1f} دقيقة")
                with col3:
                    st.metric("إجمالي وقت التوقف", f"{total_downtime_minutes:.1f} دقيقة")
                
                # تحميل البيانات
                csv = mttr_data.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="تحميل بيانات MTTR",
                    data=csv,
                    file_name="mttr_data.csv",
                    mime="text/csv"
                )
            else:
                st.warning("لم يتم العثور على الأحداث المحددة في الفترة المحددة")
    
    # ------------------------------------------------------------------
    # 7. حساب الوقت بين الأحداث
    # ------------------------------------------------------------------
    elif selected_option == "حساب الوقت بين الأحداث":
        st.subheader("⏱️ حساب الوقت بين الأحداث")
        
        # قسم إدخال الأحداث
        st.write("**حدد الأحداث المراد حساب الوقت بينها:**")
        
        all_events = filtered_df['Event'].unique().tolist()
        
        col1, col2 = st.columns(2)
        with col1:
            # حدث أو أحداث أولية
            selected_events1 = st.multiselect(
                "الحدث/الأحداث الأولية:",
                all_events,
                default=['Sliver break'] if 'Sliver break' in all_events else []
            )
        
        with col2:
            # الحدث الثاني
            selected_event2 = st.selectbox(
                "الحدث الثاني:",
                all_events,
                index=all_events.index('Automatic mode') if 'Automatic mode' in all_events else 0
            )
        
        if selected_events1 and selected_event2:
            # حساب الوقت بين الأحداث
            time_data, total_time = calculate_time_between(
                df, selected_events1, selected_event2, start_datetime, end_datetime
            )
            
            if not time_data.empty:
                st.write("**النتائج:**")
                
                # عرض البيانات التفصيلية
                st.table(time_data)
                
                # إحصائيات إجمالية
                st.write("**الإحصائيات الإجمالية:**")
                
                # حسب الحدث الأول
                if len(selected_events1) > 1:
                    event_stats = time_data.groupby('الحدث الأول').agg({
                        'المدة (دقيقة)': ['count', 'mean', 'sum']
                    }).round(2)
                    
                    event_stats.columns = ['عدد المرات', 'المتوسط (دقيقة)', 'الإجمالي (دقيقة)']
                    st.table(event_stats)
                
                # الإحصائيات الكلية
                total_occurrences = len(time_data)
                avg_time = time_data['المدة (دقيقة)'].mean()
                total_minutes = total_time.total_seconds() / 60
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("إجمالي التكرارات", total_occurrences)
                with col2:
                    st.metric("متوسط الوقت", f"{avg_time:.1f} دقيقة")
                with col3:
                    st.metric("إجمالي الوقت", f"{total_minutes:.1f} دقيقة")
                
                # خيار لحساب إجمالي وقت حدث معين
                if len(selected_events1) > 1:
                    st.write("**حساب إجمالي وقت حدث معين:**")
                    
                    event_for_total = st.selectbox(
                        "اختر حدث لحساب إجمالي وقته:",
                        selected_events1
                    )
                    
                    if event_for_total:
                        event_total = time_data[time_data['الحدث الأول'] == event_for_total]['المدة (دقيقة)'].sum()
                        st.success(f"إجمالي وقت {event_for_total}: {event_total:.1f} دقيقة")
                
                # تحميل البيانات
                csv = time_data.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="تحميل البيانات",
                    data=csv,
                    file_name="time_between_events.csv",
                    mime="text/csv"
                )
            else:
                st.warning("لم يتم العثور على الأحداث المحددة في الفترة المحددة")

else:
    # واجهة بدون ملف مرفوع
    st.info("👆 الرجاء رفع ملف السجل للبدء في التحليل")
    
    st.write("""
    ### دليل الاستخدام:
    
    1. **رفع ملف السجل**: اختر ملف Logbook_YYYYMMDD.txt من الماكينة
    2. **اختيار التحليل**: اختر نوع التحليل من القائمة المنسدلة
    3. **تحديد الفترة**: حدد الفترة الزمنية المراد تحليلها
    4. **تحليل البيانات**: ستظهر النتائج حسب التحليل المختار
    
    ### أنواع التحاليل المتاحة:
    
    - **معاينة البيانات**: عرض البيانات الأصلية
    - **احصائيات عامة**: إحصائيات عامة عن الأحداث
    - **أنواع الأحداث**: عرض جميع أنواع الأحداث وتفاصيلها
    - **تكرارات الأحداث**: تحليل تكرار كل نوع حدث
    - **MTBF**: متوسط الوقت بين أعطال من نفس النوع
    - **MTTR**: متوسط وقت الإصلاح بين العطل والعودة للتشغيل
    - **حساب الوقت بين الأحداث**: حساب الوقت بين أي حدثين أو مجموعات
    """)

# تذييل الصفحة
st.markdown("---")
st.markdown("نظام تحليل سجلات الماكينة - إصدار مبسط")
