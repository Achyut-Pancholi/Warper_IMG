import cv2
import numpy as np
import processor
from detector import LicensePlateDetector
from collections import Counter

class VideoProcessor:
    def __init__(self, detector):
        self.detector = detector

    def process_video(self, video_path, num_frames=10, start_time=0, end_time=None):
        """
        Extracts frames, detects plates, runs OCR, and aggregates results.
        start_time, end_time: in seconds
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Could not open video file")

        # Basic properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_video_frames / fps if fps > 0 else 0
        
        # Calculate Start/End Frames
        start_frame = int(start_time * fps)
        if end_time is None or end_time > duration:
            end_time = duration
        end_frame = int(end_time * fps)
        
        # Ensure bounds
        start_frame = max(0, start_frame)
        end_frame = min(total_video_frames, end_frame)
        
        frames_to_scan = end_frame - start_frame
        if frames_to_scan <= 0:
            return {"final_text": "Invalid Time Range", "confidence": "0", "frames_processed": 0, "debug_frames": []}
            
        # We want to pick 'num_frames' spread across the SELECTED RANGE
        step = max(1, frames_to_scan // num_frames)
        
        # Seek to start
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        results = []
        debug_frames = []

        current_frame_idx = start_frame
        extracted_count = 0
        
        while cap.isOpened() and current_frame_idx < end_frame and extracted_count < num_frames:
            # We manually seek to avoid reading every frame if step is large (faster)
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process this frame
            try:
                # 1. Detect
                points = self.detector.detect(frame)
                print(f"DEBUG: Frame {current_frame_idx} Processing. Points: {points}")
                
                if points:
                    # 2. Process (Warp + OCR)
                    # Use default enhancement settings for auto-pipeline
                    warped, text, enhanced, _ = processor.process_license_plate(
                        frame, points, width_scale=2.0 
                    )
                    
                    if text and len(text.strip()) > 2:
                        results.append(text.strip())
                        
                        # Encode debug frame for frontend
                        _, encoded = cv2.imencode('.jpg', warped)
                        import base64
                        b64 = base64.b64encode(encoded).decode('utf-8')
                        debug_frames.append({
                            "frame_idx": current_frame_idx,
                            "text": text,
                            "image": f"data:image/jpeg;base64,{b64}"
                        })

                extracted_count += 1
            except Exception as e:
                print(f"Error processing frame {current_frame_idx}: {e}")

            current_frame_idx += step
        
        cap.release()
        
        # Voting / Aggregation
        final_text = "No Plate Detected"
        confidence = "0"
        
        if results:
            # Simple majority voting
            # For plates, we might want char-by-char voting if results vary slightly,
            # but whole-string voting is a good start.
            counts = Counter(results)
            most_common = counts.most_common(1)[0] # (text, count)
            final_text = most_common[0]
            confidence = f"{most_common[1]}/{len(results)} matches"
            
            # Advanced: If no consensus, maybe merge? 
            # E.g. "ABC 123" vs "ABC I23" -> "ABC 123" via char voting
            # Leave for refinement.

        return {
            "final_text": final_text,
            "confidence": confidence,
            "frames_processed": extracted_count,
            "debug_frames": debug_frames # Return the successful frames to show user
        }
