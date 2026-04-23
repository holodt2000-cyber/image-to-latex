from flask import Flask, render_template, request, jsonify
import os
import re
import base64
from openai import OpenAI
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp' if os.environ.get('RENDER') else 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

SYSTEM_PROMPT = r"""
Ты — узкоспециализированный ИИ-ассистент по переводу физических схем в код LaTeX/TikZ. 

1. ГЕОМЕТРИЧЕСКАЯ ЛОГИКА:
- СНАЧАЛА определи координаты поверхности. Пример: (0,0) -- (0,3) -- (3,3) -- (7,0) -- (10,0).
- ШТРИХОВКА: Используй \fill[pattern=north west lines] для замкнутой фигуры ПОД линией поверхности (включая "землю").
- ЗАПРЕТ: Не используй `rectangle` для поверхностей.

2. ПРАВИЛА ПОЗИЦИОНИРОВАНИЯ:
- ТЕЛА: Используй `\node[anchor=south]`.
- ТЕЛА НА СКЛОНЕ: Используй библиотеку `calc`: `at ($(A)!0.5!(B)$)`.
- СТРЕЛКИ: Рисуй векторы из центров (`node.center`) через `++(x,y)`.

3. ТЕХНИЧЕСКИЙ СТЭК:
- ПРЕАМБУЛА: \usetikzlibrary{arrows.meta, patterns, calc}.
- ТЕКСТ: Кириллицу пиши в скобках {брусок}.

4. ОГРАНИЧЕНИЯ:
- Начинай СРАЗУ с \documentclass. Никакой разметки ```.
- ЗАПРЕЩЕНО использовать `decorations` (snake/spring).
"""
VISION_PROMPT = r"""
Проанализируй физическую схему и составь техническое описание для построения её копии в TikZ.

СТРУКТУРА ОПИСАНИЯ:
1. ЛИНЕЙНАЯ ГЕОМЕТРИЯ: Перечисли последовательные точки излома поверхности. Опиши высоту и протяженность участков (плато, спуски, горизонтальные уровни).
2. ОБЪЕКТЫ: Перечисли все тела и укажите их положение относительно сегментов поверхности.
3. СИЛЫ И ВЕКТОРЫ: Опиши все стрелки, укажи их направление и точку начала относительно тел.
4. ТЕКСТОВЫЕ МЕТКИ: Укажи все буквенные и словесные обозначения, привязанные к объектам или размерам.
5. ЗАЛИВКА: Укажи границы областей, требующих штриховки.

Пиши сухими геометрическими фактами.
"""
# Модели для кодинга (текстовые)
CODER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.2-11b-vision-instruct:free"
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_image():
    if 'image' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    success = False
    latex_code = ""

    try:
        file.save(filepath)
        with open(filepath, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode('utf-8')

        # ШАГ 1: Описание (Vision)
        try:
            vision_response = client.chat.completions.create(
                model="google/gemini-flash-1.5-8b",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                timeout=30
            )
            description = vision_response.choices[0].message.content
        except Exception as e:
            return jsonify({'error': f"Ошибка распознавания (Vision): {str(e)}"}), 500

        # ШАГ 2: Генерация кода (Coder)
        for model in CODER_MODELS:
            try:
                print(f"Попытка кодинга с моделью: {model}")
                final_response = client.chat.completions.create(
                    model=model,
                    extra_headers={
                        "HTTP-Referer": "[https://render.com](https://render.com)",
                        "X-Title": "TikZ Converter Pipeline",
                    },
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Напиши TikZ код по этому описанию схемы:\n{description}"}
                    ],
                    temperature=0.0
                )
                
                content = final_response.choices[0].message.content
                if content and r"\documentclass" in content:
                    latex_code = content
                    success = True
                    break
            except Exception as e:
                print(f"Модель {model} не справилась: {e}")
                continue

        if not success:
            return jsonify({'error': 'Модели-кодеры перегружены.'}), 503

        # Очистка и доработка
        latex_code = re.sub(r'^```latex\s*|```', '', latex_code, flags=re.MULTILINE)
        
        required_preamble = r"\usetikzlibrary{arrows.meta, patterns, calc}"
        if required_preamble not in latex_code:
            latex_code = latex_code.replace(r"\begin{document}", required_preamble + "\n" + r"\begin{document}")
            
        if r"\documentclass" in latex_code:
            latex_code = latex_code[latex_code.find(r"\documentclass"):]

        return jsonify({'success': True, 'latex': latex_code.strip()})

    except Exception as e:
        return jsonify({'error': f"Критическая ошибка: {str(e)}"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)