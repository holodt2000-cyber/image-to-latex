from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from PIL import Image
from pix2tex.cli import LatexOCR

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize LaTeX OCR model
model = None

def get_model():
    global model
    if model is None:
        model = LatexOCR()
    return model

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # TODO: Integrate LaTeX OCR model here
            latex_code = convert_to_latex(filepath)

            return jsonify({
                'success': True,
                'latex': latex_code
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)

    return jsonify({'error': 'Invalid file type'}), 400

def convert_to_latex(image_path):
    """Convert image to LaTeX using OCR model"""
    try:
        img = Image.open(image_path)
        model = get_model()
        latex_code = model(img)
        return latex_code
    except Exception as e:
        raise Exception(f"Failed to convert image: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
