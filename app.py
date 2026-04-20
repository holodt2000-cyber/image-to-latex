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
    """Convert image to TikZ code using contour detection with colors and shape recognition"""
    try:
        # Read image with OpenCV
        img_cv = cv2.imread(image_path)

        # Get image dimensions
        height, width = img_cv.shape[:2]
        scale = 0.05  # Scale factor for TikZ coordinates

        # Convert to different color spaces
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)

        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # Find contours
        contours, hierarchy = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Start TikZ document
        tikz_code = f"""\\documentclass{{standalone}}
\\usepackage{{tikz}}
\\usepackage{{xcolor}}

\\begin{{document}}
\\begin{{tikzpicture}}[scale=1]

% Original image size: {width}x{height}px
% Vectorized with shape recognition and color detection

"""

        # Process each contour
        for i, contour in enumerate(contours):
            # Skip very small contours
            area = cv2.contourArea(contour)
            if area < 100:
                continue

            # Get contour color (average color inside contour)
            mask = np.zeros(gray.shape, np.uint8)
            cv2.drawContours(mask, [contour], 0, 255, -1)
            mean_color = cv2.mean(img_cv, mask=mask)
            b, g, r = int(mean_color[0]), int(mean_color[1]), int(mean_color[2])

            # Convert BGR to RGB and normalize
            color_rgb = f"{{rgb,255:red,{r};green,{g};blue,{b}}}"

            # Simplify contour
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Detect shape type
            shape_type, shape_params = detect_shape(approx, contour, scale, height)

            if shape_type:
                tikz_code += f"% Shape {i+1}: {shape_type}\n"
                tikz_code += f"\\draw[{color_rgb}, fill={color_rgb}, fill opacity=0.8] {shape_params};\n\n"
            else:
                # Draw as polygon if shape not recognized
                tikz_code += f"% Contour {i+1}\n\\draw[{color_rgb}, fill={color_rgb}, fill opacity=0.8, line width=0.5pt] "

                for j, point in enumerate(approx):
                    x = point[0][0] * scale
                    y = (height - point[0][1]) * scale

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

def detect_shape(approx, contour, scale, height):
    """Detect geometric shapes from contours"""
    vertices = len(approx)

    # Get bounding box
    x, y, w, h = cv2.boundingRect(contour)
    aspect_ratio = float(w) / h if h > 0 else 0

    # Convert coordinates
    def to_tikz(point):
        px = point[0][0] * scale
        py = (height - point[0][1]) * scale
        return px, py

    # Circle detection
    if vertices > 8:
        (cx, cy), radius = cv2.minEnclosingCircle(contour)
        area = cv2.contourArea(contour)
        circle_area = np.pi * (radius ** 2)

        if abs(area - circle_area) / circle_area < 0.2:  # 20% tolerance
            cx_tikz = cx * scale
            cy_tikz = (height - cy) * scale
            r_tikz = radius * scale
            return "circle", f"({cx_tikz:.2f},{cy_tikz:.2f}) circle ({r_tikz:.2f})"

    # Rectangle detection
    if vertices == 4:
        if 0.85 < aspect_ratio < 1.15:  # Square
            x1, y1 = to_tikz(approx[0])
            x2, y2 = to_tikz(approx[2])
            return "square", f"({x1:.2f},{y1:.2f}) rectangle ({x2:.2f},{y2:.2f})"
        else:  # Rectangle
            x1, y1 = to_tikz(approx[0])
            x2, y2 = to_tikz(approx[2])
            return "rectangle", f"({x1:.2f},{y1:.2f}) rectangle ({x2:.2f},{y2:.2f})"

    # Triangle detection
    if vertices == 3:
        p1, p2, p3 = [to_tikz(p) for p in approx]
        return "triangle", f"({p1[0]:.2f},{p1[1]:.2f}) -- ({p2[0]:.2f},{p2[1]:.2f}) -- ({p3[0]:.2f},{p3[1]:.2f}) -- cycle"

    # Line detection (2 vertices or very elongated shape)
    if vertices == 2 or (aspect_ratio > 5 or aspect_ratio < 0.2):
        if vertices >= 2:
            p1, p2 = to_tikz(approx[0]), to_tikz(approx[-1])
            return "line", f"({p1[0]:.2f},{p1[1]:.2f}) -- ({p2[0]:.2f},{p2[1]:.2f})"

    return None, None

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
