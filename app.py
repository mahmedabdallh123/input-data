import streamlit as st
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="محلل أعطال الماكينة", layout="wide")
st.title("🛠️ محلل أعطال الماكينة")
st.markdown("تحميل وتحليل سجلات أعطال الماكينة بسهولة")

# ==================== دالة تحليل الملف ====================
def parse_log_file(content):
    """تحليل ملف السجلات واستخراج البيانات"""
    lines = content.split('\n')
    data = []
    current_date = ""
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('==='):
            continue
        
        # تقسيم السطر باستخدام علامات التبويب
        parts = re.split(r'\t+', line)
        
        # إذا كان السطر يحتوي على تاريخ
        if len(parts) >= 3 and re.match(r'\d{2}\.\d{2}\.\d{4}', parts[0]):
            current_date = parts[0]
            time = parts[1]
            event = parts[2]
            code = parts[3] if len(parts) > 3 else ""
        elif current_date and len(parts) >= 2:
            # إذا كان استمرار للسطر السابق
            time = parts[0]
            event = parts[1]
            code = parts[2] if len(parts) > 2 else ""
        else:
            continue
        
        # تحويل التاريخ والوقت
        try:
            dt = datetime.strptime(f"{current_date} {time}", "%d.%m.%Y %H:%M:%S")
        except:
            continue
        
        # تحديد نوع العطل
        fault_type = "آخر"
        if code.startswith('W'):
            fault_type = "تحذير"
        elif code.startswith('E'):
            fault_type = "خطأ"
        elif code.startswith('T'):
            fault_type = "مهمة"
        
        data.append({
            'التاريخ_الوقت': dt,
            'التاريخ': dt.date(),
            'الوقت': dt.time(),
            'الحدث': event,
            'الرمز': code,
            'نوع_العطل': fault_type,
            'الساعة': dt.hour
        })
    
    return pd.DataFrame(data)

# ==================== واجهة رفع الملف ====================
st.header("📤 رفع ملف السجلات")
uploaded_file = st.file_uploader("اختر ملف logbook.txt", type=['txt'])

if uploaded_file:
    try:
        # قراءة المحتوى
        content = uploaded_file.getvalue().decode('utf-8')
        
        # تحليل البيانات
        df = parse_log_file(content)
        
        if len(df) > 0:
            st.success(f"✅ تم تحليل {len(df)} حدث بنجاح")
            
            # ==================== عرض البيانات ====================
            st.header("📋 البيانات المستخرجة")
            st.dataframe(df.head(50))
            
            # ==================== الإحصائيات ====================
            st.header("📊 الإحصائيات")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("عدد الأحداث", len(df))
            with col2:
                st.metric("عدد الأيام", df['التاريخ'].nunique())
            with col3:
                faults = df[df['الرمز'].str.startswith(('W', 'E', 'T'), na=False)]
                st.metric("عدد الأعطال", len(faults))
            with col4:
                st.metric("الفترة", f"{df['التاريخ'].min()} إلى {df['التاريخ'].max()}")
            
            # ==================== تحليل الأعطال ====================
            st.header("🔍 تحليل الأعطال")
            
            # تصفية الأعطال فقط
            faults_df = df[df['الرمز'].str.startswith(('W', 'E', 'T'), na=False)].copy()
            
            if len(faults_df) > 0:
                # 1. أكثر الأعطال تكراراً
                st.subheader("أكثر الأعطال تكراراً")
                fault_counts = faults_df['الرمز'].value_counts().head(15)
                
                # عرض كجدول
                st.table(fault_counts.reset_index().rename(
                    columns={'index': 'رمز العطل', 'الرمز': 'عدد التكرارات'}
                ))
                
                # 2. توزيع الأعطال حسب النوع
                st.subheader("توزيع الأعطال حسب النوع")
                type_counts = faults_df['نوع_العطل'].value_counts()
                
                # عرض كجدول مع ألوان
                type_df = type_counts.reset_index()
                st.dataframe(type_df.style.bar(subset=['count'], color='#FF4B4B'))
                
                # 3. تحليل حسب الساعة
                st.subheader("توزيع الأعطال خلال اليوم")
                hour_counts = faults_df['الساعة'].value_counts().sort_index()
                st.bar_chart(hour_counts)
                
                # ==================== تحليل الفترة الزمنية ====================
                st.header("⏱️ تحليل الفترة بين الأعطال")
                
                selected_fault = st.selectbox(
                    "اختر عطلاً لتحليل الفترة بين تكراراته",
                    options=[''] + sorted(faults_df['الرمز'].unique().tolist())
                )
                
                if selected_fault:
                    fault_events = faults_df[faults_df['الرمز'] == selected_fault].sort_values('التاريخ_الوقت')
                    
                    if len(fault_events) > 1:
                        # حساب الفروق الزمنية
                        fault_events = fault_events.copy()
                        fault_events['الفترة_السابقة'] = fault_events['التاريخ_الوقت'].diff()
                        fault_events['الدقائق_بين_التكرارات'] = fault_events['الفترة_السابقة'].dt.total_seconds() / 60
                        
                        st.write(f"**العطل:** {selected_fault}")
                        st.write(f"**عدد التكرارات:** {len(fault_events)}")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("المتوسط", f"{fault_events['الدقائق_بين_التكرارات'].mean():.1f} دقيقة")
                        with col2:
                            st.metric("الأقصر", f"{fault_events['الدقائق_بين_التكرارات'].min():.1f} دقيقة")
                        with col3:
                            st.metric("الأطول", f"{fault_events['الدقائق_بين_التكرارات'].max():.1f} دقيقة")
                        
                        # عرض جدول التكرارات
                        st.dataframe(fault_events[[
                            'التاريخ_الوقت', 'الحدث', 'الدقائق_بين_التكرارات'
                        ]].head(20))
                        
                        # ==================== نظام التنبيهات ====================
                        st.subheader("🚨 نظام التنبيهات")
                        
                        threshold = st.slider(
                            "حدد الحد الأدنى للدقائق بين التكرارات",
                            min_value=1,
                            max_value=240,
                            value=30,
                            help="سيتم التنبيه إذا حدث العطل مرتين خلال هذه الدقائق"
                        )
                        
                        fast_repeats = fault_events[fault_events['الدقائق_بين_التكرارات'] < threshold]
                        
                        if len(fast_repeats) > 0:
                            st.warning(f"⚠️ **تنبيه:** العطل تكرر {len(fast_repeats)} مرة خلال أقل من {threshold} دقيقة")
                            st.dataframe(fast_repeats[['التاريخ_الوقت', 'الدقائق_بين_التكرارات']])
                        else:
                            st.success(f"✅ لا توجد تكرارات سريعة للعطل")
            
            # ==================== تحميل النتائج ====================
            st.header("💾 تصدير النتائج")
            
            # خيارات التصدير
            export_format = st.radio(
                "اختر صيغة التصدير",
                ["CSV", "Excel"]
            )
            
            if st.button("توليد التقرير"):
                if export_format == "CSV":
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        "📥 تحميل CSV",
                        csv,
                        "fault_analysis.csv",
                        "text/csv"
                    )
                else:
                    # استخدام BytesIO لملف Excel
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='كل_البيانات', index=False)
                        if len(faults_df) > 0:
                            faults_df.to_excel(writer, sheet_name='الأعطال_فقط', index=False)
                    
                    st.download_button(
                        "📥 تحميل Excel",
                        output.getvalue(),
                        "fault_analysis.xlsx",
                        "application/vnd.ms-excel"
                    )
            
            # ==================== تصفية البيانات ====================
            st.header("🔎 تصفية البيانات")
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("من تاريخ", value=df['التاريخ'].min())
            with col2:
                end_date = st.date_input("إلى تاريخ", value=df['التاريخ'].max())
            
            filtered_df = df[
                (df['التاريخ'] >= start_date) & 
                (df['التاريخ'] <= end_date)
            ]
            
            # تصفية حسب نوع العطل
            fault_types = st.multiselect(
                "اختر نوع العطل",
                options=["كل الأنواع", "تحذير", "خطأ", "مهمة", "آخر"],
                default=["كل الأنواع"]
            )
            
            if "كل الأنواع" not in fault_types:
                filtered_df = filtered_df[filtered_df['نوع_العطل'].isin(fault_types)]
            
            st.write(f"عدد الأحداث المصفاة: {len(filtered_df)}")
            st.dataframe(filtered_df[['التاريخ_الوقت', 'الحدث', 'الرمز', 'نوع_العطل']].head(50))
            
        else:
            st.warning("⚠️ لم يتم العثور على بيانات قابلة للتحليل في الملف")
            
    except Exception as e:
        st.error(f"حدث خطأ: {str(e)}")

else:
    st.info("👆 يرجى رفع ملف السجلات لبدء التحليل")

# ==================== معلومات التثبيت ====================
with st.expander("🛠️ إرشادات التثبيت"):
    st.markdown("""
    ### المتطلبات الأساسية:
    
    ```bash
    pip install streamlit pandas
    ```
    
    ### تشغيل التطبيق محلياً:
    
    ```bash
    streamlit run app.py
    ```
    
    ### هيكل ملف السجلات المتوقع:
    ```
    23.12.2024    19:06:26    Starting speed    ON
    23.12.2024    19:11:04    Thick spots       W0547
    23.12.2024    19:11:11    Thick spots monitoring    E0431
    ```
    
    ### ميزات التطبيق:
    1. تحليل تلقائي لسجلات الأعطال
    2. إحصائيات تفصيلية
    3. تحليل الفترة الزمنية بين الأعطال
    4. نظام تنبيهات للتكرار السريع
    5. تصدير النتائج بصيغ مختلفة
    6. تصفية متقدمة للبيانات
    """)

# ==================== حقل الاختبار ====================
with st.expander("🧪 اختبار سريع بدون ملف"):
    test_content = st.text_area("الصق بيانات اختبارية هنا:", height=150, 
                               value="23.12.2024\t19:06:26\tStarting speed\tON\n23.12.2024\t19:11:04\tThick spots\tW0547")
    
    if st.button("تحليل بيانات الاختبار"):
        if test_content:
            test_df = parse_log_file(test_content)
            if len(test_df) > 0:
                st.success(f"تم تحليل {len(test_df)} حدث اختباري")
                st.dataframe(test_df)
            else:
                st.warning("لم يتم العثور على بيانات قابلة للتحليل")
