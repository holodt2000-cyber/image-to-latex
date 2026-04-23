from flask import Flask, render_template, request, jsonify
import os
import re
import base64
import traceback
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

# --- МОДЕЛИ (Free) ---
VISION_MODELS = [
    "google/gemini-flash-1.5-8b:free",
    "meta-llama/llama-3.2-11b-vision-instruct:free",
    "google/gemma-3-27b-it:free",
    "google/gemma-3-4b-it:free",
    "google/gemma-3n-e4b-it:free",
    "qwen/qwen3-coder:free",
    "openai/gpt-oss-120b:free"

]

CODER_MODELS = [
    "qwen/qwen3-coder:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free"
]

# Промпты (оставим те же, они у тебя хорошие)
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


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_image():
    # 1. Базовые проверки
    if 'image' not in request.files:
        return jsonify({'error': 'Файл не получен'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    last_error = "Неизвестная ошибка"

    try:
        file.save(filepath)
        with open(filepath, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode('utf-8')

        # ШАГ 1: VISION (Распознавание)
        description = ""
        for v_model in VISION_MODELS:
            try:
                print(f"DEBUG: Пробую Vision модель {v_model}")
                response = client.chat.completions.create(
                    model=v_model,
                    extra_headers={
                        "HTTP-Referer": "https://render.com", 
                        "X-Title": "TikZ Tool",
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
                description = response.choices[0].message.content
                if description:
                    print(f"DEBUG: Vision SUCCESS ({v_model})")
                    break
            except Exception as e:
                last_error = f"Vision ({v_model}) failed: {str(e)}"
                print(f"DEBUG ERROR: {last_error}")
                continue

        if not description:
            return jsonify({'error': f"Ошибка на этапе зрения: {last_error}"}), 503

        # ШАГ 2: CODER (Генерация кода)
        latex_code = ""
        for c_model in CODER_MODELS:
            try:
                print(f"DEBUG: Пробую Coder модель {c_model}")
                response = client.chat.completions.create(
                    model=c_model,
                    extra_headers={
                        "HTTP-Referer": "https://render.com",
                        "X-Title": "TikZ Tool",
                    },
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Создай TikZ код по описанию:\n{description}"}
                    ],
                    temperature=0.1,
                    timeout=45
                )
                content = response.choices[0].message.content
                if content and r"\documentclass" in content:
                    latex_code = content
                    print(f"DEBUG: Coder SUCCESS ({c_model})")
                    break
            except Exception as e:
                last_error = f"Coder ({c_model}) failed: {str(e)}"
                print(f"DEBUG ERROR: {last_error}")
                continue

        if not latex_code:
            return jsonify({'error': f"Ошибка на этапе кода: {last_error}"}), 503

        # Очистка результата
        latex_code = re.sub(r'^```latex\s*|```', '', latex_code, flags=re.MULTILINE)
        if r"\documentclass" in latex_code:
            latex_code = latex_code[latex_code.find(r"\documentclass"):]

        return jsonify({'success': True, 'latex': latex_code.strip()})

    except Exception as e:
        # Это поймает ошибки самого Python (например, проблемы с файловой системой)
        error_trace = traceback.format_exc()
        print(f"CRITICAL:\n{error_trace}")
        return jsonify({'error': f"Критический сбой: {str(e)}"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)