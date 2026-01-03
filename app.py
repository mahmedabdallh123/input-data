import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
from collections import Counter
import matplotlib.pyplot as plt
import io

# تهيئة صفحة Streamlit
st.set_page_config(page_title="تحليل سجل الأحداث", layout="wide")
st.title("📊 تحليل سجل الأحداث الصناعية (Logbook Analysis)")
st.markdown("### حساب MTTR, MTBF وتكرارات الأحداث")

# رفع الملف
uploaded_file = st.file_uploader("اختر ملف السجل (Logbook_YYYYMMDD.txt)", type="txt")

if uploaded_file is not None:
    # قراءة الملف
    lines = uploaded_file.readlines()
    
    # تحويل bytes إلى نص إذا لزم الأمر
    if isinstance(lines[0], bytes):
        lines = [line.decode('utf-8') for line in lines]
    else:
        lines = [line for line in lines]
    
    # معالجة البيانات
    data = []
    for line in lines:
        # تخطي الأسطر الفارغة أو رؤوس الجداول
        if line.startswith("=") or line.strip() == "":
            continue
        
        parts = line.split("\t")
        
        # التأكد من وجود 4 أعمدة
        while len(parts) < 4:
            parts.append("")
        
        # تنظيف البيانات
        cleaned_parts = [part.strip() for part in parts]
        
        # التأكد من وجود تاريخ ووقت
        if len(cleaned_parts) >= 2 and cleaned_parts[0] and cleaned_parts[1]:
            data.append(cleaned_parts[:4])  # أخذ أول 4 أعمدة فقط
    
    # إنشاء DataFrame
    df = pd.DataFrame(data, columns=["Date", "Time", "Event", "Details"])
    
    # عرض البيانات الأصلية
    with st.expander("📄 عرض البيانات الأصلية (أول 100 سطر)"):
        st.dataframe(df.head(100), use_container_width=True)
    
    # تحويل التاريخ والوقت إلى كائن datetime
    df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%d.%m.%Y %H:%M:%S', errors='coerce')
    
    # إزالة الصفوف التي لا تحتوي على تاريخ/وقت صحيح
    df = df.dropna(subset=['DateTime']).sort_values('DateTime').reset_index(drop=True)
    
    # إنشاء علامات للأحداث (محطات توقف/إخفاقات)
    # تحديد الأحداث التي تمثل إخفاقات/مشاكل (بالاعتماد على الأكواد التي تبدأ بـ E أو W)
    failure_patterns = ['E', 'W', 'T']  # رموز الأخطاء والتحذيرات
    df['IsFailure'] = df['Event'].apply(lambda x: any(x.startswith(pattern) for pattern in failure_patterns))
    df['IsStoppage'] = df['Event'].str.contains('stopped|Stopped|machine stopped', case=False, na=False)
    
    # تحديد أحداث بدء التشغيل
    df['IsStartup'] = df['Event'].str.contains('Starting speed|Automatic mode|starting', case=False, na=False)
    
    # ==================== قسم 1: حساب تكرارات الأحداث ====================
    st.subheader("📈 1. تحليل تكرارات الأحداث")
    
    # حساب تكرارات الأحداث
    event_counts = df['Event'].value_counts().reset_index()
    event_counts.columns = ['الحدث', 'عدد التكرارات']
    
    # عرض أهم 20 حدثًا
    st.markdown("**أكثر 20 حدث تكرارًا:**")
    st.dataframe(event_counts.head(20), use_container_width=True)
    
    # تحليل الأحداث حسب التصنيف
    failure_events = df[df['IsFailure']]['Event'].value_counts()
    if not failure_events.empty:
        st.markdown("**توزيع أحداث الإخفاق (بالرمز):**")
        failure_df = failure_events.reset_index()
        failure_df.columns = ['رمز الحدث', 'عدد التكرارات']
        st.dataframe(failure_df.head(20), use_container_width=True)
    
    # ==================== قسم 2: حساب MTBF (Mean Time Between Failures) ====================
    st.subheader("⏱️ 2. حساب MTBF (متوسط الوقت بين الأعطال)")
    
    # تحديد أوقات بداية ونهاية التشغيل
    operation_periods = []
    current_start = None
    current_end = None
    
    for i in range(len(df)):
        if df.iloc[i]['IsStartup'] and current_start is None:
            current_start = df.iloc[i]['DateTime']
        elif (df.iloc[i]['IsFailure'] or df.iloc[i]['IsStoppage']) and current_start is not None:
            current_end = df.iloc[i]['DateTime']
            if current_start and current_end:
                operation_periods.append((current_start, current_end))
                current_start = None
                current_end = None
    
    # حساب MTBF
    if operation_periods and len(operation_periods) > 1:
        time_between_failures = []
        for i in range(1, len(operation_periods)):
            # الوقت بين نهاية فترة التشغيل السابقة وبداية التالية
            time_diff = (operation_periods[i][0] - operation_periods[i-1][1]).total_seconds() / 60  # بالدقائق
            if time_diff > 0:  # تجاهل الفروق السلبية
                time_between_failures.append(time_diff)
        
        if time_between_failures:
            mttf = np.mean(time_between_failures)
            mttf_std = np.std(time_between_failures)
            mttf_min = np.min(time_between_failures)
            mttf_max = np.max(time_between_failures)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("MTBF (متوسط)", f"{mttf:.2f} دقيقة")
            with col2:
                st.metric("الانحراف المعياري", f"{mttf_std:.2f} دقيقة")
            with col3:
                st.metric("أقصر فترة", f"{mttf_min:.2f} دقيقة")
            with col4:
                st.metric("أطول فترة", f"{mttf_max:.2f} دقيقة")
            
            st.markdown(f"**عدد فترات التشغيل:** {len(time_between_failures)}")
            
            # عرض جدول بالأوقات بين الأعطال
            with st.expander("عرض تفاصيل الأوقات بين الأعطال"):
                tb_df = pd.DataFrame({
                    'رقم الفترة': range(1, len(time_between_failures) + 1),
                    'الوقت بين الأعطال (دقيقة)': time_between_failures
                })
                st.dataframe(tb_df, use_container_width=True)
    
    # ==================== قسم 3: حساب MTTR (Mean Time To Repair) ====================
    st.subheader("🔧 3. حساب MTTR (متوسط وقت الإصلاح)")
    
    # تحديد فترات التوقف (من وقت حدوث العطل إلى وقت إعادة التشغيل)
    repair_times = []
    
    for i in range(len(df) - 1):
        if df.iloc[i]['IsFailure'] or df.iloc[i]['IsStoppage']:
            failure_time = df.iloc[i]['DateTime']
            
            # البحث عن أقرب حدث بدء تشغيل بعد العطل
            for j in range(i + 1, len(df)):
                if df.iloc[j]['IsStartup']:
                    repair_time = df.iloc[j]['DateTime']
                    repair_duration = (repair_time - failure_time).total_seconds() / 60  # بالدقائق
                    if 0 < repair_duration < 1440:  # تجاهل الفترات الأطول من يوم (ربما بيانات غير صحيحة)
                        repair_times.append({
                            'العطل': df.iloc[i]['Event'],
                            'وقت العطل': failure_time,
                            'وقت الإصلاح': repair_time,
                            'مدة الإصلاح (دقيقة)': repair_duration
                        })
                    break
    
    if repair_times:
        repair_df = pd.DataFrame(repair_times)
        mttr = repair_df['مدة الإصلاح (دقيقة)'].mean()
        mttr_std = repair_df['مدة الإصلاح (دقيقة)'].std()
        mttr_min = repair_df['مدة الإصلاح (دقيقة)'].min()
        mttr_max = repair_df['مدة الإصلاح (دقيقة)'].max()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("MTTR (متوسط)", f"{mttr:.2f} دقيقة")
        with col2:
            st.metric("الانحراف المعياري", f"{mttr_std:.2f} دقيقة")
        with col3:
            st.metric("أقصر إصلاح", f"{mttr_min:.2f} دقيقة")
        with col4:
            st.metric("أطول إصلاح", f"{mttr_max:.2f} دقيقة")
        
        st.markdown(f"**عدد حالات الإصلاح:** {len(repair_times)}")
        
        # عرض فترات الإصلاح
        with st.expander("عرض تفاصيل فترات الإصلاح"):
            st.dataframe(repair_df, use_container_width=True)
        
        # تحليل أوقات الإصلاح حسب نوع العطل
        repair_by_failure = repair_df.groupby('العطل')['مدة الإصلاح (دقيقة)'].agg(['mean', 'count', 'std', 'min', 'max']).reset_index()
        repair_by_failure = repair_by_failure.sort_values('count', ascending=False)
        
        st.markdown("**متوسط وقت الإصلاح حسب نوع العطل:**")
        st.dataframe(repair_by_failure.head(15), use_container_width=True)
    
    # ==================== قسم 4: التحليل الزمني بين الأحداث ====================
    st.subheader("📅 4. التحليل الزمني بين الأحداث")
    
    # حساب الفترات الزمنية بين جميع الأحداث المتتالية
    df['الفرق الزمني (دقيقة)'] = df['DateTime'].diff().dt.total_seconds() / 60  # الفرق بالدقائق
    
    # عرض الفترات الزمنية بين الأحداث
    with st.expander("عرض الفترات الزمنية بين الأحداث المتتالية (أول 50 حدث)"):
        time_diff_df = df[['DateTime', 'Event', 'Details', 'الفرق الزمني (دقيقة)']].copy()
        st.dataframe(time_diff_df.head(50), use_container_width=True)
    
    # إحصائيات الفترات الزمنية
    st.markdown("**إحصائيات الفترات الزمنية بين الأحداث:**")
    time_stats = df['الفرق الزمني (دقيقة)'].describe()
    st.dataframe(time_stats.to_frame().T, use_container_width=True)
    
    # ==================== قسم 5: التحليل المتقدم ====================
    st.subheader("📊 5. تحليل متقدم")
    
    # تحليل حسب نوبات العمل
    df['الساعة'] = df['DateTime'].dt.hour
    df['الوردية'] = pd.cut(df['الساعة'], 
                          bins=[0, 8, 16, 24], 
                          labels=['الوردية الثالثة', 'الوردية الأولى', 'الوردية الثانية'])
    
    # حساب تكرار الأحداث حسب الوردية
    events_by_shift = df[df['IsFailure']].groupby('الوردية')['Event'].count().reset_index()
    events_by_shift.columns = ['الوردية', 'عدد الأحداث']
    
    st.markdown("**توزيع الأحداث حسب الوردية:**")
    st.dataframe(events_by_shift, use_container_width=True)
    
    # تحليل حسب اليوم والساعة
    hourly_events = df[df['IsFailure']].groupby('الساعة').size().reset_index()
    hourly_events.columns = ['الساعة', 'عدد الأحداث']
    
    st.markdown("**توزيع الأحداث حسب الساعة:**")
    st.dataframe(hourly_events.sort_values('الساعة'), use_container_width=True)
    
    # ==================== قسم 6: الملخص التنفيذي ====================
    st.subheader("📋 6. الملخص التنفيذي")
    
    # إنشاء بطاقات ملخصة
    total_events = len(df)
    failure_events_count = df['IsFailure'].sum()
    stoppage_events_count = df['IsStoppage'].sum()
    unique_events = df['Event'].nunique()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("إجمالي الأحداث", f"{total_events:,}")
    with col2:
        st.metric("أحداث إخفاق", f"{failure_events_count:,}")
    with col3:
        st.metric("أحداث توقف", f"{stoppage_events_count:,}")
    with col4:
        st.metric("أنواع أحداث مختلفة", f"{unique_events:,}")
    
    # حساب التوفر (Availability)
    if 'repair_times' in locals() and repair_times and 'time_between_failures' in locals() and time_between_failures:
        total_uptime = sum(time_between_failures)
        total_downtime = sum(repair_df['مدة الإصلاح (دقيقة)']) if 'repair_df' in locals() else 0
        if total_uptime + total_downtime > 0:
            availability = (total_uptime / (total_uptime + total_downtime)) * 100
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("التوفر التشغيلي", f"{availability:.2f}%")
            with col2:
                st.metric("إجمالي وقت التشغيل", f"{total_uptime:.2f} دقيقة")
            with col3:
                st.metric("إجمالي وقت التوقف", f"{total_downtime:.2f} دقيقة")
    
    # الأحداث الأكثر تكرارًا مع نسبتها
    top_events = event_counts.head(10).copy()
    top_events['النسبة %'] = (top_events['عدد التكرارات'] / total_events * 100).round(2)
    
    st.markdown("**الأحداث العشرة الأكثر تكرارًا:**")
    st.dataframe(top_events, use_container_width=True)
    
    # ==================== قسم 7: تحميل النتائج ====================
    st.subheader("💾 7. تحميل النتائج")
    
    # زر لحفظ النتائج
    if st.button("حفظ النتائج في ملف Excel"):
        # إنشاء ملف Excel في الذاكرة
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # حفظ البيانات الأصلية
            df.to_excel(writer, sheet_name='البيانات_الأصلية', index=False)
            
            # حفظ تكرارات الأحداث
            event_counts.to_excel(writer, sheet_name='تكرارات_الأحداث', index=False)
            
            # حفظ فترات الإصلاح إذا وجدت
            if 'repair_df' in locals():
                repair_df.to_excel(writer, sheet_name='أوقات_الإصلاح', index=False)
            
            # حفظ تحليل MTBF إذا وجد
            if 'time_between_failures' in locals() and time_between_failures:
                mtbf_df = pd.DataFrame({
                    'رقم_الفترة': range(1, len(time_between_failures) + 1),
                    'الوقت_بين_الأعطال_دقيقة': time_between_failures
                })
                mtbf_df.to_excel(writer, sheet_name='MTBF_تحليل', index=False)
            
            # إنشاء ملخص تنفيذي
            summary_data = {
                'المؤشر': [
                    'إجمالي الأحداث',
                    'أحداث إخفاق',
                    'أحداث توقف',
                    'أنواع أحداث مختلفة',
                    'إجمالي وقت التشغيل (دقيقة)',
                    'إجمالي وقت التوقف (دقيقة)',
                    'التوفر التشغيلي (%)'
                ],
                'القيمة': [
                    total_events,
                    failure_events_count,
                    stoppage_events_count,
                    unique_events,
                    total_uptime if 'total_uptime' in locals() else 0,
                    total_downtime if 'total_downtime' in locals() else 0,
                    availability if 'availability' in locals() else 0
                ]
            }
            
            if 'mttf' in locals():
                summary_data['المؤشر'].extend(['MTBF (دقيقة)', 'انحراف معياري MTBF'])
                summary_data['القيمة'].extend([round(mttf, 2), round(mttf_std, 2)])
            
            if 'mttr' in locals():
                summary_data['المؤشر'].extend(['MTTR (دقيقة)', 'انحراف معياري MTTR'])
                summary_data['القيمة'].extend([round(mttr, 2), round(mttr_std, 2)])
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='الملخص_التنفيذي', index=False)
            
            # حفظ توزيع الأحداث حسب الوردية
            events_by_shift.to_excel(writer, sheet_name='توزيع_الورديات', index=False)
            
            # حفظ توزيع الأحداث حسب الساعة
            hourly_events.to_excel(writer, sheet_name='توزيع_الساعات', index=False)
        
        output.seek(0)
        
        # تقديم رابط للتنزيل
        st.download_button(
            label="📥 تنزيل ملف Excel",
            data=output,
            file_name="نتائج_تحليل_السجل.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.success("✅ تم إنشاء الملف بنجاح! اضغط على زر التنزيل أعلاه.")

else:
    st.info("⬆️ يرجى رفع ملف السجل لبدء التحليل")

# تعليمات الاستخدام
with st.expander("📖 تعليمات الاستخدام"):
    st.markdown("""
    ### كيفية استخدام أداة تحليل السجل:
    
    1. **رفع الملف**: قم برفع ملف السجل النصي (Logbook_YYYYMMDD.txt)
    2. **تحليل البيانات**: سيقوم البرنامج تلقائيًا بـ:
       - حساب تكرارات كل حدث
       - حساب MTBF (متوسط الوقت بين الأعطال)
       - حساب MTTR (متوسط وقت الإصلاح)
       - تحليل الفترات الزمنية بين الأحداث
    3. **تصدير النتائج**: يمكنك حفظ النتائج في ملف Excel
    
    ### تعريف المؤشرات:
    - **MTBF (Mean Time Between Failures)**: متوسط الوقت بين الأعطال المتتالية
    - **MTTR (Mean Time To Repair)**: متوسط الوقت اللازم لإصلاح العطل
    - **التوفر**: نسبة الوقت الذي يكون فيه النظام قيد التشغيل
    
    ### ملاحظات:
    - يتم تحديد الأعطال تلقائيًا بناءً على رموز الأخطاء (E, W, T)
    - يتم حساب الأوقات بالدقائق
    - يمكن تحميل الملفات ذات الصيغة TXT فقط
    - يتم عرض جميع النتائج في جداول تفاعلية
    """)
