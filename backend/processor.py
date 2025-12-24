import cv2
import numpy as np
import threading

# Lazy load PaddleOCR to save memory on startup
_ocr_engine = None
ocr_lock = threading.Lock() 

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        from paddleocr import PaddleOCR
        # Initialize PaddleOCR
        # Disable angle classifier as per recommendation and to avoid overhead on rectified images
        _ocr_engine = PaddleOCR(use_angle_cls=False, lang='en')
    return _ocr_engine 

def order_points(pts):
    rect = np.zeros((4, 2), dtype = "float32")
    s = pts.sum(axis = 1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis = 1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def enhance_image(image, threshold=-1, morph_op='none', kernel_size=1):
    """
    Enhance image for OCR.
    threshold: int, -1 for auto (OTSU/Adaptive), 0-255 for manual
    morph_op: str, 'dilation', 'erosion', 'none'
    kernel_size: int, 1-5
    """
    # 1. Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # 2. Resize if too small
    h, w = gray.shape
    if h < 50:
        scale = 2.0
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # 3. Denoise
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    # 4. Thresholding
    if threshold is not None and threshold >= 0:
        # Manual threshold
        _, binary = cv2.threshold(denoised, threshold, 255, cv2.THRESH_BINARY)
    else:
        # Auto (Adaptive is usually better for plates with shadows)
        binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        # OR Otsu
        # ret, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 5. Morphological Ops
    output_img = binary
    if morph_op and morph_op != 'none' and kernel_size > 0:
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        if morph_op == 'dilation':
            output_img = cv2.dilate(binary, kernel, iterations=1)
        elif morph_op == 'erosion':
            output_img = cv2.erode(binary, kernel, iterations=1)
            
    # Return both the 'ocr-ready' image and a visualization version
    return output_img

def rotate_image(image, angle):
    if angle == 0: return image
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    # Use borderReplicate to avoid black borders affecting OCR if possible
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def process_license_plate(image, points, width_scale=1.0, aspect_ratio=None, threshold=-1, rotation=0, morph_op='none', kernel_size=1):
    pts = np.array(points, dtype="float32")
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    if aspect_ratio:
        maxHeight = int(maxWidth / aspect_ratio)

    if width_scale != 1.0:
        maxWidth = int(maxWidth * width_scale)
        maxHeight = int(maxHeight * width_scale)

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype = "float32")
    
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    
    # Apply user rotation after warp
    if rotation != 0:
        warped = rotate_image(warped, rotation)

    # SIMPLIFIED PIPELINE FOR DEBUGGING
    # 1. Use Warped (BGR) - PaddleOCR requires 3 channels
    # gray_warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    
    # 2. Add Padding (Fix for edge characters)
    # Characters touching the border often fail OCR. Add a white border.
    pad_amount = 20
    padded = cv2.copyMakeBorder(warped, pad_amount, pad_amount, pad_amount, pad_amount, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    ocr_input = padded
    
    # Define enhanced for return compatibility (using warped for now)
    enhanced = padded

    try:
        results_candidates = []
        with ocr_lock:
             # Standard OCR on Grayscale
             engine = get_ocr_engine()
             res0 = engine.ocr(ocr_input)
             if res0:
                 # Check if it's a list of lists or a list of dicts
                 # If dict (PP-Structure style): {'rec_texts': [], ...}
                 # If list (Standard OCR): [[box, (text, conf)], ...]
                 if isinstance(res0[0], dict):
                     results_candidates = res0[0] # Store the dict
                 elif isinstance(res0[0], list):
                     results_candidates = res0[0] # Store the list

        
        # Log raw count
        if True: # Kept for structure, but logging removed
             pass

        # Reconstruct result
        if results_candidates:
             # If it's a dict (PaddleStructure), wrap it
             result = [results_candidates]
        else:
             pass
             result = []
             
    except Exception as e:
        print(f"DEBUG: Critical PaddleOCR error: {e}")
        result = []

    
    # Clean up
    if 'results_candidates' not in locals(): results_candidates = []
    
    ocr_details = []
    detected_text = []

    if result:
        # Handle PaddleOCR structure
        # Structure often: [ [ [ [x1,y1],..], ("text", conf) ], ... ]
        lines = result[0] if result and isinstance(result, list) and len(result) > 0 else []
        
        if lines:
            # Handle Dict structure (PP-Structure / Layout analysis result?)
            if isinstance(lines, dict) and 'rec_texts' in lines:
                rec_texts = lines.get('rec_texts', [])
                rec_scores = lines.get('rec_scores', [])
                rec_boxes = lines.get('rec_boxes', []) # might be 'dt_polys' or 'rec_polys' or 'rec_boxes'
                
                # Logs showed: rec_texts, rec_scores, rec_boxes
                count = len(rec_texts)
                for i in range(count):
                    text_content = rec_texts[i]
                    confidence = rec_scores[i] if i < len(rec_scores) else 0.0
                    box = rec_boxes[i] if i < len(rec_boxes) else []
                    
                    if isinstance(box, np.ndarray):
                        box = box.tolist()
                    
                    ocr_details.append({
                        "text": text_content,
                        "confidence": float(confidence),
                        "box": box
                    })
                    
                    if confidence > 0.0:
                         print(f"DEBUG: Accepted text: '{text_content}' with conf {confidence}")
                         detected_text.append(text_content)
            
            # Handle List structure (Standard OCR)
            elif isinstance(lines, list):
                 for i, line in enumerate(lines):
                     # line structure: [box_points, (text, score)]
                     if isinstance(line, (list, tuple)) and len(line) >= 2:
                         box = line[0]
                         text_info = line[1]
                         if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                             text_content = text_info[0]
                             confidence = text_info[1]
                             
                             if isinstance(box, np.ndarray):
                                 box = box.tolist()

                             ocr_details.append({
                                 "text": text_content,
                                 "confidence": float(confidence),
                                 "box": box
                             })
                             
                             if confidence > 0.0:  # ACCEPT ALL RESULTS FOR DEBUGGING
                                 print(f"DEBUG: Accepted text: '{text_content}' with conf {confidence}")
                                 detected_text.append(text_content)
    
                             else:
                                 print(f"DEBUG: Rejected text: '{text_content}' with conf {confidence}")

    final_text = " ".join(detected_text)
    
    # Return: Warped(RGB), Text, Enhanced(for Debug), Details
    return warped, final_text, enhanced, ocr_details
