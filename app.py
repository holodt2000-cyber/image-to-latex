from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from PIL import Image
import subprocess
import tempfile

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

        try:
            file.save(filepath)
            latex_code = convert_to_latex(filepath)

            return jsonify({
                'success': True,
                'latex': latex_code
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            # Clean up uploaded file
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except PermissionError:
                # File still in use, will be cleaned up later
                pass

    return jsonify({'error': 'Invalid file type'}), 400

def convert_to_latex(image_path):
    """Convert image to TikZ code"""
    img = None
    try:
        # Open and process image
        img = Image.open(image_path)

        # Convert to grayscale
        img = img.convert('L')

        # Get image dimensions
        width, height = img.size

        # Create basic TikZ code with image dimensions
        tikz_code = f"""\\begin{{tikzpicture}}[scale=1]
% Image dimensions: {width}x{height}
% This is a simplified conversion
% For better results, use Inkscape with TikZ export or potrace

% You can include the image directly:
% \\node[anchor=south west,inner sep=0] at (0,0) {{\\includegraphics[width={width/100}cm]{{your-image.png}}}};

% Or trace it manually in TikZ
\\draw[thick] (0,0) rectangle ({width/100},{height/100});
\\node at ({width/200},{height/200}) {{Vectorize this image manually or use Inkscape}};

\\end{{tikzpicture}}"""

        return tikz_code

    except Exception as e:
        raise Exception(f"Failed to convert image: {str(e)}")
    finally:
        if img:
            img.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
