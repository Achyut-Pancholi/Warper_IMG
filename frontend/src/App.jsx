import React, { useState, useEffect } from 'react';
import ImageCanvas from './ImageCanvas';
import './App.css';

function App() {
  const [processedImage, setProcessedImage] = useState(null);
  const [enhancedImage, setEnhancedImage] = useState(null);
  const [extractedText, setExtractedText] = useState(null);
  const [ocrDetails, setOcrDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // State for inputs to trigger effects
  const [inputImage, setInputImage] = useState(null);
  const [inputPoints, setInputPoints] = useState(null);

  // Advanced Debug Settings
  const [settings, setSettings] = useState({
    scale: 2.0,
    aspectRatio: null,
    threshold: -1, // -1 for Auto
    rotation: 0,
    morph_op: 'none',
    kernel_size: 1
  });

  // Debounced Processing Effect
  useEffect(() => {
    if (!inputImage || !inputPoints) return;

    const timer = setTimeout(() => {
      executeProcess(inputImage, inputPoints);
    }, 400); // 400ms debounce

    return () => clearTimeout(timer);
  }, [inputImage, inputPoints, settings]);

  // Handler for Canvas updates (Drag end or Auto-detect)
  const handleCanvasUpdate = (imageFile, pointsJson) => {
    setInputImage(imageFile);
    setInputPoints(pointsJson);
  };

  const [mode, setMode] = useState('image'); // 'image' | 'video'
  const [videoResult, setVideoResult] = useState(null);

  const handleVideoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    setVideoResult(null);
    setError(null);

    const formData = new FormData();
    formData.append('video', file);

    try {
      const res = await fetch('http://localhost:5000/process_video', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setVideoResult(data);
    } catch (err) {
      setError(err.message || "Video processing failed");
    } finally {
      setLoading(false);
    }
  };

  const executeProcess = async (imageFile, pointsJson) => {
    setLoading(true);
    setError(null);
    // Don't clear previous results immediately to reduce flicker during fine-tuning? 
    // Maybe better to show loading overlay.

    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('points', pointsJson);
    formData.append('scale', settings.scale);
    if (settings.aspectRatio) formData.append('aspect_ratio', settings.aspectRatio);

    // Debug params
    formData.append('threshold', settings.threshold);
    formData.append('rotation', settings.rotation);
    formData.append('morph_op', settings.morph_op);
    formData.append('kernel_size', settings.kernel_size);

    try {
      const response = await fetch('http://localhost:5000/process', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Server error: ${response.statusText}`);
      }

      const data = await response.json();

      setProcessedImage(data.image);
      setEnhancedImage(data.enhanced_image);
      setProcessedImage(data.image);
      setEnhancedImage(data.enhanced_image);
      setExtractedText(data.text);
      setOcrDetails(data.ocr_details);
    } catch (err) {
      console.error(err);
      setError(err.message || "Failed to process image");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>License Plate Warper & OCR</h1>
        <p className="subtitle">AI-Powered Detection & Correction</p>
        <div className="mode-switch">
          <button className={`btn ${mode === 'image' ? 'primary' : 'secondary'}`} onClick={() => setMode('image')}>Image Mode</button>
          <button className={`btn ${mode === 'video' ? 'primary' : 'secondary'}`} onClick={() => setMode('video')}>Video Mode</button>
        </div>
      </header>

      <main className="main-content">

        {mode === 'image' && (
          <>
            <section className="controls-section">
              <div className="settings-panel">
                <div className="setting-group">
                  <h3>Output Settings</h3>
                  <div className="setting-item">
                    <label>Output Scale: {settings.scale}x</label>
                    <input
                      type="range"
                      min="1.0"
                      max="3.0"
                      step="0.5"
                      value={settings.scale}
                      onChange={(e) => setSettings({ ...settings, scale: parseFloat(e.target.value) })}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Aspect Ratio: {settings.aspectRatio || "Auto"}</label>
                    <div style={{ display: 'flex', gap: '5px' }}>
                      <input
                        type="range"
                        min="2.0"
                        max="6.0"
                        step="0.1"
                        value={settings.aspectRatio || 4.0}
                        onChange={(e) => setSettings({ ...settings, aspectRatio: parseFloat(e.target.value) })}
                      />
                      <button className="btn small" onClick={() => setSettings({ ...settings, aspectRatio: null })}>Auto</button>
                    </div>
                  </div>
                </div>

                <div className="setting-group">
                  <h3>Debug Controls</h3>
                  <div className="setting-item">
                    <label>Binarization Threshold: {settings.threshold === -1 ? 'Auto' : settings.threshold}</label>
                    <div style={{ display: 'flex', gap: '5px' }}>
                      <input
                        type="range"
                        min="0"
                        max="255"
                        value={settings.threshold === -1 ? 128 : settings.threshold} // Visual default
                        onChange={(e) => setSettings({ ...settings, threshold: parseInt(e.target.value) })}
                      />
                      <button className="btn small" onClick={() => setSettings({ ...settings, threshold: -1 })}>Auto</button>
                    </div>
                  </div>
                  <div className="setting-item">
                    <label>Rotation Correction: {settings.rotation}°</label>
                    <input
                      type="range"
                      min="-15"
                      max="15"
                      step="0.5"
                      value={settings.rotation}
                      onChange={(e) => setSettings({ ...settings, rotation: parseFloat(e.target.value) })}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Morphological Op</label>
                    <select value={settings.morph_op} onChange={(e) => setSettings({ ...settings, morph_op: e.target.value })}>
                      <option value="none">None</option>
                      <option value="dilation">Dilation (Thicken)</option>
                      <option value="erosion">Erosion (Thin)</option>
                    </select>
                  </div>
                </div>
              </div>
            </section>

            <section className="canvas-section">
              <ImageCanvas onProcess={handleCanvasUpdate} />
            </section>

            {(processedImage || extractedText) && (
              <section className="results-section">
                <h2>Results</h2>
                <div className="results-grid">

                  <div className="result-card">
                    <h3>Extracted Text</h3>
                    <div className="ocr-text-box">
                      {extractedText ? (
                        <div>
                          <div style={{ fontSize: '2.5rem', marginBottom: '10px', letterSpacing: '4px' }}>{extractedText}</div>

                          {ocrDetails && ocrDetails.length > 0 && (
                            <div className="confidence-bars">
                              {ocrDetails.map((item, idx) => (
                                <div key={idx} className="conf-item" title={`Confidence: ${(item.confidence * 100).toFixed(1)}%`}>
                                  <span className="char">{item.text}</span>
                                  <div className="bar-container">
                                    <div
                                      className="bar"
                                      style={{
                                        width: `${Math.min(item.confidence * 100, 100)}%`,
                                        backgroundColor: item.confidence > 0.8 ? '#00ff00' : item.confidence > 0.6 ? '#ffff00' : '#ff0000'
                                      }}
                                    ></div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}

                          <div className="action-buttons">
                            <button className="btn-icon" onClick={() => navigator.clipboard.writeText(extractedText)}>📋 Copy Text</button>
                          </div>
                        </div>
                      ) : <span style={{ color: 'gray', fontStyle: 'italic' }}>No text detected</span>}
                    </div>
                  </div>


                  {processedImage && (
                    <div className="result-card">
                      <h3>Warped Preview</h3>
                      <div className="resizable-img-container">
                        <img src={processedImage} alt="Warped Plate" className="result-img" />
                      </div>
                      <div className="action-buttons">
                        <a href={processedImage} download="warped_plate.jpg" className="btn-icon">⬇ Download</a>
                      </div>
                    </div>
                  )}
                  {enhancedImage && (
                    <div className="result-card">
                      <h3>Enhanced (Debug)</h3>
                      <div className="resizable-img-container">
                        <img src={enhancedImage} alt="OCR View" className="result-img" style={{ filter: 'grayscale(100%)' }} />
                      </div>
                      <div className="action-buttons">
                        <a href={enhancedImage} download="debug_ocr.jpg" className="btn-icon">⬇ Download</a>
                      </div>
                    </div>
                  )}

                </div>
              </section>
            )}
          </>
        )}

        {mode === 'video' && (
          <section className="video-section">
            <div className="controls">
              <label className="upload-btn big">
                Upload Video Clip (MP4)
                <input type="file" accept="video/mp4,video/x-m4v,video/*,application/mp4" onChange={handleVideoUpload} hidden />
              </label>
            </div>
            {videoResult && (
              <div className="video-results">
                <div className="result-card highlight">
                  <h3>Consensus Result</h3>
                  <div className="ocr-text-box large">
                    {videoResult.final_text}
                  </div>
                  <p>Confidence: {videoResult.confidence}</p>
                  <p>Frames Processed: {videoResult.frames_processed}</p>
                </div>

                <div className="frame-grid">
                  {videoResult.debug_frames.map((frame, i) => (
                    <div key={i} className="frame-card">
                      <img src={frame.image} alt={`Frame ${frame.frame_idx}`} />
                      <p>Frame {frame.frame_idx}: <strong>{frame.text}</strong></p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {loading && (
          <div className="loading-overlay">
            <div className="spinner"></div>
            <p>Processing...</p>
          </div>
        )}

        {error && (
          <div className="error-message">
            <p>Error: {error}</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
