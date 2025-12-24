from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import cv2
import numpy as np
import io
import processor
import os
from PIL import Image
import base64
import json
from detector import LicensePlateDetector

app = Flask(__name__)
CORS(app)
import sys

# Force flush of stdout to capture logs in real-time
sys.stdout.reconfigure(line_buffering=True)

# Initialize Detector
# user can replace yolov8n.pt with a fine-tuned model path if available
detector = LicensePlateDetector(model_path='yolov8n.pt')

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/detect', methods=['POST'])
def detect_plate():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    file = request.files['image']
    try:
        pil_image = Image.open(file.stream).convert('RGB')
        image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        points = detector.detect(image)
        
        if points:
            return jsonify({"points": points, "detected": True})
        else:
            return jsonify({"points": [], "detected": False})
            
    except Exception as e:
        print(f"Error in detection: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/process', methods=['POST'])
def process_image():
    # print("Files:", request.files)
    # print("Form:", request.form)
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    file = request.files['image']
    points_str = request.form.get('points')
    
    if not points_str:
        return jsonify({"error": "No points provided"}), 400

    try:
        points_list = json.loads(points_str)
    except:
        return jsonify({"error": "Invalid points format"}), 400

    try:
        pil_image = Image.open(file.stream).convert('RGB')
        image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    except Exception as e:
        return jsonify({"error": f"Server error processing image: {str(e)}"}), 500

    # Parse parameters
    width_scale = float(request.form.get('scale', 1.0))
    aspect_ratio_val = request.form.get('aspect_ratio')
    aspect_ratio = float(aspect_ratio_val) if aspect_ratio_val and aspect_ratio_val != 'null' else None
    
    # Advanced Debug Params
    threshold_val = request.form.get('threshold')
    threshold = int(threshold_val) if threshold_val else -1 # -1 means auto/default
    
    rotation_val = request.form.get('rotation')
    rotation = float(rotation_val) if rotation_val else 0.0
    
    morph_op = request.form.get('morph_op') # 'dilation', 'erosion', 'none'
    kernel_size = int(request.form.get('kernel_size', 1))

    # Process
    try:
        processed_img, extracted_text, enhanced_img, ocr_details = processor.process_license_plate(
            image, 
            points_list, 
            width_scale=width_scale, 
            aspect_ratio=aspect_ratio,
            threshold=threshold,
            rotation=rotation,
            morph_op=morph_op,
            kernel_size=kernel_size
        )
        
        # Encode result (Warped RGB)
        _, img_encoded = cv2.imencode('.jpg', processed_img)
        b64_img = base64.b64encode(img_encoded).decode('utf-8')

        # Encode enhanced (Binary/Grayscale) for debug
        _, enhanced_encoded = cv2.imencode('.jpg', enhanced_img)
        b64_enhanced = base64.b64encode(enhanced_encoded).decode('utf-8')
        
        return jsonify({
            "image": f"data:image/jpeg;base64,{b64_img}",
            "enhanced_image": f"data:image/jpeg;base64,{b64_enhanced}",
            "text": extracted_text,
            "ocr_details": ocr_details
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

from video_processor import VideoProcessor
video_proc = VideoProcessor(detector)

@app.route('/process_video', methods=['POST'])
def process_video_endpoint():
    if 'video' not in request.files:
        return jsonify({"error": "No video provided"}), 400
    
    file = request.files['video']
    
    # Save temp file
    import tempfile
    fd, path = tempfile.mkstemp(suffix='.mp4')
    try:
        with os.fdopen(fd, 'wb') as tmp:
            file.save(tmp)
        
        # Process
        result = video_proc.process_video(path)
        
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        # Cleanup
        if os.path.exists(path):
            os.remove(path)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
