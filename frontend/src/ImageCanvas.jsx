import React, { useState, useRef, useEffect } from 'react';
import './ImageCanvas.css';

const ImageCanvas = ({ onProcess }) => {
    const [image, setImage] = useState(null);
    const [points, setPoints] = useState([]); // List of {x, y}
    const [draggingPoint, setDraggingPoint] = useState(null);
    const [detecting, setDetecting] = useState(false);
    const canvasRef = useRef(null);
    const [imgObj, setImgObj] = useState(null);

    const handleImageUpload = (e) => {
        const file = e.target.files[0];
        if (file) {
            // Visualize immediately
            const reader = new FileReader();
            reader.onload = (event) => {
                const img = new Image();
                img.onload = () => {
                    setImgObj(img);
                    setPoints([]);
                    setImage(file);
                };
                img.src = event.target.result;
            };
            reader.readAsDataURL(file);
        }
    };

    // Auto-detect removed as per user request
    const detectPoints = async (file, width, height) => {
        // Disabled
    };

    const getCanvasCoordinates = (e) => {
        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        return {
            x: (e.clientX - rect.left) * scaleX,
            y: (e.clientY - rect.top) * scaleY
        };
    };

    const handleMouseDown = (e) => {
        if (!imgObj) return;
        const coords = getCanvasCoordinates(e);

        // Check if clicking near an existing point
        const clickedPointIndex = points.findIndex(p => {
            const dist = Math.sqrt(Math.pow(p.x - coords.x, 2) + Math.pow(p.y - coords.y, 2));
            return dist < 30; // Hit radius increased
        });

        if (clickedPointIndex !== -1) {
            setDraggingPoint(clickedPointIndex);
        } else if (points.length < 4) {
            // Add new point if not dragging and less than 4
            setPoints([...points, coords]);
        }
    };

    const handleMouseMove = (e) => {
        if (draggingPoint !== null) {
            const coords = getCanvasCoordinates(e);

            // Constrain to canvas
            if (canvasRef.current) {
                coords.x = Math.max(0, Math.min(canvasRef.current.width, coords.x));
                coords.y = Math.max(0, Math.min(canvasRef.current.height, coords.y));
            }

            const newPoints = [...points];
            newPoints[draggingPoint] = coords;
            setPoints(newPoints);
        }
    };

    const handleMouseUp = () => {
        setDraggingPoint(null);
        // Trigger update on drag end
        if (points.length === 4 && image) {
            const ptsList = points.map(p => [p.x, p.y]);
            onProcess(image, JSON.stringify(ptsList));
        }
    };

    const draw = () => {
        const canvas = canvasRef.current;
        if (!canvas || !imgObj) return;
        const ctx = canvas.getContext('2d');

        if (canvas.width !== imgObj.width || canvas.height !== imgObj.height) {
            canvas.width = imgObj.width;
            canvas.height = imgObj.height;
        }

        ctx.drawImage(imgObj, 0, 0);

        // Draw points
        points.forEach((p, index) => {
            ctx.beginPath();
            // Highlight dragging point
            const radius = (index === draggingPoint) ? 20 : 15;
            ctx.arc(p.x, p.y, radius, 0, 2 * Math.PI);
            ctx.fillStyle = (index === draggingPoint) ? '#ffff00' : '#00ff00';
            ctx.fill();
            ctx.lineWidth = 3;
            ctx.strokeStyle = '#000000';
            ctx.stroke();

            // Draw number
            ctx.fillStyle = '#000000';
            ctx.font = 'bold 20px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(index + 1, p.x, p.y);
        });

        // Draw lines
        if (points.length > 0) {
            ctx.beginPath();
            // Draw hull or just lines in order? Let's generic poly
            if (points.length > 1) {
                ctx.moveTo(points[0].x, points[0].y);
                for (let i = 1; i < points.length; i++) {
                    ctx.lineTo(points[i].x, points[i].y);
                }
                if (points.length === 4) ctx.lineTo(points[0].x, points[0].y);
            }
            ctx.strokeStyle = 'rgba(0, 255, 0, 0.8)';
            ctx.lineWidth = 4;
            ctx.stroke();
        }
    };

    useEffect(() => {
        draw();
    }, [imgObj, points, draggingPoint]);

    // Allow parent to access points if needed for real-time (not implemented yet in parent for real-time dragging, but ready)
    useEffect(() => {
        if (points.length === 4 && !draggingPoint) {
            // Could auto-process here if desired
        }
    }, [points, draggingPoint]);

    const handleSubmit = () => {
        if (points.length !== 4) {
            alert("Please select exactly 4 points (TL, TR, BR, BL)");
            return;
        }
        const ptsList = points.map(p => [p.x, p.y]);
        onProcess(image, JSON.stringify(ptsList));
    };

    const handleReset = () => {
        setPoints([]);
    };

    return (
        <div className="canvas-container">
            <div className="controls">
                <label className="upload-btn primary">
                    Upload Car Image
                    <input type="file" accept="image/*" onChange={handleImageUpload} hidden />
                </label>
                <button onClick={handleReset} disabled={points.length === 0} className="btn secondary">Reset Points</button>
            </div>

            <div className="canvas-wrapper">
                {detecting && <div className="detecting-overlay">Auto-Detecting Plate...</div>}

                {imgObj ? (
                    <canvas
                        ref={canvasRef}
                        onMouseDown={handleMouseDown}
                        onMouseMove={handleMouseMove}
                        onMouseUp={handleMouseUp}
                        onMouseLeave={handleMouseUp}
                        // Touch support for mobile basics
                        onTouchStart={(e) => {
                            const touch = e.touches[0];
                            const mouseEvent = new MouseEvent("mousedown", {
                                clientX: touch.clientX,
                                clientY: touch.clientY
                            });
                            handleMouseDown(mouseEvent);
                        }}
                        onTouchMove={(e) => {
                            const touch = e.touches[0];
                            const mouseEvent = new MouseEvent("mousemove", {
                                clientX: touch.clientX,
                                clientY: touch.clientY
                            });
                            handleMouseMove(mouseEvent);
                        }}
                        onTouchEnd={handleMouseUp}

                        style={{ maxWidth: '100%', maxHeight: '600px', cursor: draggingPoint !== null ? 'grabbing' : 'crosshair' }}
                    />
                ) : (
                    <div className="placeholder">
                        <p>Upload an image to start</p>
                    </div>
                )}
            </div>
            <div className="instructions">
                <p>Click on the 4 corners of the license plate to select them.</p>
            </div>
        </div>
    );
};

export default ImageCanvas;
