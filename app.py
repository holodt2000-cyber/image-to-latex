from flask import Flask, render_template, request, jsonify
import os
import re
import base64
from openai import OpenAI
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# Настройка папки для загрузок (адаптация под Render)
app.config['UPLOAD_FOLDER'] = '/tmp' if os.environ.get('RENDER') else 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Инициализация клиента
client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# --- ПРОМПТЫ ---
SYSTEM_PROMPT = r"""
Ты — узкоспециализированный ИИ-ассистент по переводу физических схем в код LaTeX/TikZ. 

1. ГЕОМЕТРИЧЕСКАЯ ЛОГИКА:
- СНАЧАЛА определи координаты поверхности. Пример: (0,0) -- (0,3) -- (3,3).
- ШТРИХОВКА: Используй \fill[pattern=north west lines] для фигур ПОД линией поверхности.
- ЗАПРЕТ: Не используй `rectangle` для поверхностей.

2. ПРАВИЛА ПОЗИЦИОНИРОВАНИЯ:
- ТЕЛА: Используй `\node[anchor=south]`.
- ТЕЛА НА СКЛОНЕ: Используй библиотеку `calc`: `at ($(A)!0.5!(B)$)`.
- СТРЕЛКИ: Рисуй векторы из центров (`node.center`).

3. ТЕХНИЧЕСКИЙ СТЭК:
- ПРЕАМБУЛА: \usetikzlibrary{arrows.meta, patterns, calc}.
- ТЕКСТ: Кириллицу пиши в фигурных скобках {груз}.

4. ОГРАНИЧЕНИЯ:
- Начинай СРАЗУ с \documentclass. Без Markdown разметки.
"""

VISION_PROMPT = r"""
Проанализируй физическую схему и составь техническое описание для TikZ.
Опиши: 
1. Линии поверхности (координаты).
2. Положение объектов (бруски, блоки).
3. Направление сил (стрелок).
4. Текстовые метки.
Пиши только сухие геометрические факты.
"""

# --- МОДЕЛИ ---
VISION_MODELS = [
    "google/gemini-flash-1.5-8b:free",
    "meta-llama/llama-3.2-11b-vision-instruct:free",
    "google/gemini-2.0-flash-exp:free"
]

CODER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "qwen/qwen-2.5-72b-instruct:free"
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

    vision_success = False
    coder_success = False
    description = ""
    latex_code = ""

    try:
        print(f"DEBUG: Начало обработки {filename}")
        file.save(filepath)
        
        with open(filepath, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode('utf-8')

        # ШАГ 1: Распознавание (Vision)
        for v_model in VISION_MODELS:
            try:
                print(f"DEBUG: Пробую Vision через {v_model}")
                vision_response = client.chat.completions.create(
                    model=v_model,
                    extra_headers={
                        "HTTP-Referer": "http://localhost:5000",
                        "X-Title": "TikZ Converter",
                    },
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
                if description and len(description) > 10:
                    vision_success = True
                    break
            except Exception as e:
                print(f"DEBUG: Ошибка Vision ({v_model}): {e}")
                continue

        if not vision_success:
            return jsonify({'error': "Все Vision-модели сейчас под лимитом (429)."}), 503

        # ШАГ 2: Генерация TikZ кода
        for c_model in CODER_MODELS:
            try:
                print(f"DEBUG: Пробую Кодинг через {c_model}")
                final_response = client.chat.completions.create(
                    model=c_model,
                    extra_headers={
                        "HTTP-Referer": "http://localhost:5000",
                        "X-Title": "TikZ Converter",
                    },
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Напиши TikZ код по описанию:\n{description}"}
                    ],
                    temperature=0.0,
                    timeout=50
                )
                
                content = final_response.choices[0].message.content
                if content and r"\documentclass" in content:
                    latex_code = content
                    coder_success = True
                    break
            except Exception as e:
                print(f"DEBUG: Ошибка Coder ({c_model}): {e}")
                continue

        if not coder_success:
            return jsonify({'error': 'Модели-кодеры перегружены. Попробуйте снова.'}), 503

        # --- ПОСТОБРАБОТКА ---
        # Удаляем Markdown обертки
        latex_code = re.sub(r'^```latex\s*|```', '', latex_code, flags=re.MULTILINE)
        
        # Обрезаем лишнее после документа
        if r"\end{document}" in latex_code:
            latex_code = latex_code[:latex_code.find(r"\end{document}") + 14]

        # Гарантируем наличие библиотек
        required_lib = r"\usetikzlibrary{arrows.meta, patterns, calc}"
        if required_lib not in latex_code:
            latex_code = latex_code.replace(r"\begin{document}", required_lib + "\n" + r"\begin{document}")
            
        # Убираем возможный мусор в начале
        if r"\documentclass" in latex_code:
            latex_code = latex_code[latex_code.find(r"\documentclass"):]

        return jsonify({'success': True, 'latex': latex_code.strip()})

    except Exception as e:
        print(f"DEBUG: Критическая ошибка: {e}")
        return jsonify({'error': f"Ошибка сервера: {str(e)}"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)