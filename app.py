from flask import Flask, render_template, request, jsonify, Response
import os
import re
import base64
import io
import json
import time
from PIL import Image
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

# Отключаем системный прокси — иначе httpx рвёт соединение
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

app = Flask(__name__)

# Hugging Face Inference API (бесплатно)
HF_TOKEN = os.environ.get("HF_TOKEN")
MODEL_ID = os.environ.get("MODEL_ID", "Qwen/Qwen3.5-27B")

if not HF_TOKEN:
    print("ERROR: HF_TOKEN not found!")
    print("Get FREE token at: https://huggingface.co/settings/tokens")
else:
    print("HF Token: OK")

hf_client = InferenceClient(token=HF_TOKEN, timeout=180)

# Универсальный промпт для любых изображений
SYSTEM_PROMPT = r"""/no_think
You are a TikZ LaTeX expert. Your task: reproduce the image EXACTLY as TikZ code.

CRITICAL RULES:
1. ONLY reproduce what you see in the image. Do NOT add, invent, or embellish anything.
2. Do NOT add elements, labels, colors, or decorations that are not in the image.
3. If something is unclear, keep it simple rather than guessing.

CODE STRUCTURE (must compile with pdflatex):
- Start with \documentclass[tikz,border=10pt]{standalone}
- \usepackage{tikz}
- Include ALL needed \usetikzlibrary BEFORE \begin{document}
- \begin{document} ... \end{document} must be present
- Every \begin{...} must have a matching \end{...}
- Every { must have a matching }
- Use only standard TikZ packages (no custom or rare packages)

STYLE:
- Use >=Stealth for arrows (requires arrows.meta)
- Use pattern=north west lines for hatched areas (requires patterns)
- Keep code clean and well-indented

Output ONLY the complete, compilable LaTeX code. No markdown fences, no text before or after."""

def process_image(file):
    img = Image.open(file)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def clean_latex(code):
    code = re.sub(r'^```latex\s*', '', code, flags=re.MULTILINE)
    code = re.sub(r'^```\s*', '', code, flags=re.MULTILINE)
    code = re.sub(r'```$', '', code, flags=re.MULTILINE)

    if r'\documentclass' not in code and r'\begin{tikzpicture}' in code:
        code = r'''\documentclass[border=10pt]{standalone}
\usepackage{tikz}
\begin{document}
''' + code + r'''
\end{document}'''

    return code.strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'image' not in request.files:
        return jsonify({'error': 'No file'}), 400

    try:
        img_b64 = process_image(request.files['image'])
        instructions = request.form.get('instructions', '').strip()

        prompt_text = SYSTEM_PROMPT
        if instructions:
            prompt_text += f"\n\nADDITIONAL USER INSTRUCTIONS:\n{instructions}"

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]
            }
        ]

        def stream_one_request(msgs):
            """Один стрим-запрос, возвращает (текст, finish_reason)"""
            text_out = ""
            finish = None
            stream = hf_client.chat_completion(
                model=MODEL_ID,
                messages=msgs,
                max_tokens=8192,
                temperature=0.2,
                stream=True
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta
                text = getattr(delta, 'content', '') or ''
                if text:
                    text_out += text
                    yield text
                if getattr(choice, 'finish_reason', None):
                    finish = choice.finish_reason
            stream_one_request._finish = finish
            stream_one_request._text = text_out

        def is_complete(code):
            return r'\end{document}' in code

        def generate():
            """SSE стриминг с автопродолжением при обрезке"""
            full_content = ""
            MAX_CONTINUATIONS = 5

            # Первый запрос (с картинкой)
            for attempt in range(3):
                try:
                    print(f"  Attempt {attempt + 1}/3...")
                    yield f"data: {json.dumps({'status': 'Генерация кода...'})}\n\n"

                    for text in stream_one_request(messages):
                        full_content += text
                        yield f"data: {json.dumps({'chunk': text})}\n\n"
                    break

                except Exception as api_err:
                    err_str = str(api_err)
                    if "503" in err_str or "504" in err_str:
                        wait = 15 * (attempt + 1)
                        print(f"  Model loading, retry in {wait}s...")
                        yield f"data: {json.dumps({'status': f'Модель загружается, повтор через {wait}с...'})}\n\n"
                        time.sleep(wait)
                    else:
                        yield f"data: {json.dumps({'error': str(api_err)})}\n\n"
                        return
            else:
                yield f"data: {json.dumps({'error': 'Не удалось подключиться после 3 попыток'})}\n\n"
                return

            # Автопродолжение — если код обрезан, просим модель дописать
            continuation = 0
            while not is_complete(full_content) and continuation < MAX_CONTINUATIONS:
                continuation += 1
                print(f"  Continuation {continuation}/{MAX_CONTINUATIONS}...")
                yield f"data: {json.dumps({'status': f'Код обрезан, продолжаю генерацию ({continuation}/{MAX_CONTINUATIONS})...'})}\n\n"

                # Передаём картинку + историю: модель видит изображение и свой предыдущий ответ
                cont_messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": SYSTEM_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                        ]
                    },
                    {
                        "role": "assistant",
                        "content": full_content
                    },
                    {
                        "role": "user",
                        "content": "/no_think\nYour code was cut off. Continue EXACTLY from where you stopped. Output ONLY the remaining code."
                    }
                ]

                try:
                    for text in stream_one_request(cont_messages):
                        full_content += text
                        yield f"data: {json.dumps({'chunk': text})}\n\n"
                except Exception as e:
                    print(f"  Continuation error: {e}")
                    break

            clean_code = clean_latex(full_content)
            yield f"data: {json.dumps({'done': True, 'latex': clean_code})}\n\n"

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error: {str(e)}'}), 500

REFINE_PROMPT = r"""/no_think
You are a TikZ LaTeX expert. Modify the given code according to user instructions.

CRITICAL RULES:
1. Output the COMPLETE modified LaTeX code (not a diff, not partial).
2. ONLY change what the user asked for. Do NOT add or remove anything else.
3. Do NOT invent new elements, decorations, or embellishments.
4. The code MUST compile with pdflatex without errors.
5. Keep \documentclass[tikz,border=10pt]{standalone}
6. All \usetikzlibrary must be BEFORE \begin{document}
7. Every \begin{...} must have a matching \end{...}

Output ONLY the complete, compilable LaTeX code. No markdown fences, no text before or after."""

@app.route('/refine', methods=['POST'])
def refine():
    data = request.get_json()
    code = (data or {}).get('code', '').strip()
    instructions = (data or {}).get('instructions', '').strip()

    if not code:
        return jsonify({'error': 'Нет кода для исправления'}), 400
    if not instructions:
        return jsonify({'error': 'Укажите пожелания'}), 400

    try:
        messages = [
            {
                "role": "user",
                "content": f"{REFINE_PROMPT}\n\nHere is the current TikZ code:\n```\n{code}\n```\n\nUSER INSTRUCTIONS:\n{instructions}"
            }
        ]

        def stream_one_request(msgs):
            text_out = ""
            stream = hf_client.chat_completion(
                model=MODEL_ID,
                messages=msgs,
                max_tokens=8192,
                temperature=0.2,
                stream=True
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta
                text = getattr(delta, 'content', '') or ''
                if text:
                    text_out += text
                    yield text

        def is_complete(code):
            return r'\end{document}' in code

        def generate():
            full_content = ""
            MAX_CONTINUATIONS = 5

            for attempt in range(3):
                try:
                    yield f"data: {json.dumps({'status': 'Исправляю код...'})}\n\n"
                    for text in stream_one_request(messages):
                        full_content += text
                        yield f"data: {json.dumps({'chunk': text})}\n\n"
                    break
                except Exception as api_err:
                    err_str = str(api_err)
                    if "503" in err_str or "504" in err_str:
                        wait = 15 * (attempt + 1)
                        yield f"data: {json.dumps({'status': f'Модель загружается, повтор через {wait}с...'})}\n\n"
                        time.sleep(wait)
                    else:
                        yield f"data: {json.dumps({'error': str(api_err)})}\n\n"
                        return
            else:
                yield f"data: {json.dumps({'error': 'Не удалось подключиться после 3 попыток'})}\n\n"
                return

            continuation = 0
            while not is_complete(full_content) and continuation < MAX_CONTINUATIONS:
                continuation += 1
                yield f"data: {json.dumps({'status': f'Код обрезан, продолжаю ({continuation}/{MAX_CONTINUATIONS})...'})}\n\n"
                cont_messages = [
                    messages[0],
                    {"role": "assistant", "content": full_content},
                    {"role": "user", "content": "/no_think\nYour code was cut off. Continue EXACTLY from where you stopped. Output ONLY the remaining code."}
                ]
                try:
                    for text in stream_one_request(cont_messages):
                        full_content += text
                        yield f"data: {json.dumps({'chunk': text})}\n\n"
                except Exception as e:
                    break

            clean_code = clean_latex(full_content)
            yield f"data: {json.dumps({'done': True, 'latex': clean_code})}\n\n"

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error: {str(e)}'}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("Image to TikZ Converter — Hugging Face")
    print(f"Model: {MODEL_ID}")
    print(f"HF Token: {'OK' if HF_TOKEN else 'MISSING'}")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
