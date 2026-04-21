from flask import Flask, render_template, request, jsonify
import os
import re  # ДОБАВЛЕНО: Без этого re.sub выдает ошибку!
from werkzeug.utils import secure_filename
import base64
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Загружаем переменные
load_dotenv()

app = Flask(__name__)
# Render использует временную папку /tmp для записи, если нет постоянного диска
app.config['UPLOAD_FOLDER'] = '/tmp' if os.environ.get('RENDER') else 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Инициализация клиента
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
gemini_client = None

if GEMINI_API_KEY:
    # Важно: Для Render не указываем никакие прокси!
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    print("ВНИМАНИЕ: Ключ API не найден.")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_image():
    if not gemini_client:
        return jsonify({'error': 'API Gemini не настроен. Добавьте ключ в .env'}), 500

    if 'image' not in request.files:
        return jsonify({'error': 'Изображение не предоставлено'}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            file.save(filepath)
            
            # Основной вызов конвертации через Gemini
            latex_code = convert_with_gemini_max(filepath)

            return jsonify({
                'success': True,
                'latex': latex_code
            })
        except Exception as e:
            return jsonify({'error': f"Ошибка сервера: {str(e)}"}), 500
        finally:
            # Очистка загруженного файла
            if os.path.exists(filepath):
                os.remove(filepath)

    return jsonify({'error': 'Недопустимый тип файла'}), 400


def convert_with_gemini_max(image_path):
    """
    Конвертирует изображение в ультимативный, многофункциональный векторный TikZ
    используя Gemini 2.5 Pro (стандарт апреля 2026).
    """
    
    # Выбираем PRO модель для максимального качества распознавания и кодинга
    model_id = "gemini-2.0-flash"
    
    # Читаем изображение как байты
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # УЛЬТИМАТИВНЫЙ ПРОМПТ для векторной графики и всех функций
    prompt = r"""
    Проанализируй это изображение и преобразуй его в КРАЙНЕ ВЫСОКОКЛАССНЫЙ, 
    полностью ВЕКТОРНЫЙ код LaTeX/TikZ.

    Твоя цель — создать код, который выглядит так, будто его написал эксперт по TikZ, 
    а не просто автоматический конвертер. Используй ВСЕ ВОЗМОЖНЫЕ функции TikZ.

    ТРЕБОВАНИЯ К ВЕКТОРНОЙ ГРАФИКЕ И ФУНКЦИЯМ:

    1. СТРУКТУРА И СТИЛИ (ЭТО ВАЖНО):
       - Не пиши стили (цвет, толщину линий, форму) внутри каждой команды \\draw.
       - Вместо этого, определи глобальные стили в начале окружения \\begin{tikzpicture}[...].
       - Например: [my_block/.style={rectangle, draw=blue, fill=blue!10, rounded corners}, connection/.style={->, thick, >=Stealth}].
       - Используй эти стили для элементов: \\node[my_block] (n1) {...};

    2. ЦВЕТА И ЗАЛИВКА:
       - Точно определи RGB цвета элементов.
       - Глобально определи цвета через \\definecolor{color_name}{RGB}{R,G,B}.
       - Активно используй прозрачность (opacity) и градиенты (shading), если они есть на оригинале.
       - Используй закрашенные области (\\fill) вместо обводки (\\draw) там, где это соответствует оригиналу.

    3. ГЕОМЕТРИЯ И РАСПОЛОЖЕНИЕ:
       - Используй относительные координаты (например, (node1.east) -- (node2.west)) вместо абсолютных (0,0).
       - Задействуй библиотеку `positioning` (например, `right=of node1`).
       - Для сложных путей используй `calc` библиотеку (например, `($ (n1.east)!.5!(n2.west) $)`).

    4. СТРЕЛКИ И СОЕДИНЕНИЯ:
       - Используй библиотеку `arrows.meta` для современных наконечников стрелок (например, `{-Stealth[scale=1.2]}`).
       - Используй ортогональные соединения ( |- или -| ), если линии прямые.

    5. ТЕКСТ И МАТЕМАТИКА:
       - Весь текст оформляй через \\node.
       - Определи шрифт и размер текста в стилях нод.
       - Если текст содержит формулы, ОБЯЗАТЕЛЬНО используй математический режим $...$.

    6. БИБЛИОТЕКИ:
       - Включи в преамбулу все необходимые библиотеки: positioning, shapes.geometric, arrows.meta, calc, backgrounds, shadows (если есть тени).

    ВЕРНИ ТОЛЬКО ЧИСТЫЙ КОД LaTeX, готовый к компиляции (начиная с \documentclass). Без пояснений.
    """

    # Вызов Gemini API
    response = gemini_client.models.generate_content(
        model=model_id,
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        ]
    )

    latex_code = response.text

    # Очистка кода от Markdown-обертки ```latex ... ```
    latex_code = re.sub(r'^```latex\s*', '', latex_code, flags=re.MULTILINE)
    latex_code = re.sub(r'```$', '', latex_code, flags=re.MULTILINE)

    return latex_code.strip()


if __name__ == '__main__':
    # Перед запуском убедитесь, что создали папку templates и файл index.html в ней.
    # Также создайте .env файл с ключом GEMINI_API_KEY.
    app.run(debug=True, host='0.0.0.0', port=5000)