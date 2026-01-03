import pandas as pd
import streamlit as st
from datetime import datetime
import io

# إعداد واجهة Streamlit
st.set_page_config(page_title="تحليل سجلات ماكينة الكرد", layout="wide")
st.title("📊 لوحة تحليل سجلات ماكينة الكرد - تفاعلية")
st.markdown("رفع ملف السجل (Logbook) للحصول على تحليل فوري للأعطال والفترات الزمنية")

# 1. رفع الملف
uploaded_file = st.file_uploader("📁 اختر ملف السجل (Logbook_YYYYMMDD.txt)", type=["txt"])

if uploaded_file is not None:
    # قراءة الملف
    lines = uploaded_file.read().decode('utf-8').splitlines()
    
    # معالجة البيانات
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
    
    # عرض البيانات الأولية
    st.subheader("📄 معاينة البيانات")
    st.dataframe(df.head(), use_container_width=True)
    
    # إحصائيات سريعة
    st.subheader("📈 إحصائيات عامة")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("إجمالي الأحداث", df.shape[0])
    with col2:
        st.metric("عدد أنواع الأحداث", df['Event'].nunique())
    with col3:
        st.metric("الفترة الزمنية", f"{df['DateTime'].min():%d/%m/%Y} إلى {df['DateTime'].max():%d/%m/%Y}")
    with col4:
        st.metric("المدة الكلية", f"{(df['DateTime'].max() - df['DateTime'].min()).days} يوم")
    
    # 2. تحليل الأعطال
    st.subheader("🔧 تحليل الأعطال والإنذارات")
    
    # اختيار الفترة الزمنية
    min_date = df['DateTime'].min().date()
    max_date = df['DateTime'].max().date()
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("إلى تاريخ", max_date, min_value=min_date, max_value=max_date)
    
    # تحويل إلى datetime
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    # تصفية البيانات
    filtered_df = df[(df['DateTime'] >= start_dt) & (df['DateTime'] <= end_dt)]
    
    # عد الأحداث
    event_counts = filtered_df['Event'].value_counts().reset_index()
    event_counts.columns = ['الحدث', 'عدد التكرارات']
    
    st.write("**تكرارات الأحداث:**")
    st.dataframe(event_counts, use_container_width=True)
    
    # 3. تحليل الوقت الضائع لكل عطل
    st.subheader("⏱️ حساب الوقت الضائع بين العطل و'Automatic mode'")
    
    # اختيار الأحداث المراد تحليلها
    all_events = filtered_df['Event'].unique().tolist()
    selected_events = st.multiselect(
        "اختر الأحداث المراد تحليل وقتها:",
        all_events,
        default=['Sliver break', 'Suction pressure monitoring', 'Machine stopped']
    )
    
    if selected_events:
        # فرز البيانات
        sorted_df = filtered_df.sort_values('DateTime')
        
        results = []
        for event in selected_events:
            event_df = sorted_df[sorted_df['Event'] == event]
            
            for _, row in event_df.iterrows():
                current_time = row['DateTime']
                
                # البحث عن أقرب 'Automatic mode' بعد الحدث
                auto_mode_df = sorted_df[
                    (sorted_df['Event'] == 'Automatic mode') &
                    (sorted_df['DateTime'] > current_time)
                ]
                
                if not auto_mode_df.empty:
                    next_auto_mode_time = auto_mode_df.iloc[0]['DateTime']
                    time_difference = next_auto_mode_time - current_time
                    
                    results.append({
                        'وقت الحدث': current_time,
                        'الحدث': event,
                        'وقت Automatic mode التالي': next_auto_mode_time,
                        'المدة الزمنية': time_difference
                    })
        
        if results:
            results_df = pd.DataFrame(results)
            results_df['المدة بالدقائق'] = results_df['المدة الزمنية'].dt.total_seconds() / 60
            
            st.write("**النتائج:**")
            st.dataframe(results_df, use_container_width=True)
            
            # إجمالي الوقت الضائع
            total_time = results_df['المدة الزمنية'].sum()
            total_minutes = total_time.total_seconds() / 60
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("إجمالي الوقت الضائع", f"{total_minutes:.1f} دقيقة")
            with col2:
                st.metric("إجمالي الوقت الضائع", f"{total_minutes/60:.1f} ساعة")
            
            # رسم بياني
            st.subheader("📊 توزيع الوقت الضائع حسب الحدث")
            time_by_event = results_df.groupby('الحدث')['المدة بالدقائق'].sum().reset_index()
            st.bar_chart(time_by_event.set_index('الحدث'))
            
            # 4. تصدير النتائج
            st.subheader("📥 تصدير النتائج")
            
            # إنشاء Excel في الذاكرة
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='البيانات_الأصلية', index=False)
                event_counts.to_excel(writer, sheet_name='عدد_الأحداث', index=False)
                results_df.to_excel(writer, sheet_name='الوقت_الضائع', index=False)
            
            output.seek(0)
            
            # زر التحميل
            st.download_button(
                label="📥 تحميل النتائج كملف Excel",
                data=output,
                file_name=f"تحليل_السجل_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ لم يتم العثور على 'Automatic mode' بعد الأحداث المحددة")
    else:
        st.info("👈 الرجاء اختيار أحداث لتحليل الوقت الضائع")
    
    # 5. عرض الأحداث الهامة
    st.subheader("🚨 الأحداث الهامة (إنذارات وأعطال)")
    
    # تعريف الأحداث الهامة
    critical_events = ['Sliver break', 'Machine stopped', 'Safety circuit is interrupted',
                      'Suction pressure monitoring', 'Drive block', 'Plant not ready for operation']
    
    critical_df = filtered_df[filtered_df['Event'].isin(critical_events)]
    
    if not critical_df.empty:
        st.dataframe(critical_df[['DateTime', 'Event', 'Details']].sort_values('DateTime', ascending=False), 
                    use_container_width=True)
        
        # عد الأحداث الحرجة
        critical_counts = critical_df['Event'].value_counts()
        st.write("**توزيع الأحداث الهامة:**")
        st.bar_chart(critical_counts)
    else:
        st.success("✅ لا توجد أحداث حرجة في الفترة المحددة")
    
else:
    st.info("👆 الرجاء رفع ملف السجل للبدء في التحليل")
    st.markdown("""
    ### 📋 تعليمات الاستخدام:
    1. قم بتحميل ملف السجل (Logbook_YYYYMMDD.txt) من الماكينة
    2. اختر الفترة الزمنية المراد تحليلها
    3. اختر الأحداث المراد حساب الوقت الضائع لها
    4. احصل على تقرير مفصل وتحميل النتائج كملف Excel
    
    ### 🔧 الأحداث الشائعة في الماكينة:
    - **Sliver break**: قطع السليفر
    - **Machine stopped**: توقف الماكينة
    - **Suction pressure monitoring**: مراقبة ضغط الشفط
    - **Drive block**: توقف المحركات
    - **Automatic mode**: تشغيل الوضع التلقائي
    """)

# تذييل الصفحة
st.markdown("---")
st.markdown("📱 *يمكن استخدام هذا التطبيق من أي جهاز (موبايل، لابتوب، تابلت)*")
st.markdown("⚙️ *تم التطوير باستخدام Python + Streamlit*")
