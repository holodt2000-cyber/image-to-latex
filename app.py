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
1. КАРКАС: Определи ключевые точки через `\coordinate`. Соединяй их напрямую.
2. СЛОИ: 
   - Сначала штриховка (\fill[pattern=...]).
   - Затем контуры (\draw[thick]).
   - Затем объекты и подписи (\node).
3. ПРЕМБУЛА: СТРОГО используй только эти библиотеки: \usetikzlibrary{arrows.meta, patterns, calc}.
4. ГЕОМЕТРИЯ:
   - ЗАПРЕЩЕНО использовать `decoration` и пакет `decorations.pathmorphing`. 
   - НИКАКИХ пружин (snake/zigzag). Если видишь пружину — игнорируй или рисуй прямой линией.
   - Для тел используй `anchor=south`, чтобы они стояли НА линии.
   - Используй `\fill[pattern=north west lines, pattern color=gray]` для поверхностей.

ФОРМАТ ОТВЕТА:
- СТРОГО: Начинай ответ сразу с \documentclass[tikz]{standalone}.
- СТРОГО: Без Markdown-разметки (никаких ```latex).
- СТРОГО: Только чистый код.
- Текст подписей: пиши {брусок}, а не {$брусок$}.
- Математика: только для переменных типа {$H$}, {$v$}, {$m$}.
"""

# Очередь моделей: если первая занята, идем ко второй
MODELS_PRIORITY = [
    "google/gemma-3-27b-it:free",      # Приоритет 1 (лучшая)
    "google/gemma-3-12b-it:free",      # Приоритет 2
    "meta-llama/llama-3.2-11b-vision-instruct:free", # Приоритет 3 (очень стабильная)
    "google/gemini-flash-1.5-8b:free"  # Приоритет 4 (последний шанс)
]





app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp' if os.environ.get('RENDER') else 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Инициализация Groq
client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# АКТУАЛЬНАЯ МОДЕЛЬ 2026
MODEL_ID = "google/gemma-3-27b-it:free"
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

    # Инициализируем флаги ДО входа в цикл
    success = False
    latex_code = ""

    try:
        file.save(filepath)
        
        with open(filepath, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode('utf-8')

        # Цикл по моделям
        for model in MODELS_PRIORITY:
            try:
                print(f"Пробую модель: {model}...")
                response = client.chat.completions.create(
                    model=model,
                    extra_headers={
                        "HTTP-Referer": "https://render.com",
                        "X-Title": "TikZ Converter",
                    },
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"{SYSTEM_PROMPT}\n\nЗАДАНИЕ: Оцифруй это изображение в TikZ. Верни ТОЛЬКО код."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ],
                        }
                    ],
                    temperature=0.0,
                    timeout=30  
                )
                
                content = response.choices[0].message.content
                if content:
                    latex_code = content
                    success = True
                    print(f"Успех с моделью: {model}")
                    break 
                    
            except Exception as e:
                print(f"Модель {model} не справилась: {str(e)}")
                continue

        if not success:
            return jsonify({'error': 'Все бесплатные модели сейчас перегружены или недоступны.'}), 503

        # Очистка кода от Markdown-мусора (на случай, если модель проигнорировала промпт)
        latex_code = re.sub(r'^```latex\s*', '', latex_code, flags=re.MULTILINE)
        latex_code = re.sub(r'```$', '', latex_code, flags=re.MULTILINE)
        
        # Если модель добавила текст ДО \documentclass, обрезаем его
        if r"\documentclass" in latex_code:
            latex_code = latex_code[latex_code.find(r"\documentclass"):]

        return jsonify({'success': True, 'latex': latex_code.strip()})

    except Exception as e:
        return jsonify({'error': f"Критическая ошибка сервера: {str(e)}"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)