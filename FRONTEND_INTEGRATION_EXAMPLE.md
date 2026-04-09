# Frontend Integration Example - Manual Camera Analysis

## Overview
The backend now supports manual camera triggering instead of automatic detection. The frontend captures video and sends it to the backend for analysis.

## Available Endpoints

### 1. REST API - Video Upload Analysis
```javascript
// Upload video file for analysis
const analyzeVideo = async (videoFile, videoId = "manual_upload", organization = "Smart Guard") => {
  const formData = new FormData();
  formData.append('file', videoFile);
  formData.append('video_id', videoId);
  formData.append('organization', organization);

  try {
    const response = await fetch('http://localhost:8000/api/manual/analyze-video', {
      method: 'POST',
      body: formData,
    });

    const result = await response.json();
    console.log('Analysis Result:', result);
    return result;
  } catch (error) {
    console.error('Analysis failed:', error);
  }
};
```

### 2. WebSocket - Real-time Frame Analysis
```javascript
// WebSocket connection for real-time analysis
const ws = new WebSocket('ws://localhost:8000/ws/manual-analysis');

ws.onopen = () => {
  console.log('Connected to manual analysis WebSocket');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received analysis result:', data);
  
  if (data.type === 'analysis_result') {
    if (data.is_abnormal) {
      console.log(`Abnormal behavior detected! Confidence: ${data.confidence}`);
      // Trigger alert, show notification, etc.
    }
  }
};

// Send video frame for analysis
const sendFrameForAnalysis = (canvasElement, videoId = "manual_frame") => {
  const base64Data = canvasElement.toDataURL('image/jpeg', 0.8);
  
  const message = {
    type: 'video_frame',
    frame_data: base64Data,
    video_id: videoId,
    organization: 'Smart Guard'
  };
  
  ws.send(JSON.stringify(message));
};
```

## Frontend Implementation Example

### React Component Example
```jsx
import React, { useState, useRef, useEffect } from 'react';

const ManualCameraAnalysis = () => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [ws, setWs] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    // Initialize WebSocket connection
    const websocket = new WebSocket('ws://localhost:8000/ws/manual-analysis');
    
    websocket.onopen = () => {
      console.log('WebSocket connected');
      setWs(websocket);
    };
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'analysis_result') {
        setLastResult(data);
        if (data.is_abnormal) {
          // Handle abnormal behavior detection
          alert(`Abnormal behavior detected! Confidence: ${data.confidence.toFixed(3)}`);
        }
      }
    };
    
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    return () => {
      websocket.close();
    };
  }, []);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 } 
      });
      videoRef.current.srcObject = stream;
    } catch (error) {
      console.error('Camera access denied:', error);
    }
  };

  const captureAndAnalyze = () => {
    if (!videoRef.current || !ws) return;
    
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    canvas.width = 640;
    canvas.height = 480;
    
    // Draw video frame to canvas
    context.drawImage(videoRef.current, 0, 0, 640, 480);
    
    // Send frame for analysis
    const base64Data = canvas.toDataURL('image/jpeg', 0.8);
    const message = {
      type: 'video_frame',
      frame_data: base64Data,
      video_id: 'manual_capture',
      organization: 'Smart Guard'
    };
    
    ws.send(JSON.stringify(message));
    setIsAnalyzing(true);
    
    // Reset analyzing state after 2 seconds
    setTimeout(() => setIsAnalyzing(false), 2000);
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('video_id', 'file_upload');
    formData.append('organization', 'Smart Guard');
    
    try {
      const response = await fetch('http://localhost:8000/api/manual/analyze-video', {
        method: 'POST',
        body: formData,
      });
      
      const result = await response.json();
      setLastResult(result);
      
      if (result.is_abnormal) {
        alert(`Abnormal behavior detected! Confidence: ${result.confidence.toFixed(3)}`);
      }
    } catch (error) {
      console.error('Analysis failed:', error);
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h2>Manual Camera Analysis</h2>
      
      {/* Camera Section */}
      <div style={{ marginBottom: '20px' }}>
        <h3>Live Camera Analysis</h3>
        <button onClick={startCamera}>Start Camera</button>
        <button 
          onClick={captureAndAnalyze} 
          disabled={!ws || isAnalyzing}
          style={{ marginLeft: '10px' }}
        >
          {isAnalyzing ? 'Analyzing...' : 'Capture & Analyze'}
        </button>
        
        <div style={{ marginTop: '10px' }}>
          <video ref={videoRef} autoPlay style={{ display: 'none' }} />
          <canvas ref={canvasRef} style={{ border: '1px solid black' }} />
        </div>
      </div>
      
      {/* File Upload Section */}
      <div style={{ marginBottom: '20px' }}>
        <h3>Video File Analysis</h3>
        <input type="file" accept="video/*" onChange={handleFileUpload} />
      </div>
      
      {/* Results Section */}
      {lastResult && (
        <div style={{ 
          padding: '10px', 
          border: '1px solid #ccc', 
          borderRadius: '5px',
          backgroundColor: lastResult.is_abnormal ? '#ffebee' : '#e8f5e8'
        }}>
          <h4>Analysis Results</h4>
          <p><strong>Confidence:</strong> {lastResult.confidence.toFixed(3)}</p>
          <p><strong>Status:</strong> {lastResult.is_abnormal ? 'ABNORMAL' : 'NORMAL'}</p>
          <p><strong>Threshold:</strong> {lastResult.threshold}</p>
          <p><strong>Timestamp:</strong> {new Date(lastResult.timestamp).toLocaleString()}</p>
        </div>
      )}
    </div>
  );
};

export default ManualCameraAnalysis;
```

## Backend Status Check
```javascript
// Check if backend is ready for analysis
const checkBackendStatus = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/manual/status');
    const status = await response.json();
    console.log('Backend Status:', status);
    return status;
  } catch (error) {
    console.error('Backend not available:', error);
  }
};
```

## Usage Flow

1. **Start Backend**: Run `python main.py` or `uvicorn main:app --reload`
2. **Frontend Camera**: Frontend accesses camera using `getUserMedia()`
3. **Manual Trigger**: User clicks button to capture/analyze
4. **Send to Backend**: Frontend sends video frame/file via WebSocket/REST
5. **Analysis**: Backend processes video using ML model
6. **Results**: Backend returns analysis results and triggers alerts if needed
7. **Display**: Frontend shows results to user

## Benefits of Manual Mode

- **User Control**: Camera only captures when user triggers it
- **Privacy**: No continuous surveillance
- **Resource Efficient**: Analysis only when needed
- **Flexible**: Support both file upload and real-time analysis
- **Scalable**: Better for multi-user environments

## API Response Format

```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "video_id": "manual_upload",
  "organization": "Smart Guard",
  "confidence": 0.85,
  "is_abnormal": true,
  "threshold": 0.5,
  "model_path": "/path/to/model",
  "analysis_type": "manual"
}
```
