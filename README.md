# Weapon Detection System

A Flask-based web application for real-time weapon (pistol) detection using YOLOv8 with multi-user authentication support.

## Features

- 🔐 Multi-user authentication system
- 📸 Support for image and video processing
- 🔫 Real-time weapon detection using YOLOv8
- 🌓 Dark/Light theme toggle
- 📊 Detection statistics and results visualization
- 🔒 User-specific file storage and processing

## Prerequisites

- Python 3.8 or higher
- Conda package manager
- CUDA-capable GPU (recommended for faster processing)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Sindhujathammi/WeaponDetection.git
   cd WeaponDetection
   ```

2. **Create and activate Conda environment**
   ```bash
   conda create -n weapon-detection python=3.8
   conda activate weapon-detection
   ```

3. **Install PyTorch with CUDA support (if you have a CUDA-capable GPU)**
   ```bash
   conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
   ```
   
   For CPU-only installation:
   ```bash
   conda install pytorch torchvision torchaudio cpuonly -c pytorch
   ```

4. **Install required packages**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create necessary directories**
   ```bash
   mkdir -p static/uploads static/outputs models
   ```

6. **Download the model**
   - Place your trained YOLOv8 model file (best.pt) in the `models` directory
   - If you don't have a trained model, you can use the default YOLOv8n model:
     ```bash
     wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -O models/best.pt
     ```

## Usage

1. **Start the application**
   ```bash
   python app.py
   ```

2. **Access the web interface**
   - Open your browser and navigate to `http://localhost:5000`
   - Default admin credentials:
     - Username: admin
     - Password: admin123

3. **Using the application**
   - Register a new account or login with existing credentials
   - Upload an image or video file
   - Click "Process File" to start detection
   - View results and statistics
   - Use the clear button to remove processed files

## Project Structure

```
WeaponDetection/
├── app.py                 # Main Flask application
├── models/               
│   └── best.pt           # YOLOv8 model file
├── static/
│   ├── uploads/          # User uploads directory
│   └── outputs/          # Processed files directory
└── templates/
    ├── index.html        # Main application template
    ├── login.html        # Login page template
    └── register.html     # Registration page template
```

## Environment Variables

Create a `.env` file in the root directory with the following variables:
```env
FLASK_SECRET_KEY=your_secret_key_here
MAX_CONTENT_LENGTH=16777216  # 16MB max file size
```

## Dependencies

Main dependencies include:
- Flask
- OpenCV (cv2)
- Ultralytics YOLOv8
- PyTorch
- Werkzeug

For a complete list, see `requirements.txt`

## Security Notes

For production deployment:
- Change default admin credentials
- Use a proper database instead of in-memory storage
- Enable HTTPS
- Implement rate limiting
- Add email verification
- Use stronger password hashing
- Implement proper session management

## Troubleshooting

1. **CUDA errors**
   - Verify CUDA installation: `nvidia-smi`
   - Check PyTorch CUDA availability: 
     ```python
     import torch
     print(torch.cuda.is_available())
     ```

2. **File upload issues**
   - Check file size limits
   - Verify upload directory permissions
   - Ensure supported file formats (jpg, jpeg, png, mp4)

3. **Processing errors**
   - Check model file existence
   - Verify CUDA memory availability
   - Check log files for detailed error messages

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- YOLOv8 by Ultralytics
- Flask web framework
- OpenCV community 