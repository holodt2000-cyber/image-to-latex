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
    """Convert image to TikZ code for Overleaf"""
    img = None
    try:
        # Open and process image
        img = Image.open(image_path)

        # Convert to grayscale
        img_gray = img.convert('L')

        # Get image dimensions
        width, height = img.size

        # Sample some pixels to create a simple representation
        # Reduce resolution for TikZ (too many points will be slow)
        sample_width = min(width, 50)
        sample_height = min(height, 50)
        img_small = img_gray.resize((sample_width, sample_height), Image.Resampling.LANCZOS)

        # Create TikZ code with pixel-based shading
        tikz_code = f"""\\documentclass{{standalone}}
\\usepackage{{tikz}}

\\begin{{document}}
\\begin{{tikzpicture}}[x=0.1cm, y=0.1cm]

% Original image size: {width}x{height}px
% Sampled to: {sample_width}x{sample_height} for TikZ

"""

        # Generate rectangles for each pixel (grayscale)
        for y in range(sample_height):
            for x in range(sample_width):
                pixel_value = img_small.getpixel((x, y))
                # Convert to grayscale value (0=black, 255=white)
                gray_value = pixel_value / 255.0

                # Only draw darker pixels to reduce code size
                if gray_value < 0.9:
                    tikz_code += f"\\fill[black!{int((1-gray_value)*100)}] ({x},{sample_height-y-1}) rectangle ({x+1},{sample_height-y});\n"

        tikz_code += """
\\end{tikzpicture}
\\end{document}"""

        return tikz_code

    except Exception as e:
        raise Exception(f"Failed to convert image: {str(e)}")
    finally:
        if img:
            img.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
