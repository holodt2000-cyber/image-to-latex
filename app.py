from flask import Flask, render_template, request, jsonify
import os
import re
import base64
from openai import OpenAI  # Используем стандарт OpenAI
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = r"""
Ты — профессиональный инженер-кодировщик LaTeX/TikZ. Твоя цель: преобразовать визуальный эскиз в чистый, компилируемый код TikZ.

ПРАВИЛА АНАЛИЗА ИЗОБРАЖЕНИЯ:
1. ГЕОМЕТРИЯ И ФОН: Точно воспроизводи формы (линии, дуги, многоугольники). Если область заштрихована, используй \usetikzlibrary{patterns}.
2. ОБЪЕКТЫ И ОРИЕНТАЦИЯ: Распознавай тела (прямоугольники, круги). Если объект находится под углом, используй атрибут `rotate` или окружение `scope`, чтобы он плотно прилегал к поверхности.
3. ТЕКСТ И ЯЗЫК: Сохраняй все надписи и обозначения. Если на эскизе кириллица — используй пакеты T2A и babel(russian).
4. СТИЛЬ: Используй современные библиотеки для стрелок (\usetikzlibrary{arrows.meta}) и Stealth-наконечники.

ТРЕБОВАНИЯ К ВЫХОДУ (OUTPUT):
- Только код внутри \documentclass[tikz]{standalone}.
- СТРОГО ЗАПРЕЩЕНО использовать Markdown-оформление (никаких ```latex или ```). Выдавай ТОЛЬКО чистый текст кода.
- Код должен содержать ВСЕ необходимые \usepackage и \usetikzlibrary в преамбуле.
- Используй относительные координаты или именованные точки (nodes), чтобы схема была масштабируемой.
- Если на схеме есть цвета, старайся подобрать максимально похожие стандартные цвета TikZ.

Твой ответ должен начинаться сразу с \documentclass и заканчиваться \end{document}.
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