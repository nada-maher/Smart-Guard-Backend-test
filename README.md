# 🛡️ Smart Guard Backend

> 🚀 **Advanced Security Monitoring System with AI-Powered Anomaly Detection**

## 📋 Overview

Smart Guard Backend is a sophisticated security monitoring system that provides real-time video surveillance with AI-powered abnormal behavior detection. The system supports multiple camera types and deployment environments, making it perfect for both local and cloud deployments.

## 🎯 Features

### 🎥️ **Camera Support**
- 📹 **Local Cameras**: USB/Integrated webcams
- 🌐 **IP Cameras**: RTSP/HTTP streaming
- 📺 **RTMP Streaming**: Professional broadcasting
- 📱 **Device Streaming**: Mobile phone cameras
- 🎨 **Cloud Simulation**: Virtual camera for cloud environments

### 🤖 **AI-Powered Detection**
- 🧠 **Abnormal Behavior Detection**: Advanced ML models
- 📊 **Real-time Analysis**: 35-frame processing
- 🔔 **Smart Alerts**: Email and WhatsApp notifications
- 📈 **Confidence Scoring**: Detailed prediction metrics

### 🌐 **Deployment Options**
- ☁️ **Railway**: Optimized for cloud deployment
- 🚀 **Fly.io**: Alternative cloud platform
- 💻 **Local Development**: Easy local setup
- 🐳 **Docker Support**: Containerized deployment

## 🚀 Quick Start

### 📋 Prerequisites

- **Python 3.13+**
- **OpenCV 4.8+**
- **Supabase Account**
- **Railway/Fly.io Account** (for cloud deployment)

### 🔧 Installation

```bash
# Clone the repository
git clone <repository-url>
cd Smart-guard-master/Backend

# Install dependencies
pip install -r requirements.txt

# Run locally
python start_backend.py
```

## 🌐 Deployment

### ☁️ **Railway Deployment**

1. **Create Railway Account**
   - Visit [railway.app](https://railway.app)
   - Sign up or login

2. **Deploy Project**
   - Click "New Project"
   - Upload the `Backend` folder
   - Set environment variables (auto-configured)

3. **Environment Variables**
   ```toml
   # Camera Configuration
   CAMERA_TYPE = "device"  # local, ip, rtmp, device
   CAMERA_URL = "http://your-ip:8080/video"
   
   # Cloud Detection
   CLOUD_ENV = "true"
   RAILWAY_ENVIRONMENT = "production"
   ```

4. **Deploy**
   - Click "Deploy"
   - Wait for deployment to complete
   - Access at: `https://your-app.railway.app`

### 🚀 **Fly.io Deployment**

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Deploy
fly launch
fly deploy
```

### 💻 **Local Development**

```bash
# Start with local camera
python start_backend.py

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# Video Stream: http://localhost:8001/stream/mjpeg
```

## 📹 Camera Setup

### 🌐 **IP Camera Configuration**

```toml
# For IP cameras
CAMERA_TYPE = "ip"
CAMERA_URL = "rtsp://username:password@camera-ip:554/stream"

# For RTMP streaming
CAMERA_TYPE = "rtmp"
CAMERA_URL = "rtmp://streaming-server/live/key"
```

### 📱 **Mobile Camera Setup**

1. **Install DroidCam** (Android/iOS)
2. **Start IP Webcam** feature
3. **Get the IP address**
4. **Configure in Railway**:
   ```toml
   CAMERA_TYPE = "device"
   CAMERA_URL = "http://phone-ip:8080/video"
   ```

### 💻 **Local Webcam Setup**

```toml
# For built-in webcam
CAMERA_TYPE = "local"
# CAMERA_URL not needed
```

## 🔧 Configuration

### 🌐 **Environment Variables**

| Variable | Description | Default |
|----------|-------------|---------|
| `CAMERA_TYPE` | Camera type (local, ip, rtmp, device) | `local` |
| `CAMERA_URL` | Camera stream URL | `""` |
| `CLOUD_ENV` | Cloud environment detection | `false` |
| `SUPABASE_URL` | Supabase database URL | Required |
| `SUPABASE_ANON_KEY` | Supabase public key | Required |
| `SMTP_SERVER` | Email server | `smtp.gmail.com` |
| `SENDER_EMAIL` | Sender email | Required |
| `TWILIO_ACCOUNT_SID` | Twilio account ID | Required |

### 📊 **Model Configuration**

The system uses advanced AI models for abnormal behavior detection:

- **Input Processing**: 35-frame analysis windows
- **Feature Extraction**: Motion, object, and behavior patterns
- **Classification**: Normal vs Abnormal behavior
- **Confidence Scoring**: 0.0 to 1.0 confidence levels
- **Alert Cooldown**: 90 seconds between duplicate alerts

## 📡 **API Endpoints**

### 🔐 **Authentication**
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `POST /api/auth/refresh` - Token refresh

### 👥 **Users Management**
- `GET /api/users/` - List users
- `POST /api/users/` - Create user
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

### 📹 **Camera Control**
- `GET /api/camera/status` - Camera status
- `POST /api/camera/enable` - Enable camera
- `POST /api/camera/disable` - Disable camera
- `GET /api/camera/stream` - Video stream endpoint

### 📊 **Monitoring**
- `GET /api/monitoring/alerts` - Recent alerts
- `POST /api/monitoring/test` - Test detection
- `GET /api/monitoring/stats` - System statistics

### 🔔 **Notifications**
- `POST /api/notifications/email` - Send email alert
- `POST /api/notifications/whatsapp` - Send WhatsApp alert
- `GET /api/notifications/history` - Alert history

## 🎥️ **Video Streaming**

### 📹 **MJPEG Stream**
- **URL**: `/stream/mjpeg`
- **Format**: Motion JPEG
- **Resolution**: 640x480
- **FPS**: 30 frames per second
- **Access**: `http://localhost:8001/stream/mjpeg`

### 🎨 **Cloud Simulation**
When no physical camera is available, the system provides a sophisticated simulation:

- **Dynamic Elements**: Moving circles, rectangles, and grids
- **Real-time Info**: Timestamp, frame count, status
- **Professional UI**: Clean, modern interface design
- **Status Indicators**: Clear system state display

## 📊 **Database Schema**

### 👥 **Users Table**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT,
    role TEXT DEFAULT 'user',
    organization TEXT DEFAULT 'SmartGuard',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 📊 **Alerts Table**
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    video_id TEXT,
    timestamp TIMESTAMP,
    confidence REAL,
    prediction TEXT,
    snapshot_path TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## 🛠️ **Development**

### 🧪 **Testing**
```bash
# Run tests
python -m pytest tests/

# Test camera stream
curl http://localhost:8001/stream/mjpeg

# Test API endpoints
curl http://localhost:8000/api/camera/status
```

### 🐛 **Debugging**
```bash
# Enable debug logging
export DEBUG=true

# View logs
tail -f smart_guard.log

# Check camera status
python -c "from workers.stream_processor import *; print(get_camera_status())"
```

## 🔒 **Security**

### 🛡️ **Authentication**
- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control
- Session management

### 🔐 **API Security**
- CORS configuration
- Rate limiting
- Input validation
- SQL injection prevention

### 📡 **Data Protection**
- Encrypted database connections
- Secure environment variables
- HTTPS enforcement in production

## 🚀 **Performance**

### ⚡ **Optimizations**
- **Frame Buffering**: Reduces latency
- **Async Processing**: Non-blocking operations
- **Memory Management**: Efficient frame handling
- **Connection Pooling**: Database optimization

### 📊 **Metrics**
- **Processing Speed**: ~30 FPS
- **Memory Usage**: < 500MB
- **CPU Usage**: < 50% per core
- **Network Latency**: < 100ms

## 🔧 **Troubleshooting**

### 🐛 **Common Issues**

**Camera Not Found**
```bash
# Check camera permissions
ls -la /dev/video*

# Test with different indices
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

**OpenCV Installation Error**
```bash
# Install system dependencies
sudo apt-get install libgl1-mesa-glx libglib2.0-0

# Use Python 3.13
python3.13 -m pip install opencv-python
```

**Database Connection Error**
```bash
# Check Supabase credentials
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY

# Test connection
python -c "import supabase; print(supabase.create_client().table('users').select('*').execute())"
```

## 📞 **Support**

### 🆘 **Getting Help**
- 📧 **Documentation**: [Full Documentation](./docs/)
- 🐛 **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)

### 📧 **Contributing**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- **OpenCV**: Computer vision library
- **FastAPI**: Web framework
- **Supabase**: Backend-as-a-service
- **Railway**: Cloud platform
- **React**: Frontend framework

---

**🛡️ Smart Guard - Protecting what matters most with AI-powered security**

*Last updated: April 2026*
