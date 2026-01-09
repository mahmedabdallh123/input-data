import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import base64

# تهيئة إعدادات الصفحة
st.set_page_config(
    page_title="عرض بيانات السجل التقني",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# إضافة CSS مخصص لتحسين المظهر
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1E3A8A;
        padding: 20px 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 30px;
    }
    .stDataFrame {
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
</style>
""", unsafe_allow_html=True)

# عنوان التطبيق
st.markdown('<div class="main-header"><h1>📋 نظام عرض بيانات السجل التقني</h1><h3>عرض وتحليل بيانات أعطال المعدات</h3></div>', unsafe_allow_html=True)

# الشريط الجانبي
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/data-configuration.png", width=100)
    st.markdown("### ⚙️ إعدادات العرض")
    
    # خيارات عرض البيانات
    st.markdown("#### خيارات البيانات:")
    show_raw_data = st.checkbox("عرض البيانات الخام", value=True)
    show_stats = st.checkbox("عرض الإحصائيات", value=True)
    show_charts = st.checkbox("عرض الرسوم البيانية", value=True)
    
    st.markdown("---")
    st.markdown("#### تصفية البيانات:")
    
    # زر إعادة تحميل البيانات
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    st.markdown("#### معلومات:")
    st.info("""
    **مميزات التطبيق:**
    - عرض كامل للبيانات
    - إحصائيات تفصيلية
    - تصورات بيانية متقدمة
    - تصدير للعديد من الصيغ
    """)

# دالة لتحميل البيانات من GitHub
@st.cache_data
def load_data_from_github():
    """
    تحميل البيانات من GitHub أو المسار المحلي
    """
    try:
        # حاول تحميل من GitHub أولاً
        github_url = "https://raw.githubusercontent.com/username/repo/main/organized_logbook.xlsx"
        df = pd.read_excel(github_url)
        st.sidebar.success("✅ تم تحميل البيانات من GitHub")
        return df
    except:
        try:
            # إذا فشل، جرب المسار المحلي
            df = pd.read_excel("organized_logbook.xlsx")
            st.sidebar.success("✅ تم تحميل البيانات من الملف المحلي")
            return df
        except Exception as e:
            st.sidebar.error(f"❌ لم يتم العثور على ملف البيانات: {e}")
            # إنشاء بيانات تجريبية للعرض
            sample_data = {
                "Date": pd.date_range(start="2024-01-01", periods=100, freq='H'),
                "Time": [f"{i%24:02d}:{(i*30)%60:02d}" for i in range(100)],
                "Event": ["Automatic mode", "Manual mode", "Error 001", "Maintenance", 
                         "System Reset", "Error 002", "Calibration", "Error 003"] * 12 + ["Automatic mode", "Manual mode"],
                "Details": [f"Detail {i}" for i in range(100)]
            }
            df = pd.DataFrame(sample_data)
            st.sidebar.warning("⚠️ يتم عرض بيانات تجريبية")
            return df

# تحميل البيانات
df = load_data_from_github()

# تحضير البيانات
if 'DateTime' not in df.columns and 'Date' in df.columns and 'Time' in df.columns:
    try:
        df['DateTime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
    except:
        df['DateTime'] = pd.to_datetime(df['Date'])

# قسم العرض الرئيسي
tab1, tab2, tab3, tab4 = st.tabs(["📋 عرض البيانات", "📊 الإحصائيات", "📈 الرسوم البيانية", "📥 التصدير"])

with tab1:
    st.header("📋 عرض البيانات التفصيلي")
    
    # إعدادات عرض البيانات
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rows_to_show = st.slider("عدد الصفوف للعرض:", 10, 1000, 100, 10)
    
    with col2:
        sort_column = st.selectbox("ترتيب البيانات حسب:", 
                                  ['DateTime', 'Date', 'Time', 'Event'] if 'DateTime' in df.columns else df.columns.tolist())
    
    with col3:
        sort_order = st.radio("نوع الترتيب:", ["تصاعدي", "تنازلي"], horizontal=True)
    
    # تصفية حسب التاريخ إذا كان موجوداً
    if 'DateTime' in df.columns:
        st.markdown("### ⏰ تصفية حسب التاريخ")
        date_col1, date_col2 = st.columns(2)
        
        with date_col1:
            start_date = st.date_input("من تاريخ:", 
                                      value=df['DateTime'].min().date(),
                                      min_value=df['DateTime'].min().date(),
                                      max_value=df['DateTime'].max().date())
        
        with date_col2:
            end_date = st.date_input("إلى تاريخ:", 
                                    value=df['DateTime'].max().date(),
                                    min_value=df['DateTime'].min().date(),
                                    max_value=df['DateTime'].max().date())
        
        # تطبيق التصفية
        df_filtered = df[(df['DateTime'].dt.date >= start_date) & 
                        (df['DateTime'].dt.date <= end_date)].copy()
    else:
        df_filtered = df.copy()
    
    # تصفية حسب الحدث
    if 'Event' in df_filtered.columns:
        st.markdown("### 🔍 تصفية حسب الحدث")
        all_events = ['الكل'] + sorted(df_filtered['Event'].dropna().unique().tolist())
        selected_events = st.multiselect("اختر الأحداث:", 
                                        all_events[1:], 
                                        default=all_events[1] if len(all_events) > 1 else [])
        
        if selected_events:
            df_filtered = df_filtered[df_filtered['Event'].isin(selected_events)]
    
    # ترتيب البيانات
    ascending_order = True if sort_order == "تصاعدي" else False
    df_display = df_filtered.sort_values(by=sort_column, ascending=ascending_order).head(rows_to_show)
    
    # عرض البيانات
    st.markdown(f"### 📄 عرض البيانات ({len(df_display)} من {len(df_filtered)} سجل)")
    
    # استخدام ميزة Data Editor للعرض التفاعلي
    st.dataframe(
        df_display,
        use_container_width=True,
        height=600,
        column_config={
            "DateTime": st.column_config.DatetimeColumn("التاريخ والوقت"),
            "Date": st.column_config.TextColumn("التاريخ"),
            "Time": st.column_config.TextColumn("الوقت"),
            "Event": st.column_config.TextColumn("الحدث"),
            "Details": st.column_config.TextColumn("التفاصيل", width="large")
        }
    )
    
    # عرض ملخص سريع
    st.markdown(f"""
    <div class="metric-card">
        <h4>📊 ملخص البيانات</h4>
        <p>• عدد السجلات الكلي: <strong>{len(df):,}</strong></p>
        <p>• عدد السجلات بعد التصفية: <strong>{len(df_filtered):,}</strong></p>
        <p>• عدد السجلات المعروضة: <strong>{len(df_display):,}</strong></p>
    </div>
    """, unsafe_allow_html=True)

with tab2:
    st.header("📊 الإحصائيات التحليلية")
    
    if len(df_filtered) > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("إجمالي السجلات", f"{len(df_filtered):,}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if 'DateTime' in df_filtered.columns:
                date_range = (df_filtered['DateTime'].max() - df_filtered['DateTime'].min()).days
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("المدة الزمنية (أيام)", f"{date_range:,}")
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            if 'Event' in df_filtered.columns:
                unique_events = df_filtered['Event'].nunique()
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("عدد أنواع الأحداث", f"{unique_events:,}")
                st.markdown('</div>', unsafe_allow_html=True)
        
        # إحصائيات الأحداث
        if 'Event' in df_filtered.columns:
            st.subheader("📋 توزيع الأحداث")
            event_stats = df_filtered['Event'].value_counts().reset_index()
            event_stats.columns = ['الحدث', 'التكرار']
            
            col4, col5 = st.columns([3, 2])
            
            with col4:
                st.dataframe(
                    event_stats,
                    use_container_width=True,
                    height=400
                )
            
            with col5:
                fig_pie = px.pie(
                    event_stats.head(10),
                    values='التكرار',
                    names='الحدث',
                    title="توزيع أهم 10 أحداث"
                )
                fig_pie.update_layout(height=400)
                st.plotly_chart(fig_pie, use_container_width=True)
        
        # إحصائيات زمنية
        if 'DateTime' in df_filtered.columns:
            st.subheader("⏰ إحصائيات زمنية")
            
            # استخراج الساعة واليوم
            df_filtered['Hour'] = df_filtered['DateTime'].dt.hour
            df_filtered['DayOfWeek'] = df_filtered['DateTime'].dt.day_name()
            df_filtered['Month'] = df_filtered['DateTime'].dt.month_name()
            
            col6, col7, col8 = st.columns(3)
            
            with col6:
                hourly_stats = df_filtered['Hour'].value_counts().sort_index()
                st.bar_chart(hourly_stats)
                st.caption("التوزيع على مدار الساعة")
            
            with col7:
                daily_stats = df_filtered['DayOfWeek'].value_counts()
                st.bar_chart(daily_stats)
                st.caption("التوزيع على أيام الأسبوع")
            
            with col8:
                monthly_stats = df_filtered['Month'].value_counts()
                st.bar_chart(monthly_stats)
                st.caption("التوزيع على الأشهر")
        
        # جدول تفصيلي للإحصائيات
        st.subheader("📈 الإحصائيات الوصفية")
        
        if 'DateTime' in df_filtered.columns:
            time_stats = df_filtered['DateTime'].describe()
            st.write("الإحصائيات الزمنية:")
            st.write(time_stats)
        
        # البحث في التفاصيل
        if 'Details' in df_filtered.columns:
            st.subheader("🔍 البحث في التفاصيل")
            search_term = st.text_input("ابحث في التفاصيل:")
            
            if search_term:
                search_results = df_filtered[df_filtered['Details'].str.contains(search_term, case=False, na=False)]
                st.write(f"نتائج البحث ({len(search_results)} سجل):")
                st.dataframe(search_results.head(20), use_container_width=True)

with tab3:
    st.header("📈 الرسوم البيانية التفاعلية")
    
    if len(df_filtered) > 0:
        chart_type = st.selectbox("نوع الرسم البياني:", 
                                 ["عمودي", "خطي", "دائري", "مبعثر", "مساحي"])
        
        if 'Event' in df_filtered.columns:
            # تحضير بيانات الأحداث
            event_data = df_filtered['Event'].value_counts().reset_index()
            event_data.columns = ['Event', 'Count']
            
            if chart_type == "عمودي":
                fig = px.bar(
                    event_data.head(20),
                    x='Event',
                    y='Count',
                    title="توزيع الأحداث (أعلى 20)",
                    color='Count',
                    color_continuous_scale='viridis'
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            elif chart_type == "خطي":
                if 'DateTime' in df_filtered.columns:
                    timeline_data = df_filtered.groupby(df_filtered['DateTime'].dt.date).size().reset_index()
                    timeline_data.columns = ['Date', 'Count']
                    fig = px.line(
                        timeline_data,
                        x='Date',
                        y='Count',
                        title="اتجاه الأحداث عبر الزمن"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            elif chart_type == "دائري":
                fig = px.pie(
                    event_data.head(10),
                    values='Count',
                    names='Event',
                    title="نسبة الأحداث (أعلى 10)",
                    hole=0.3
                )
                st.plotly_chart(fig, use_container_width=True)
            
            elif chart_type == "مبعثر":
                if 'DateTime' in df_filtered.columns and 'Event' in df_filtered.columns:
                    scatter_data = df_filtered.copy()
                    scatter_data['Hour'] = scatter_data['DateTime'].dt.hour
                    scatter_data['Day'] = scatter_data['DateTime'].dt.day
                    
                    fig = px.scatter(
                        scatter_data.head(100),
                        x='Day',
                        y='Hour',
                        color='Event',
                        size=[10]*len(scatter_data.head(100)),
                        title="توزيع الأحداث خلال اليوم والشهر"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            elif chart_type == "مساحي":
                if 'DateTime' in df_filtered.columns:
                    area_data = df_filtered.groupby(df_filtered['DateTime'].dt.date).size().reset_index()
                    area_data.columns = ['Date', 'Count']
                    fig = px.area(
                        area_data,
                        x='Date',
                        y='Count',
                        title="تراكم الأحداث عبر الزمن"
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        # رسم بياني تفاعلي متعدد
        st.subheader("🎛 رسم بياني تفاعلي متعدد")
        
        col_x, col_y, col_color = st.columns(3)
        
        with col_x:
            x_axis = st.selectbox("المحور X:", df_filtered.columns.tolist())
        
        with col_y:
            y_axis = st.selectbox("المحور Y:", ['عدد السجلات'] + df_filtered.columns.tolist())
        
        with col_color:
            color_by = st.selectbox("التلوين حسب:", ['لا شيء'] + df_filtered.columns.tolist())
        
        if st.button("إنشاء الرسم البياني", type="primary"):
            if y_axis == 'عدد السجلات':
                plot_data = df_filtered[x_axis].value_counts().reset_index()
                plot_data.columns = [x_axis, 'Count']
                
                if color_by != 'لا شيء' and color_by in df_filtered.columns:
                    plot_data = df_filtered.groupby([x_axis, color_by]).size().reset_index()
                    plot_data.columns = [x_axis, color_by, 'Count']
                    
                    fig = px.bar(
                        plot_data,
                        x=x_axis,
                        y='Count',
                        color=color_by,
                        title=f"توزيع البيانات حسب {x_axis}"
                    )
                else:
                    fig = px.bar(
                        plot_data,
                        x=x_axis,
                        y='Count',
                        title=f"توزيع البيانات حسب {x_axis}"
                    )
            else:
                if color_by != 'لا شيء':
                    fig = px.scatter(
                        df_filtered,
                        x=x_axis,
                        y=y_axis,
                        color=color_by,
                        title=f"{y_axis} مقابل {x_axis}"
                    )
                else:
                    fig = px.scatter(
                        df_filtered,
                        x=x_axis,
                        y=y_axis,
                        title=f"{y_axis} مقابل {x_axis}"
                    )
            
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.header("📥 خيارات التصدير")
    
    st.info("""
    يمكنك تصدير البيانات المصفاة إلى عدة صيغ مختلفة.
    اختر الصيغة المناسبة واحفظ البيانات على جهازك.
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 📄 Excel")
        st.markdown("صيغة جدول بيانات متقدمة")
        
        # زر التصدير إلى Excel
        if st.button("💾 تصدير إلى Excel", use_container_width=True):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_filtered.to_excel(writer, index=False, sheet_name='Data')
            excel_data = output.getvalue()
            
            b64 = base64.b64encode(excel_data).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="data_export.xlsx">📥 انقر للتحميل</a>'
            st.markdown(href, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 📊 CSV")
        st.markdown("صيغة نصية بسيطة")
        
        # زر التصدير إلى CSV
        if st.button("📊 تصدير إلى CSV", use_container_width=True):
            csv_data = df_filtered.to_csv(index=False, encoding='utf-8-sig')
            b64 = base64.b64encode(csv_data.encode('utf-8-sig')).decode()
            href = f'<a href="data:text/csv;charset=utf-8-sig;base64,{b64}" download="data_export.csv">📥 انقر للتحميل</a>'
            st.markdown(href, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 📝 JSON")
        st.markdown("صيغة تبادل بيانات")
        
        # زر التصدير إلى JSON
        if st.button("🔤 تصدير إلى JSON", use_container_width=True):
            json_data = df_filtered.to_json(orient='records', indent=2, force_ascii=False)
            b64 = base64.b64encode(json_data.encode('utf-8')).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="data_export.json">📥 انقر للتحميل</a>'
            st.markdown(href, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # إحصائيات التصدير
    st.markdown("### 📈 ملخص البيانات المصدَّرة")
    st.write(f"**عدد السجلات:** {len(df_filtered):,}")
    st.write(f"**عدد الأعمدة:** {len(df_filtered.columns)}")
    st.write(f"**الأعمدة:** {', '.join(df_filtered.columns.tolist())}")
    
    # معاينة البيانات قبل التصدير
    with st.expander("👁️ معاينة البيانات قبل التصدير"):
        st.dataframe(df_filtered.head(10), use_container_width=True)

# تذييل الصفحة
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>📋 نظام عرض بيانات السجل التقني | إصدار 1.0</p>
    <p>تم التطوير باستخدام Streamlit | للاستخدام التقني والتحليلي</p>
</div>
""", unsafe_allow_html=True)
