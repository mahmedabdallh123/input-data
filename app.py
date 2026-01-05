import pandas as pd
import numpy as np
import streamlit as st
import io

# تهيئة صفحة Streamlit
st.set_page_config(page_title="تحليل سجل الأحداث", layout="wide")
st.title("📊 تحليل سجل الأحداث الصناعية (Logbook Analysis)")
st.markdown("### حساب MTTR, MTBF وتكرارات الأحداث")

# رفع الملف
uploaded_file = st.file_uploader("اختر ملف السجل (Logbook_YYYYMMDD.txt)", type="txt")

if uploaded_file is not None:
    # قراءة الملف مباشرة
    content = uploaded_file.read().decode('utf-8')
    lines = content.split('\n')
    
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
    
    if not data:
        st.error("❌ لم يتم العثور على بيانات في الملف!")
        st.stop()
    
    # إنشاء DataFrame
    df = pd.DataFrame(data, columns=["Date", "Time", "Event", "Details"])
    
    st.success(f"✅ تم تحميل {len(df)} حدث بنجاح!")
    
    # عرض عينة من البيانات
    with st.expander("📄 عرض عينة من البيانات (أول 50 سطر)"):
        st.dataframe(df.head(50), use_container_width=True)
    
    # تحويل التاريخ والوقت إلى كائن datetime
    try:
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%d.%m.%Y %H:%M:%S', errors='coerce')
    except Exception as e:
        st.error(f"❌ خطأ في تحويل التواريخ: {e}")
        df['DateTime'] = pd.NaT
    
    # إزالة الصفوف التي لا تحتوي على تاريخ/وقت صحيح
    df = df.dropna(subset=['DateTime']).sort_values('DateTime').reset_index(drop=True)
    
    if len(df) == 0:
        st.error("❌ لا توجد بيانات صالحة للتحليل بعد تصفية التواريخ!")
        st.stop()
    
    # إنشاء علامات للأحداث
    failure_patterns = ['E', 'W', 'T']
    df['IsFailure'] = df['Event'].apply(lambda x: any(str(x).startswith(pattern) for pattern in failure_patterns))
    df['IsStoppage'] = df['Event'].astype(str).str.contains('stopped|Stopped|machine stopped', case=False, na=False)
    df['IsStartup'] = df['Event'].astype(str).str.contains('Starting speed|Automatic mode|starting', case=False, na=False)
    
    # ==================== قسم 1: حساب تكرارات الأحداث ====================
    st.subheader("📈 1. تحليل تكرارات الأحداث")
    
    event_counts = df['Event'].value_counts().reset_index()
    event_counts.columns = ['الحدث', 'عدد التكرارات']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**أكثر 20 حدث تكرارًا:**")
        st.dataframe(event_counts.head(20), use_container_width=True)
    
    with col2:
        # عرض إحصائيات
        total_events = len(df)
        failure_events = df['IsFailure'].sum()
        stoppage_events = df['IsStoppage'].sum()
        
        st.metric("إجمالي الأحداث", f"{total_events:,}")
        st.metric("أحداث إخفاق", f"{failure_events:,}")
        st.metric("أحداث توقف", f"{stoppage_events:,}")
        st.metric("أنواع مختلفة من الأحداث", f"{len(event_counts):,}")
    
    # ==================== قسم 2: حساب MTBF ====================
    st.subheader("⏱️ 2. حساب MTBF (متوسط الوقت بين الأعطال)")
    
    # البحث عن فترات التشغيل
    operation_periods = []
    current_start = None
    
    for i in range(len(df)):
        if df.iloc[i]['IsStartup'] and current_start is None:
            current_start = df.iloc[i]['DateTime']
        elif (df.iloc[i]['IsFailure'] or df.iloc[i]['IsStoppage']) and current_start is not None:
            current_end = df.iloc[i]['DateTime']
            operation_periods.append((current_start, current_end))
            current_start = None
    
    # حساب MTBF
    if operation_periods and len(operation_periods) > 1:
        time_between_failures = []
        for i in range(1, len(operation_periods)):
            time_diff = (operation_periods[i][0] - operation_periods[i-1][1]).total_seconds() / 60
            if time_diff > 0:
                time_between_failures.append(time_diff)
        
        if time_between_failures:
            mttf = np.mean(time_between_failures)
            mttf_std = np.std(time_between_failures)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("MTBF (متوسط)", f"{mttf:.2f} دقيقة", 
                         delta=f"±{mttf_std:.2f} دقيقة")
            with col2:
                st.metric("الانحراف المعياري", f"{mttf_std:.2f} دقيقة")
            with col3:
                st.metric("عدد الفترات", len(time_between_failures))
            
            # عرض جدول بالأوقات
            with st.expander("عرض تفاصيل الأوقات بين الأعطال"):
                tb_df = pd.DataFrame({
                    'الفترة': range(1, len(time_between_failures) + 1),
                    'الوقت بين الأعطال (دقيقة)': time_between_failures
                })
                st.dataframe(tb_df, use_container_width=True)
        else:
            st.warning("⚠️ لا توجد فترات تشغيل كافية لحساب MTBF")
    else:
        st.warning("⚠️ لا توجد فترات تشغيل كافية لحساب MTBF")
    
    # ==================== قسم 3: حساب MTTR ====================
    st.subheader("🔧 3. حساب MTTR (متوسط وقت الإصلاح)")
    
    # البحث عن فترات الإصلاح
    repair_times = []
    
    for i in range(len(df) - 1):
        if df.iloc[i]['IsFailure'] or df.iloc[i]['IsStoppage']:
            failure_time = df.iloc[i]['DateTime']
            
            for j in range(i + 1, len(df)):
                if df.iloc[j]['IsStartup']:
                    repair_time = df.iloc[j]['DateTime']
                    repair_duration = (repair_time - failure_time).total_seconds() / 60
                    if 0 < repair_duration < 1440:
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
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("MTTR (متوسط)", f"{mttr:.2f} دقيقة", 
                     delta=f"±{mttr_std:.2f} دقيقة")
        with col2:
            st.metric("الانحراف المعياري", f"{mttr_std:.2f} دقيقة")
        with col3:
            st.metric("عدد حالات الإصلاح", len(repair_times))
        
        with st.expander("عرض تفاصيل فترات الإصلاح"):
            st.dataframe(repair_df, use_container_width=True)
    else:
        st.warning("⚠️ لا توجد حالات إصلاح كافية لحساب MTTR")
    
    # ==================== قسم 4: تحميل النتائج ====================
    st.subheader("💾 4. تحميل النتائج")
    
    # إنشاء ملف Excel
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # حفظ البيانات الأصلية
        df.to_excel(writer, sheet_name='البيانات الأصلية', index=False)
        
        # حفظ تكرارات الأحداث
        event_counts.to_excel(writer, sheet_name='تكرارات الأحداث', index=False)
        
        # حفظ تحليل MTBF
        if 'time_between_failures' in locals() and time_between_failures:
            mtbf_summary = pd.DataFrame({
                'المؤشر': ['MTBF', 'الانحراف المعياري', 'عدد الفترات'],
                'القيمة': [mttf, mttf_std, len(time_between_failures)]
            })
            mtbf_summary.to_excel(writer, sheet_name='MTBF تحليل', index=False)
        
        # حفظ تحليل MTTR
        if repair_times:
            repair_df.to_excel(writer, sheet_name='أوقات الإصلاح', index=False)
            mttr_summary = pd.DataFrame({
                'المؤشر': ['MTTR', 'الانحراف المعياري', 'عدد الحالات'],
                'القيمة': [mttr, mttr_std, len(repair_times)]
            })
            mttr_summary.to_excel(writer, sheet_name='MTTR تحليل', index=False)
        
        # إنشاء ملخص
        summary_data = {
            'المؤشر': [
                'إجمالي الأحداث',
                'أحداث إخفاق',
                'أحداث توقف',
                'أنواع الأحداث المختلفة'
            ],
            'القيمة': [
                total_events,
                failure_events,
                stoppage_events,
                len(event_counts)
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='ملخص', index=False)
    
    output.seek(0)
    
    # زر التنزيل
    st.download_button(
        label="📥 تنزيل النتائج كملف Excel",
        data=output,
        file_name="نتائج_تحليل_السجل.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("⬆️ يرجى رفع ملف السجل لبدء التحليل")

# تعليمات التشغيل في الشريط الجانبي
st.sidebar.header("🚀 تعليمات التشغيل")
st.sidebar.markdown("""
1. **حفظ الكود** في ملف باسم `app.py`
2. **تثبيت المكتبات**:
```bash
pip install streamlit pandas numpy openpyxl
