
import streamlit as st
import cv2
import numpy as np
import sys
import os
import tempfile
from PIL import Image
import pandas as pd
from streamlit_drawable_canvas import st_canvas

# Add backend to path so we can import modules
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from backend import processor
    from backend.detector import LicensePlateDetector
    from backend.video_processor import VideoProcessor
except ImportError as e:
    st.error(f"Error importing backend modules: {e}")
    st.stop()

# Page config
st.set_page_config(
    page_title="LPR Warper & OCR",
    layout="wide"
)

# Custom CSS for "Premium" look
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stButton>button {
        background-color: #ff4b4b;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #ff3333;
    }
    h1 {
        text-align: center;
        margin-bottom: 2rem;
    }
    .uploaded-img {
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🚗 License Plate Warper & OCR")

# --- Initialize Engines (Cached) ---
@st.cache_resource
def load_detector():
    return LicensePlateDetector()

detector = load_detector()
video_processor = VideoProcessor(detector)

# --- Logic ---

def reset_defaults():
    st.session_state['width_scale'] = 2.0
    st.session_state['rotation'] = 0
    st.session_state['aspect_ratio'] = 0.0
    st.session_state['threshold'] = -1
    st.session_state['morph_op'] = "none"
    st.session_state['kernel_size'] = 1

def process_photo_mode():
    st.header("📸 Photo Mode")
    
    col1, col2 = st.columns([1, 1])
    
    # --- Sidebar Controls ---
    with st.sidebar:
        st.header("🛠️ Fine-Tuning")
        st.markdown("Use these controls if the result isn't perfect.")
        
        st.subheader("1. Geometry (Shape)")
        width_scale = st.slider("Resolution Boost", 0.5, 3.0, 2.0, 0.1, help="Makes the image bigger. Helps read small text.", key="width_scale")
        rotation = st.slider("Tilt Correction", -45, 45, 0, 1, help="If the text is slanted, use this to rotate it straight.", key="rotation")
        aspect_ratio = st.slider("Force Aspect Ratio", 0.0, 6.0, 0.0, 0.1, help="0.0 = Auto-calculate. Set to ~4.0 for long plates, ~2.0 for square-ish plates. This forces the warped image to be a rectangle.", key="aspect_ratio")
        
        st.divider()
        st.subheader("2. Image Clarity")
        st.info("Adjust these if lighting is bad or text is faint.")
        threshold = st.slider("Dark/Light Threshold", -1, 255, -1, 1, help="-1 is Auto. Increase to make image darker, Decrease to make it lighter.", key="threshold")
        morph_op = st.selectbox("Clean-up Method", ["none", "dilation", "erosion"], index=0, help="Dilation makes text thicker. Erosion makes text thinner.", key="morph_op")
        kernel_size = st.slider("Effect Strength", 1, 5, 1, 1, help="How strong the Clean-up Method should be.", key="kernel_size")
        
        st.divider()
        st.divider()
        st.button("🔄 Reset to Automatic / Default", type="secondary", on_click=reset_defaults)

        st.divider()
        show_debug = st.checkbox("Show 'Computer Vision' View", value=False, help="See exactly what image is being sent to the OCR engine (Binary/Black & White).")
    
    with col1:
        uploaded_file = st.file_uploader("Upload Car/Plate Image", type=['jpg', 'png', 'jpeg'])

    # Initialize Session State
    if 'canvas_key' not in st.session_state:
        st.session_state['canvas_key'] = "canvas_1"
    if 'initial_drawing' not in st.session_state:
        st.session_state['initial_drawing'] = None

    if uploaded_file is not None:
        # Convert file to opencv image
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Dimensions
        h, w = image.shape[:2]
        
        with col1:
            st.markdown("### 1. Select 4 Points")
            st.info("Click 4 corners of the license plate in order: Top-Left, Top-Right, Bottom-Right, Bottom-Left.")
            
            # Canvas for clicking
            # Resize for canvas if too big
            # Resize for canvas
            display_width = 600
            scale_factor = display_width / w
            display_height = int(h * scale_factor)
            
            # Explicitly resize image for canvas to ensure alignment
            canvas_image = cv2.resize(image_rgb, (display_width, display_height))
            
            # DEBUG: Check if image exists before canvas
            st.write(f"Debug: Image Size: {display_width}x{display_height}")
            # st.image(canvas_image, caption="Debug Preview") # Comment out once verified
            
            # Convert to PIL and ensure RGB
            pil_image = Image.fromarray(canvas_image).convert("RGB")

            # Create a canvas component
            canvas_result = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",  # dim orange
                stroke_width=3,
                stroke_color="#FF4B4B",
                background_image=pil_image,
                update_streamlit=True,
                height=display_height,
                width=display_width,
                drawing_mode="point",
                point_display_radius=5,
                key=st.session_state['canvas_key'],
                initial_drawing=st.session_state['initial_drawing'],
            )
            
            # Get points
            points = []
            if canvas_result.json_data is not None:
                objects = canvas_result.json_data["objects"]
                for obj in objects:
                    if obj["type"] == "circle": # It's a point
                        # Scale back to original coordinates
                        orig_x = obj["left"] / scale_factor
                        orig_y = obj["top"] / scale_factor
                        points.append([orig_x, orig_y])
            
            st.write(f"selected points: {len(points)}")
            
            # Auto-detect button fallback
            if st.button("🪄 Auto-Detect Points (Beta)"):
                 detected_points = detector.detect(image)
                 if detected_points:
                     st.success("Plate detected by AI!")
                     # Update session state to force canvas redraw with new points
                     import uuid
                     st.session_state['canvas_key'] = str(uuid.uuid4())
                     
                     # Construct initial drawing JSON for canvas
                     # Canvas expects objects list
                     objects = []
                     for p in detected_points:
                         # Scale to canvas
                         objects.append({
                             "type": "circle",
                             "left": p[0] * scale_factor,
                             "top": p[1] * scale_factor,
                             "width": 10,
                             "height": 10,
                             "fill": "blue",
                             "stroke": "#FF4B4B",
                             "strokeWidth": 3
                         })
                     
                     st.session_state['initial_drawing'] = {"version": "4.4.0", "objects": objects}
                     # Rerun to show update
                     st.rerun()
                 else:
                     st.warning("AI could not find a plate. Please click manually.")
        
        with col2:
            st.markdown("### 2. Results")
            display_area = st.empty()
            
            if st.button("🚀 Process Plate", type="primary"):
                if len(points) != 4:
                    st.error(f"Please select exactly 4 points! (Currently: {len(points)})")
                else:
                    with st.spinner("Warping & Reading Text..."):
                        # Ensure points are list of lists
                        safe_points = [[p[0], p[1]] for p in points]
                        
                        # DEBUG: Show what we are sending
                        st.write(f"DEBUG: Processing with points: {safe_points}")
                        st.write(f"DEBUG: Image Shape: {image.shape}")
                        
                        warped, text, enhanced, details = processor.process_license_plate(
                            image, 
                            safe_points, 
                            width_scale=width_scale,
                            aspect_ratio=aspect_ratio if aspect_ratio > 0 else None,
                            rotation=rotation,
                            threshold=threshold,
                            morph_op=morph_op,
                            kernel_size=kernel_size
                        )
                        
                        # Display Results
                        st.subheader("B. Final Result")
                        
                        col_res1, col_res2 = st.columns(2)
                        
                        with col_res1:
                             st.markdown("**Warped Plate**")
                             # Convert warped to RGB for display
                             warped_rgb = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)
                             st.image(warped_rgb, width=300)
                        
                        with col_res2:
                             if show_debug:
                                 st.markdown("**Computer Vision View** (What the AI sees)")
                                 if len(enhanced.shape) == 2:
                                      enhanced_disp = enhanced
                                 else:
                                      enhanced_disp = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
                                 st.image(enhanced_disp, width=300)
                        
                        st.subheader("Extracted Text")
                        if text:
                            st.markdown(f"<div style='font-size: 3rem; font-weight: bold; color: #4CAF50; border: 2px solid #4CAF50; padding: 10px; border-radius: 10px; text-align: center;'>{text}</div>", unsafe_allow_html=True)
                        else:
                             st.markdown("<div style='font-size: 2rem; color: gray;'>No text found</div>", unsafe_allow_html=True)
                        
                        # Details Expander
                        with st.expander("See OCR Confidence & Details"):
                             if details:
                                 df = pd.DataFrame(details)
                                 # Clean up columns if necessary
                                 if 'box' in df.columns:
                                     df = df.drop(columns=['box'])
                                 st.dataframe(df)

def process_video_mode():
    st.header("🎥 Video Mode")
    
    uploaded_video = st.file_uploader("Upload Video", type=['mp4', 'avi', 'mov'])
    
    if uploaded_video is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False) 
        tfile.write(uploaded_video.read())
        
        st.video(tfile.name)
        
        # Get Video Meta (Duration) for slider
        try:
            cap = cv2.VideoCapture(tfile.name)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 10.0
            cap.release()
        except:
            duration = 10.0 # Fallback

        st.subheader("⚙️ Processing Options")
        col_v1, col_v2 = st.columns(2)
        
        with col_v1:
            # Time Range Slider
            start_time, end_time = st.slider(
                "Time Range (Seconds)",
                0.0, float(duration), (0.0, float(duration)),
                step=1.0,
                help="Select the section of video to analyze."
            )
        
        with col_v2:
            num_frames = st.slider("Frames to Scan", 10, 200, 20, 10, help="More frames = Higher chance of detection but slower.")

        if st.button("Analyze Video"):
            with st.spinner(f"Processing {num_frames} frames from {start_time}s to {end_time}s..."):
                results = video_processor.process_video(
                    tfile.name, 
                    num_frames=num_frames,
                    start_time=start_time,
                    end_time=end_time
                )
                
                st.success("Processing Complete!")
                
                # Summary Stats
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Consensus Text", results.get("final_text", "N/A"))
                with col_b:
                    st.metric("Confidence / Votes", results.get("confidence", "0"))
                
                # Debug Frames
                debug_frames = results.get("debug_frames", [])
                if debug_frames:
                    st.subheader(f"Captured Frames ({len(debug_frames)})")
                    
                    # Carousel-like display
                    cols = st.columns(3)
                    for idx, frame_data in enumerate(debug_frames):
                        with cols[idx % 3]:
                            # image is data url "data:image/jpeg;base64,..."
                            # Streamlit st.image can read this directly? usually needs bytes or path.
                            # Let's decode or just show text for now, or display properly.
                            
                            # Actually st.image handles base64? Not directly usually.
                            import base64
                            header, encoded = frame_data["image"].split(",", 1)
                            binary = base64.b64decode(encoded)
                            
                            # image_array = cv2.imdecode(np.frombuffer(binary, np.uint8), 1)
                            # rgb = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
                            
                            st.image(binary, caption=f"Frame {frame_data['frame_idx']} - '{frame_data['text']}'")
                else:
                    st.warning("No readable plates found in video frames.")

# --- Main Layout ---
tab1, tab2 = st.tabs(["Photo Mode", "Video Mode"])

with tab1:
    process_photo_mode()

with tab2:
    process_video_mode()
