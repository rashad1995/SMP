import os, io, json, pandas as pd
from flask import Flask, render_template, request, jsonify, session
from groq import Groq
import docx  # لملفات الورد
import fitz  # لملفات الـ PDF

app = Flask(__name__)
app.secret_key = "strategic_pro_secret_2026"

# ضع مفتاح Groq الخاص بك هنا
client = Groq(api_key="YOUR_GROQ_API_KEY")

def analyze_file(file):
    filename = file.filename.lower()
    ext = filename.split('.')[-1]
    
    try:
        # 1. ملفات الجداول (CSV, Excel)
        if ext in ['csv', 'xlsx', 'xls']:
            df = pd.read_csv(file) if ext == 'csv' else pd.read_excel(file)
            summary = df.describe(include='all').iloc[:, :10].to_string() # نأخذ أول 10 أعمدة للسرعة
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            # بناء بيانات الهيستوغرام لأول عمود رقمي يواجهنا
            chart_data = None
            if numeric_cols:
                col = numeric_cols[0]
                # حساب التوزيع التكراري
                counts, bins = pd.cut(df[col].dropna(), bins=10, retbins=True, labels=False, duplicates='drop')
                counts = df[col].dropna().groupby(counts).count()
                chart_data = {
                    "labels": [f"الفئة {i+1}" for i in range(len(counts))],
                    "values": counts.tolist(),
                    "column": col
                }
            return f"DATA_TYPE: Numeric\nStats Summary:\n{summary}", chart_data

        # 2. ملفات الورد (DOCX)
        elif ext == 'docx':
            doc = docx.Document(file)
            text = "\n".join([p.text for p in doc.paragraphs])
            return f"DATA_TYPE: Textual (Word)\nContent:\n{text[:7000]}", None

        # 3. ملفات الـ PDF
        elif ext == 'pdf':
            doc = fitz.open(stream=file.read(), filetype="pdf")
            text = " ".join([page.get_text() for page in doc])
            return f"DATA_TYPE: Textual (PDF)\nContent:\n{text[:7000]}", None

        # 4. الصور (JPG, PNG)
        elif ext in ['jpg', 'jpeg', 'png']:
            return "DATA_TYPE: Image\nTask: تحليل بصري استراتيجي شامل.", None

    except Exception as e:
        return f"Error: {str(e)}", None
    return "Unsupported Format", None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        file = request.files.get('file')
        lang = request.form.get('lang', 'Arabic')
        content, chart_info = analyze_file(file)
        
        # البرومبت الاستراتيجي المحسن
        prompt = f"""
        Role: Senior Strategy & Data Consultant.
        Language: {lang}.
        Formatting: Use [RED_TITLE] for titles and [BLUE_HEADER] for section headers.
        
        Tasks:
        1. [RED_TITLE] تقرير التحليل الاستراتيجي المعمق [/RED_TITLE]
        2. [BLUE_HEADER] 1. توصيف البيانات المُدخلة [/BLUE_HEADER]
        3. [BLUE_HEADER] 2. النتائج التحليلية والرؤى [/BLUE_HEADER]
           - إذا كانت أرقام: حلل القيم الإحصائية والتوزيع.
           - إذا كان نص: قدم ملخصاً تنفيذياً للنقاط الأساسية.
           - إذا كانت صورة: قدم تحليلاً للمحتوى البصري.
        4. [BLUE_HEADER] 3. التوصيات الاستراتيجية [/BLUE_HEADER]: خطوات عملية مبنية على التحليل.

        Input Data: {content}
        """
        
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.2
        )
        report = res.choices[0].message.content
        session['context'], session['report'], session['lang'] = content, report, lang
        return jsonify({'report': report, 'chart': chart_info})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json.get('query')
    system_prompt = f"""You are a Report Assistant. Answer ONLY based on:
    Report: {session.get('report')}
    Data: {session.get('context')}
    Language: {session.get('lang', 'Arabic')}. If unrelated, say: "أنا مختص بالتقرير فقط"."""
    
    res = client.chat.completions.create(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}],
        model="llama-3.3-70b-versatile"
    )
    return jsonify({'answer': res.choices[0].message.content})

if __name__ == '__main__':
    app.run(debug=True)
