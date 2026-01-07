import streamlit as st
import pandas as pd
import re
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="محلل أعطال الماكينة", layout="wide")
st.title("🛠️ محلل أعطال الماكينة")
st.markdown("تحميل وتحليل سجلات أعطال الماكينة بسهولة")

# ==================== دالة تحليل الملف ====================
def parse_log_file_updated(content):
    """تحليل ملف السجلات بناء على التنسيق المحدد"""
    lines = content.split('\n')
    data = []
    current_date = ""
    last_event = ""
    
    for line in lines:
        line = line.strip()
        
        # تخطي الأسطر الفارغة وأسرار الرأس
        if not line or line.startswith('===') or line.startswith('==='):
            continue
        
        # إذا كان السطر يحتوي على تاريخ (يبدأ بتاريخ)
        if re.match(r'^\d{2}\.\d{2}\.\d{4}', line):
            parts = line.split('\t')
            
            # حالة 1: سطر عادي (تاريخ - وقت - حدث - رمز)
            if len(parts) >= 3:
                date_part = parts[0]
                time_part = parts[1]
                event_part = parts[2]
                code_part = parts[3] if len(parts) > 3 else ""
                
                # تحقق أن الوقت صحيح (يحتوي على :)
                if ':' in time_part:
                    current_date = date_part
                    
                    try:
                        dt = datetime.strptime(f"{current_date} {time_part}", "%d.%m.%Y %H:%M:%S")
                    except:
                        continue
                    
                    data.append({
                        'datetime': dt,
                        'date': dt.date(),
                        'time': dt.time(),
                        'event': event_part.strip(),
                        'code': code_part.strip(),
                        'hour': dt.hour
                    })
        
        # إذا كان السطر استمراراً (يبدأ بمسافات)
        elif line.startswith('          ') or line.startswith('\t'):
            parts = line.split('\t')
            if len(parts) >= 2 and current_date:
                time_part = parts[0].strip()
                if time_part and ':' in time_part:
                    event_part = parts[1] if len(parts) > 1 else ""
                    code_part = parts[2] if len(parts) > 2 else ""
                    
                    try:
                        dt = datetime.strptime(f"{current_date} {time_part}", "%d.%m.%Y %H:%M:%S")
                    except:
                        continue
                    
                    data.append({
                        'datetime': dt,
                        'date': dt.date(),
                        'time': dt.time(),
                        'event': event_part.strip(),
                        'code': code_part.strip(),
                        'hour': dt.hour
                    })
    
    return pd.DataFrame(data)

# ==================== دالة أخرى للتحليل ====================
def parse_log_file_alternative(content):
    """طريقة بديلة لتحليل الملف"""
    data = []
    
    # استخدام regex للعثور على جميع التواريخ والأوقات
    pattern = r'(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2}:\d{2})\s+(.+?)(?:\t+|\s+)(.+)?$'
    
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('==='):
            continue
        
        # البحث عن النمط
        match = re.search(pattern, line, re.MULTILINE)
        if match:
            date_str = match.group(1)
            time_str = match.group(2)
            event = match.group(3).strip()
            code = match.group(4).strip() if match.group(4) else ""
            
            try:
                dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M:%S")
                data.append({
                    'datetime': dt,
                    'date': dt.date(),
                    'time': dt.time(),
                    'event': event,
                    'code': code,
                    'hour': dt.hour
                })
            except:
                continue
    
    return pd.DataFrame(data)

# ==================== دالة مبسطة للغاية ====================
def parse_log_simple(content):
    """تحليل مبسط مباشر"""
    data = []
    
    lines = content.split('\n')
    for line in lines:
        # تجاهل الأسطر غير المهمة
        if 'Starting speed' in line or 'Automatic mode' in line or 'Thick spots' in line:
            # ابحث عن التاريخ والوقت
            date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', line)
            time_match = re.search(r'(\d{2}:\d{2}:\d{2})', line)
            
            if date_match and time_match:
                date_str = date_match.group(1)
                time_str = time_match.group(1)
                
                # استخرج الحدث
                event = ""
                if 'Starting speed' in line:
                    event = "Starting speed"
                elif 'Automatic mode' in line:
                    event = "Automatic mode"
                elif 'Thick spots' in line:
                    event = "Thick spots"
                
                # استخرج الرمز إذا موجود
                code_match = re.search(r'([WET]\d{4})', line)
                code = code_match.group(1) if code_match else ""
                
                try:
                    dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M:%S")
                    data.append({
                        'datetime': dt,
                        'date': dt.date(),
                        'time': dt.time(),
                        'event': event,
                        'code': code,
                        'hour': dt.hour
                    })
                except:
                    continue
    
    return pd.DataFrame(data)

# ==================== واجهة التطبيق ====================
st.header("📤 رفع ملف السجلات")
uploaded_file = st.file_uploader("اختر ملف Logbook_*.txt", type=['txt'])

if uploaded_file is not None:
    try:
        # قراءة الملف
        content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
        
        # معاينة أول 500 حرف من الملف
        with st.expander("👁️ معاينة الملف"):
            st.text(content[:1000])
        
        # محاولة التحليل بطرق مختلفة
        st.info("🔍 جاري تحليل الملف...")
        
        # الطريقة 1
        df1 = parse_log_file_updated(content)
        
        # الطريقة 2
        df2 = parse_log_file_alternative(content)
        
        # الطريقة 3
        df3 = parse_log_simple(content)
        
        # اختيار أفضل نتيجة
        dfs = [("الطريقة 1", df1), ("الطريقة 2", df2), ("الطريقة 3", df3)]
        best_df = None
        best_name = ""
        
        for name, df in dfs:
            if len(df) > 0:
                best_df = df
                best_name = name
                break
        
        if best_df is not None and len(best_df) > 0:
            df = best_df
            st.success(f"✅ تم تحليل {len(df)} حدث بنجاح (باستخدام {best_name})")
            
            # ==================== عرض البيانات ====================
            st.header("📋 البيانات المستخرجة")
            st.dataframe(df)
            
            # ==================== تحليل بسيط ====================
            st.header("📊 تحليل سريع")
            
            # إحصائيات أساسية
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("إجمالي الأحداث", len(df))
            with col2:
                unique_events = df['event'].nunique()
                st.metric("أنواع الأحداث", unique_events)
            with col3:
                faults_count = len(df[df['code'].str.startswith(('W', 'E', 'T'), na=False)])
                st.metric("عدد الأعطال", faults_count)
            
            # أكثر الأحداث تكراراً
            st.subheader("أكثر الأحداث تكراراً")
            event_counts = df['event'].value_counts().head(10)
            st.table(event_counts.reset_index().rename(
                columns={'index': 'الحدث', 'event': 'التكرار'}
            ))
            
            # أكثر الأعطال تكراراً
            faults_df = df[df['code'].str.startswith(('W', 'E', 'T'), na=False)]
            if len(faults_df) > 0:
                st.subheader("أكثر الأعطال تكراراً")
                fault_counts = faults_df['code'].value_counts().head(10)
                st.table(fault_counts.reset_index().rename(
                    columns={'index': 'رمز العطل', 'code': 'التكرار'}
                ))
                
                # توزيع الأعطال حسب النوع
                st.subheader("توزيع الأعطال حسب النوع")
                def get_fault_type(code):
                    if str(code).startswith('W'):
                        return 'تحذير'
                    elif str(code).startswith('E'):
                        return 'خطأ'
                    elif str(code).startswith('T'):
                        return 'مهمة'
                    return 'أخرى'
                
                faults_df['نوع العطل'] = faults_df['code'].apply(get_fault_type)
                type_counts = faults_df['نوع العطل'].value_counts()
                st.table(type_counts.reset_index().rename(
                    columns={'index': 'نوع العطل', 'نوع العطل': 'العدد'}
                ))
            
            # ==================== تحميل النتائج ====================
            st.header("💾 تصدير البيانات")
            
            if st.button("تصدير كملف CSV"):
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 انقر للتحميل",
                    data=csv,
                    file_name="machine_logs_analysis.csv",
                    mime="text/csv"
                )
            
            if st.button("تصدير كملف Excel"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='البيانات', index=False)
                    
                    # إضافة ورقة للإحصائيات
                    stats_df = pd.DataFrame({
                        'المؤشر': ['إجمالي الأحداث', 'عدد الأيام', 'نطاق التاريخ', 'عدد الأعطال'],
                        'القيمة': [
                            len(df),
                            df['date'].nunique(),
                            f"{df['date'].min()} إلى {df['date'].max()}",
                            len(faults_df)
                        ]
                    })
                    stats_df.to_excel(writer, sheet_name='الإحصائيات', index=False)
                
                st.download_button(
                    label="📥 تحميل Excel",
                    data=output.getvalue(),
                    file_name="machine_logs_analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
        else:
            st.error("⚠️ لم يتم العثور على بيانات قابلة للتحليل")
            
            # عرض عينة من الملف لفهم المشكلة
            st.subheader("🔍 محاولة فهم المشكلة")
            st.write("أول 20 سطراً من الملف:")
            st.text("\n".join(content.split('\n')[:20]))
            
    except Exception as e:
        st.error(f"❌ حدث خطأ: {str(e)}")

else:
    st.info("👆 يرجى رفع ملف السجلات (txt) لبدء التحليل")
    
    # زر لتحميل نموذج بيانات
    if st.button("تحميل نموذج بيانات للاختبار"):
        sample_data = """23.12.2024	19:06:26	Starting speed	ON
23.12.2024	19:06:56	Automatic mode	
23.12.2024	19:11:04	Thick spots	W0547
          	        	Trützschler Card	
23.12.2024	19:11:11	Thick spots monitoring	E0431
23.12.2024	19:13:17	DFK active	ON
23.12.2024	19:13:18	DFK active	OFF
23.12.2024	19:13:18	DFK deactivated	W0534
          	        	DFK	
23.12.2024	19:13:19	Starting speed	ON
23.12.2024	19:14:29	DFK active	ON"""
        
        df_sample = parse_log_simple(sample_data)
        if len(df_sample) > 0:
            st.success(f"تم تحليل {len(df_sample)} حدث في العينة")
            st.dataframe(df_sample)
        else:
            st.warning("لم يتم تحليل العينة")

# ==================== تعليمات الاستخدام ====================
with st.expander("📖 إرشادات الاستخدام"):
    st.markdown("""
    ### كيفية استخدام التطبيق:
    
    1. **رفع الملف**: انقر على زر رفع الملف واختر ملف `Logbook_*.txt`
    2. **التحليل التلقائي**: سيقوم التطبيق بتحليل البيانات تلقائياً
    3. **عرض النتائج**: تصفح البيانات والإحصائيات
    4. **التصدير**: حمّل النتائج كملف CSV أو Excel
    
    ### تنسيق الملف المتوقع:
    - ملف نصي (txt) بتنسيق جدولة
    - التاريخ بتنسيق `DD.MM.YYYY`
    - الوقت بتنسيق `HH:MM:SS`
    - مثال: `23.12.2024	19:06:26	Starting speed	ON`
    
    ### المتطلبات:
    ```bash
    pip install streamlit pandas openpyxl
    ```
    
    ### تشغيل محلي:
    ```bash
    streamlit run app.py
    ```
    """)

# ==================== تذييل ====================
st.markdown("---")
st.markdown("🛠️ **محلل أعطال الماكينة** | يمكن الوصول من أي مكان عبر الإنترنت")
