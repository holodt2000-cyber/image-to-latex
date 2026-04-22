from flask import Flask, render_template, request, jsonify
import os
import re
import base64
from openai import OpenAI  # Используем стандарт OpenAI
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = r"""
Ты — эксперт по технической графике TikZ. Твоя задача: преобразовать визуальный эскиз в математически точный код LaTeX.

ПРАВИЛА ГЕНЕРАЦИИ:
1. КАРКАС: Сначала определи ключевые точки через `\coordinate`. Строй все элементы схемы относительно этих точек. Это исключит геометрические разрывы.
2. СЛОИ: 
   - 1. Штриховка и заливка (`pattern`, `fill`).
   - 2. Основные линии и контуры (`draw`).
   - 3. Объекты, стрелки и надписи (`node`).
3. ГЕОМЕТРИЯ: Для объектов на наклонных линиях используй `anchor` и `rotate`, чтобы обеспечить их плотное прилегание к поверхности.
4. ПРЕМБУЛА: Всегда включай [T2A]{fontenc}, [utf8]{inputenc}, [russian]{babel} и библиотеки {arrows.meta, patterns, calc}.
5. ОФОРМЛЕНИЕ: Выноси настройки цвета и типов линий в `\tikzset`. Используй Stealth-стрелки.

ФОРМАТ ОТВЕТА:
- СТРОГО: Начинай ответ сразу с \documentclass[tikz]{standalone}.
- СТРОГО: Никакого Markdown-оформления (без кавычек ```).
- Только чистый, готовый к компиляции код.
- Сохраняй язык надписей с эскиза.
# Дополнение к блоку ГЕОМЕТРИЯ:
- ЗАПРЕЩЕНО использовать сложные вычисления точек типа `intersection of`. 
- Используй только простые координаты: (0,0), (3,3) и т.д.
- ЗАПРЕЩЕНО добавлять элементы, которых нет на эскизе (оси координат, пружины, лишние пунктирные линии).
- Если видишь платформу (ступеньку) — рисуй её как `(0,0) -- (0,H) -- (L,H) -- (L+S, 0)`.
- Текст подписей пиши в `\node`, НЕ используя математический режим $...$ для обычных слов (пиши {брусок}, а не {$брусок$}).
"""







app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp' if os.environ.get('RENDER') else 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Инициализация Groq
client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# АКТУАЛЬНАЯ МОДЕЛЬ 2026
MODEL_ID = "google/gemini-flash-1.5-8b:free"
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
            temperature=0.0 # Для точности кода
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