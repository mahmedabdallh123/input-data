import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# استيراد datetime بطريقة آمنة
try:
    from datetime import datetime, timedelta
except ImportError as e:
    st.error(f"خطأ في استيراد datetime: {e}")
    st.stop()

import re

# ==================== واجهة مبسطة لبداية التشغيل ====================
st.set_page_config(page_title="محلل أعطال الماكينة", layout="wide", page_icon="🛠️")
st.title("🛠️ محلل أعطال الماكينة - التحليل الفوري")
st.markdown("تحميل ملف سجلات الماكينة وتحليل الأعطال بسهولة")

# ==================== دالة تحليل الملف ====================
def parse_log_file_safe(content):
    """
    دالة آمنة لتحليل ملف السجلات
    """
    try:
        lines = content.split('\n')
        data = []
        
        for line in lines:
            if not line.strip():
                continue
                
            # البحث عن نمط التاريخ والوقت
            date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})\t+(\d{2}:\d{2}:\d{2})', line)
            if date_match:
                date_str = date_match.group(1)
                time_str = date_match.group(2)
                
                try:
                    dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M:%S")
                except:
                    continue
                
                # استخراج الحدث والرمز
                parts = line.split('\t')
                if len(parts) >= 4:
                    event = parts[2] if len(parts) > 2 else ""
                    code = parts[3] if len(parts) > 3 else ""
                    
                    data.append({
                        'datetime': dt,
                        'date': dt.date(),
                        'time': dt.strftime("%H:%M:%S"),
                        'event': event,
                        'code': code
                    })
        
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"خطأ في تحليل الملف: {str(e)}")
        return pd.DataFrame()

# ==================== رفع الملف ====================
st.header("📤 رفع ملف السجلات")
uploaded_file = st.file_uploader("اختر ملف السجلات (Logbook_*.txt)", type=['txt'])

if uploaded_file is not None:
    try:
        content = uploaded_file.getvalue().decode('utf-8')
        st.success("✅ تم تحميل الملف بنجاح")
        
        # معاينة الملف
        with st.expander("👁️ معاينة الملف"):
            st.text(content[:2000])
        
        # تحليل البيانات
        df = parse_log_file_safe(content)
        
        if df.empty:
            st.warning("⚠️ لم يتم العثور على بيانات قابلة للتحليل")
        else:
            st.success(f"✅ تم تحليل {len(df)} حدث بنجاح")
            
            # ==================== عرض أساسي للبيانات ====================
            st.header("📋 البيانات المستخرجة")
            st.dataframe(df.head(20))
            
            # ==================== إحصائيات بسيطة ====================
            st.header("📊 إحصائيات سريعة")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("عدد الأحداث", len(df))
            with col2:
                st.metric("أول تاريخ", df['date'].min())
            with col3:
                st.metric("آخر تاريخ", df['date'].max())
            
            # ==================== تحليل الأعطال ====================
            st.header("🔍 تحليل الأعطال")
            
            # استخراج رموز الأعطال
            def extract_fault_type(code):
                if isinstance(code, str):
                    if code.startswith('W'):
                        return 'تحذير'
                    elif code.startswith('E'):
                        return 'خطأ'
                    elif code.startswith('T'):
                        return 'مهمة'
                return 'آخر'
            
            df['fault_category'] = df['code'].apply(extract_fault_type)
            
            # توزيع الأعطال
            fault_counts = df['fault_category'].value_counts()
            fig1 = px.pie(
                values=fault_counts.values,
                names=fault_counts.index,
                title="توزيع أنواع الأعطال"
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # ==================== أكثر الأعطال تكراراً ====================
            st.subheader("📈 أكثر الأعطال تكراراً")
            if 'code' in df.columns:
                top_codes = df['code'].value_counts().head(10)
                
                # تحويل للسلسلة لتجنب مشاكل الترميز
                top_codes_str = top_codes.astype(str)
                
                fig2 = px.bar(
                    x=top_codes_str.values,
                    y=top_codes_str.index.astype(str),
                    orientation='h',
                    labels={'x': 'عدد التكرارات', 'y': 'رمز العطل'},
                    title="أكثر 10 أعطال تكراراً"
                )
                st.plotly_chart(fig2, use_container_width=True)
                
                # عرض جدول الأعطال
                st.dataframe(top_codes.reset_index().rename(
                    columns={'index': 'رمز العطل', 'code': 'التكرارات'}
                ))
            
            # ==================== تحميل النتائج ====================
            st.header("💾 تحميل النتائج")
            
            if st.button("تصدير البيانات كملف CSV"):
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 انقر لتحميل CSV",
                    data=csv,
                    file_name="fault_analysis.csv",
                    mime="text/csv"
                )
    
    except Exception as e:
        st.error(f"حدث خطأ أثناء معالجة الملف: {str(e)}")

else:
    st.info("👆 يرجى رفع ملف سجلات الماكينة (.txt) لبدء التحليل")

# ==================== معلومات التثبيت ====================
with st.expander("🛠️ معلومات التثبيت والاستخدام"):
    st.markdown("""
    ### المتطلبات المسبقة:
    
    ```bash
    pip install streamlit pandas plotly
    ```
    
    ### تشغيل التطبيق:
    
    ```bash
    streamlit run app.py
    ```
    
    ### هيكل ملف السجلات المطلوب:
    ```
    23.12.2024	19:06:26	Starting speed	ON
    23.12.2024	19:06:56	Automatic mode
    23.12.2024	19:11:04	Thick spots	W0547
    ```
    
    ### دعم الفني:
    - تأكد من ترميز الملف بـ UTF-8
    - الملف يجب أن يحتوي على تواريخ بتنسيق DD.MM.YYYY
    - يمكن استخدام نموذج البيانات الموجود في الأعلى
    """)

# ==================== حقل اختبار ====================
with st.expander("🧪 اختبار سريع (بدون رفع ملف)"):
    test_data = st.text_area("الصق بيانات اختبار هنا:", height=200)
    if st.button("تحليل بيانات الاختبار"):
        if test_data:
            test_df = parse_log_file_safe(test_data)
            if not test_df.empty:
                st.success(f"تم تحليل {len(test_df)} حدث اختباري")
                st.dataframe(test_df)
            else:
                st.warning("لم يتم العثور على بيانات قابلة للتحليل")
