from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from PIL import Image
import cv2
import numpy as np

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
    """Convert image to TikZ code using contour detection"""
    img = None
    try:
        # Read image with OpenCV
        img_cv = cv2.imread(image_path)

        # Convert to grayscale
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Get image dimensions
        height, width = gray.shape
        scale = 0.1  # Scale factor for TikZ coordinates

        # Start TikZ document
        tikz_code = f"""\\documentclass{{standalone}}
\\usepackage{{tikz}}

\\begin{{document}}
\\begin{{tikzpicture}}[scale=1]

% Original image size: {width}x{height}px
% Vectorized using contour detection

"""

        # Convert contours to TikZ paths
        for i, contour in enumerate(contours):
            # Skip very small contours
            if len(contour) < 3:
                continue

            # Simplify contour to reduce points
            epsilon = 0.01 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Start path
            tikz_code += f"% Contour {i+1}\n\\draw[fill=black, line width=0.1pt] "

            # Add points
            for j, point in enumerate(approx):
                x = point[0][0] * scale
                y = (height - point[0][1]) * scale  # Flip Y coordinate

                if j == 0:
                    tikz_code += f"({x:.2f},{y:.2f})"
                else:
                    tikz_code += f" -- ({x:.2f},{y:.2f})"

            tikz_code += " -- cycle;\n\n"

        tikz_code += """\\end{tikzpicture}
\\end{document}"""

        return tikz_code

    except Exception as e:
        raise Exception(f"Failed to convert image: {str(e)}")
    finally:
        pass

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
