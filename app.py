import streamlit as st import pandas as pd import re

st.set_page_config(page_title="Logbook Analyzer", layout="wide")

st.title("📘 Logbook Data Analyzer") st.write("تطبيق بسيط لتحليل بيانات اللوج بوك وعرضها بشكل سهل")

uploaded_file = st.file_uploader("ارفع ملف اللوج بوك (txt أو csv)", type=["txt", "csv"])

@st.cache_data def load_txt(file): lines = file.read().decode("utf-8", errors="ignore").splitlines() data = [] for line in lines: # مثال parsing – عدله حسب شكل اللوج بوك عندك match = re.split(r"\s*,\s*|\s+", line) if len(match) >= 4: data.append(match) df = pd.DataFrame(data) return df

if uploaded_file: if uploaded_file.name.endswith(".csv"): df = pd.read_csv(uploaded_file) else: df = load_txt(uploaded_file)

st.success("تم تحميل البيانات بنجاح")

st.subheader("📊 نظرة عامة")
st.write(df.head())

st.subheader("ℹ️ معلومات عن الداتا")
st.write(df.describe(include="all"))

st.subheader("🔎 فلترة البيانات")
col = st.selectbox("اختار العمود", df.columns)
value = st.text_input("اكتب قيمة للبحث")

if value:
    filtered_df = df[df[col].astype(str).str.contains(value, case=False)]
    st.write(filtered_df)

st.subheader("⬇️ تحميل الداتا بعد التحليل")
csv = df.to_csv(index=False).encode('utf-8')
st.download_button("تحميل CSV", csv, "logbook_analysis.csv", "text/csv")

else: st.info("من فضلك ارفع ملف اللوج بوك علشان نبدأ التحليل")
