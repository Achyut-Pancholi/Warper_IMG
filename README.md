# 🚗 License Plate Warper & OCR (Streamlit Edition)

A high-performance "Photo Mode" and "Video Mode" application to detect, warp, and recognize text from license plates. This system uses **YOLOv8** for detection and **PaddleOCR** for text recognition, wrapped in a sleek **Streamlit** user interface.

## 🌟 Key Features

### 📸 Photo Mode
- **Auto-Detect**: Uses AI (YOLOv8) to automatically find the license plate and place 4 corner points.
- **Manual Refinement**: Drag-and-drop the 4 points on the canvas to perfectly align the plate if the AI misses.
- **Advanced Warping**: Perspective transformation to flatten skewed plates.
- **OCR Engine**: Extracts text using PaddleOCR with character-level confidence.

### 🎥 Video Mode (Beta)
- **Time Range Processing**: Select a specific clip (e.g., "5s to 12s") to analyze.
- **Frame Scan Control**: Choose how many frames to process (balance speed vs. accuracy).
- **Consensus Voting**: Aggregates OCR results across multiple frames to determine the most likely text.

### ⚙️ Advanced Controls
- **Aspect Ratio Slider**: Force the warped image to specific dimensions (fixes "squashed" plates).
- **Resolution Boost**: Upscale the image before OCR for better clarity.
- **Tilt Correction**: Manually rotate the plate.
- **Image Pre-processing**: Adjust threshold, erosion, and dilation to handle bad lighting.
- **Debug View**: See exactly what the computer sees (Binary/Black & White image).

---

## 📂 Project Structure

```
Warper_IMG/
├── backend/
│   ├── processor.py         # core logic: Warping + OCR (PaddleOCR)
│   ├── detector.py          # core logic: YOLOv8 Detection
│   ├── video_processor.py   # core logic: Video frame extraction & processing
│   ├── app.py               # (Legacy) Flask backend
│   └── requirements.txt     # Python dependencies
│
├── frontend/                # (Legacy) React Frontend code
│
├── streamlit_app.py         # 🚀 MAIN APP: The Streamlit User Interface
├── yolov8n.pt               # YOLO model weights (auto-downloaded)
└── README.md                # This documentation
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
- **Python 3.8 - 3.11** installed.
- **Visual Studio Code** (Recommended).

### 2. Set up Environment
Open a terminal in the project root (`Warper_IMG/`) and follow these steps:

#### Windows (PowerShell)
```powershell
# Navigate to backend folder
cd backend

# Create virtual environment
python -m venv venv

# Activate environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the App
Once the dependencies are installed and the environment is active, navigate back to the root folder and run Streamlit:

```powershell
# Go back to root
cd ..

# Run Streamlit (pointing to the Python in your venv)
backend\venv\Scripts\python -m streamlit run streamlit_app.py
```

The app should open automatically in your browser at `http://localhost:8501`.

---

## 📖 Usage Guide

### Photo Mode Workflow
1.  **Upload Image**: Drag & drop a car image (`.jpg`, `.png`).
2.  **Auto-Detect**: Click the **"🪄 Auto-Detect Points (Beta)"** button.
    *   *If detection fails:* Click on the image to manually place 4 points (Top-Left, Top-Right, Bottom-Right, Bottom-Left).
3.  **Process**: Click **"🚀 Process Plate"**.
4.  **Refine**:
    *   **Is the plate squashed?** Use the **"Force Aspect Ratio"** slider (set to ~4.0 for long plates).
    *   **Text not reading?** Enable **"Show Computer Vision View"** and adjust the **Threshold** slider until the text is clear in black & white.

### Video Mode Workflow
1.  **Tab Switch**: Click on the **"Video Mode"** tab.
2.  **Upload Video**: Drag & drop a video file (`.mp4`, `.avi`).
3.  **Configure**:
    *   **Time Range**: Select the start/end seconds to analyze.
    *   **Frames to Scan**: Increase this for better accuracy (slower) or decrease for speed.
4.  **Analyze**: Click **"Analyze Video"**. Results will show the "Consensus Text" (most frequent result).

---

## 🔧 Troubleshooting & Debugging

**Issue: "Streamlit command not found"**
*   **Fix**: Ensure you are using the python from the virtual environment: `backend\venv\Scripts\python -m streamlit run ...`

**Issue: "AI Detect is hitting random objects"**
*   **Reason**: The current model (`yolov8n.pt`) is a generic object detector. It detects "cars" well but "license plates" specifically requires a fine-tuned model.
*   **Fix**: Manual point selection is recommended for high precision if Auto-Detect captures the whole car.

**Issue: "OCR result is empty"**
*   **Fix**:
    1.  Check the **"Show Computer Vision View"**.
    2.  If it's black, move the **Threshold** slider.
    3.  If the text is touching the edge, the app now adds padding automatically.
    4.  Try increasing the **Resolution Boost** to 2.5 or 3.0.

**Issue: "The warped image looks weird/diagonal"**
*   **Fix**: Ensure your 4 points are in the correct order: **Top-Left -> Top-Right -> Bottom-Right -> Bottom-Left**.

---

## 🛠️ Tech Stack
*   **Frontend**: Streamlit
*   **Computer Vision**: OpenCV, NumPy
*   **AI Models**: YOLOv8 (Detection), PaddleOCR (Recognition)
*   **Backend Logic**: Python
