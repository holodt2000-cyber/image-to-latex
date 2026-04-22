from flask import Flask, render_template, request, jsonify
import os
import re
import base64
from openai import OpenAI  # Используем стандарт OpenAI
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = r"""
Ты — ведущий инженер по визуализации в LaTeX/TikZ. Твоя задача: конвертировать технический эскиз в безупречный, математически обоснованный код.

СТРАТЕГИЯ ГЕНЕРАЦИИ:
1. ПРЕМБУЛА И СТИЛИ:
   - Всегда включай пакеты: T2A, inputenc(utf8), babel(russian), tikz.
   - Подключай библиотеки: arrows.meta, patterns, calc, positioning.
   - Используй `\tikzset` для создания стилей объектов (например, block/.style={draw, fill=orange}, ground/.style={pattern=north west lines}). Это позволит отделять геометрию от оформления.

2. МАТЕМАТИЧЕСКАЯ ЛОГИКА:
   - ВМЕСТО относительных координат используй именованные узлы: `\coordinate (A) at (x,y);`.
   - Для объектов на наклонных поверхностях НЕ гадай угол. Используй библиотеку `calc` или вычисляй наклон через координаты опорных точек, чтобы объект плотно прилегал к поверхности.
   - Соблюдай иерархию: сначала рисуй фон и заштрихованные области, затем основные линии, в конце — объекты и подписи.

3. ВИЗУАЛЬНЫЙ ФИЛЬТР:
   - Игнорируй края бумаги, тени, пятна и посторонние артефакты.
   - Если на эскизе есть штриховка, она ОБЯЗАТЕЛЬНО должна быть реализована через `pattern`.

4. ФОРМАТ ВЫХОДА:
   - Выдавай ТОЛЬКО чистый код LaTeX внутри \documentclass[tikz]{standalone}.
   - СТРОГО ЗАПРЕЩЕНО использовать Markdown-оформление (```latex ... ```). Начни сразу с \documentclass.
   - Сохраняй оригинальный язык надписей (кириллицу).

Твой код должен быть готов к немедленной компиляции в MiKTeX/Texmaker без ручных правок.
"""







app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp' if os.environ.get('RENDER') else 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Инициализация Groq
client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# АКТУАЛЬНАЯ МОДЕЛЬ 2026
MODEL_ID = "meta-llama/llama-4-scout-17b-16e-instruct"
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

    try:
        file.save(filepath)
        
        # Кодируем в base64 для передачи в Groq
        with open(filepath, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode('utf-8')

        # Запрос к Groq
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Преобразуй это изображение в экспертный код LaTeX/TikZ. Верни ТОЛЬКО код."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ],
                }
            ],
            temperature=0.1 # Для точности кода
        )

        latex_code = response.choices[0].message.content
        
        # Очистка от Markdown
        latex_code = re.sub(r'^```latex\s*', '', latex_code, flags=re.MULTILINE)
        latex_code = re.sub(r'```$', '', latex_code, flags=re.MULTILINE)

        return jsonify({'success': True, 'latex': latex_code.strip()})

    except Exception as e:
        return jsonify({'error': f"Ошибка Groq: {str(e)}"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)