import os
import cv2
import uuid # To generate unique filenames
import logging
import json
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session, send_from_directory
from ultralytics import YOLO
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# --- Configuration ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__)) # Get base directory of the app
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'static', 'outputs')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4'} # Added mp4 for video
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'best.pt') # Path to your trained model
MAX_FILE_SIZE_MB = 16 # Maximum upload size in Megabytes

# --- Initialize Flask App ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE_MB * 1024 * 1024
# Generate a random secret key (important for production)
app.secret_key = os.urandom(24) # Use a random key for sessions/flash messages

# --- User Management ---
# In a real application, this would be in a database
USERS = {
    'admin': {
        'password': generate_password_hash('admin123'),
        'uploads_folder': 'admin'
    }
}

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Create directories if they don't exist ---
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    logging.info(f"Upload folder checked/created: {UPLOAD_FOLDER}")
    logging.info(f"Output folder checked/created: {OUTPUT_FOLDER}")
except OSError as e:
    logging.error(f"Error creating directories: {e}")
    exit(1) # Exit if we can't create essential folders


# --- Load the YOLO model ---
model = None
try:
    if os.path.exists(MODEL_PATH):
        model = YOLO(MODEL_PATH) # Attempting to add force_reload=True based on instruction, but it might not be a valid parameter for YOLO()
        logging.info(f"✅ YOLO model loaded successfully from {MODEL_PATH}")
    else:
        logging.error(f"🚨 CRITICAL: Model file not found at {MODEL_PATH}")
        # Model remains None, the route handler will prevent usage
except Exception as e:
    logging.error(f"🚨 CRITICAL: Error loading YOLO model from {MODEL_PATH}: {e}", exc_info=True)
    # Model remains None

# --- Authentication Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Helper Function ---
def allowed_file(filename):
    """Checks if the filename has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_folders(username):
    user_upload = os.path.join(UPLOAD_FOLDER, username)
    user_output = os.path.join(OUTPUT_FOLDER, username)
    os.makedirs(user_upload, exist_ok=True)
    os.makedirs(user_output, exist_ok=True)
    return user_upload, user_output

# --- Routes ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('upload_page'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not password:
            flash('Username and password are required.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        if username in USERS:
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))

        # Create new user
        USERS[username] = {
            'password': generate_password_hash(password),
            'uploads_folder': username
        }

        # Create user folders
        get_user_folders(username)

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('upload_page'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in USERS and check_password_hash(USERS[username]['password'], password):
            session['user_id'] = username
            session['username'] = username
            flash('Logged in successfully!', 'success')
            next_page = request.form.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('upload_page'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_page():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in the request.', 'warning')
            return redirect(request.url)
        file = request.files['file']

        if file.filename == '':
            flash('No selected file.', 'warning')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            extension = original_filename.rsplit('.', 1)[1].lower()
            unique_id = uuid.uuid4().hex
            unique_filename = f"{unique_id}.{extension}"

            # Get user-specific folders
            user_upload, user_output = get_user_folders(session['username'])
            upload_path = os.path.join(user_upload, unique_filename)

            try:
                file.save(upload_path)
                logging.info(f"✅ File '{original_filename}' saved to: {upload_path}")
                flash('File uploaded successfully! Click Process to start detection.', 'success')
                return render_template('index.html', uploaded_file=unique_filename)
            except Exception as e:
                logging.error(f"🚨 Error during upload for {original_filename}: {e}", exc_info=True)
                flash(f'An error occurred during upload: {e}', 'danger')
                return redirect(request.url)

        elif file and not allowed_file(file.filename):
            flash(f'Invalid file type: "{secure_filename(file.filename)}". Allowed types are {", ".join(ALLOWED_EXTENSIONS)}.', 'warning')
            return redirect(request.url)
        else:
            flash('An unexpected error occurred with the file upload.', 'danger')
            return redirect(request.url)

    return render_template('index.html')

# Add a new route for the main page that doesn't require login
@app.route('/main')
@login_required
def main_page():
    return render_template('index.html')

@app.route('/user_files/<path:filename>')
@login_required
def user_files(filename):
    """Serve files from user's output directory"""
    user_output = os.path.join(OUTPUT_FOLDER, session['username'])
    try:
        return send_from_directory(user_output, filename)
    except Exception as e:
        logging.error(f"Error serving file {filename}: {e}")
        return "File not found", 404

@app.route('/get_processed_files')
@login_required
def get_processed_files():
    """Returns a list of processed files with their details."""
    files = []
    try:
        # Get user-specific output directory
        user_output = os.path.join(OUTPUT_FOLDER, session['username'])
        if not os.path.exists(user_output):
            return jsonify([])

        for filename in os.listdir(user_output):
            if filename.endswith('.json'):  # Skip metadata files
                continue
            file_path = os.path.join(user_output, filename)
            if os.path.isfile(file_path):
                # Get file type
                extension = filename.rsplit('.', 1)[1].lower()
                file_type = 'video' if extension == 'mp4' else 'image'
                
                # Try to get detection count from metadata
                metadata_path = os.path.join(user_output, f"{filename}.json")
                detections = 0
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            detections = metadata.get('detection_count', 0)
                    except:
                        pass

                files.append({
                    'name': filename,
                    'type': file_type,
                    'detections': detections,
                    'url': url_for('user_files', filename=filename)
                })
    except Exception as e:
        logging.error(f"Error getting processed files: {e}")
        return jsonify([])

    return jsonify(files)

@app.route('/clear_results', methods=['POST'])
@login_required
def clear_results():
    """Clears all processed files for the current user."""
    try:
        # Get user-specific directories
        user_upload, user_output = get_user_folders(session['username'])
        
        # Clear user's output directory
        for filename in os.listdir(user_output):
            file_path = os.path.join(user_output, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        # Clear user's upload directory
        for filename in os.listdir(user_upload):
            file_path = os.path.join(user_upload, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

        return jsonify({'success': True, 'message': 'All results cleared successfully'})
    except Exception as e:
        logging.error(f"Error clearing results: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/process/<filename>', methods=['POST'])
@login_required
def process_file(filename):
    """Handles processing of uploaded file."""
    if model is None:
        return jsonify({'error': 'Object detection model is not available'}), 500

    # Get user-specific folders
    user_upload, user_output = get_user_folders(session['username'])
    
    # Clear previous results for this user
    try:
        for old_file in os.listdir(user_output):
            old_file_path = os.path.join(user_output, old_file)
            if os.path.isfile(old_file_path):
                os.remove(old_file_path)
    except Exception as e:
        logging.warning(f"Error clearing previous results: {e}")

    file_path = os.path.join(user_upload, filename)
    output_path = os.path.join(user_output, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404

    # Check if file has already been processed
    if os.path.exists(output_path):
        extension = filename.rsplit('.', 1)[1].lower()
        # Try to get metadata
        metadata_path = os.path.join(user_output, f"{filename}.json")
        metadata = {}
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            except:
                pass
        
        return jsonify({
            'success': True,
            'message': 'File has already been processed.',
            'filename': filename,
            'file_type': 'video' if extension == 'mp4' else 'image',
            'detection_count': metadata.get('detection_count', 0),
            'frame_count': metadata.get('frame_count', 0)
        })

    try:
        extension = filename.rsplit('.', 1)[1].lower()
        
        if extension in {'png', 'jpg', 'jpeg'}:
            # Image processing
            logging.info(f"🧠 Running image inference on: {file_path}")
            results = model(file_path, save=False, verbose=False, conf=0.3)

            if results and results[0] and len(results[0].boxes) > 0:
                annotated_image = results[0].plot()
                if cv2.imwrite(output_path, annotated_image):
                    detection_count = len(results[0].boxes)
                    logging.info(f"✅ Annotated image saved to: {output_path}")
                    
                    # Save metadata
                    metadata = {
                        'detection_count': detection_count,
                        'frame_count': 1
                    }
                    metadata_path = os.path.join(user_output, f"{filename}.json")
                    with open(metadata_path, 'w') as f:
                        json.dump(metadata, f)
                    
                    return jsonify({
                        'success': True,
                        'message': f'Detection complete! Found {detection_count} object(s).',
                        'filename': filename,
                        'file_type': 'image',
                        'detection_count': detection_count,
                        'frame_count': 1
                    })
            else:
                return jsonify({
                    'success': True,
                    'message': 'No pistols detected in the image.',
                    'filename': None
                })

        elif extension == 'mp4':
            # Video processing
            logging.info(f"🧠 Running video inference on: {file_path}")
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                return jsonify({'error': 'Error opening video file'}), 500

            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 25

            # Try Windows-friendly codecs first
            codecs = [
                ('XVID', cv2.VideoWriter_fourcc(*'XVID')),
                ('DIVX', cv2.VideoWriter_fourcc(*'DIVX')),
                ('mp4v', cv2.VideoWriter_fourcc(*'mp4v')),
                ('WMV2', cv2.VideoWriter_fourcc(*'WMV2')),
            ]

            # First create a temporary AVI file which is more reliable
            temp_avi = os.path.join(user_output, f"temp_{filename}.avi")
            out = None
            
            for codec_name, codec in codecs:
                try:
                    out = cv2.VideoWriter(temp_avi, codec, fps, (frame_width, frame_height))
                    if out.isOpened():
                        logging.info(f"Successfully opened VideoWriter with codec: {codec_name}")
                        break
                except Exception as e:
                    logging.warning(f"Failed to initialize codec {codec_name}: {str(e)}")
                    if out is not None:
                        out.release()
                    out = None

            if out is None:
                return jsonify({'error': 'Could not initialize video encoder with any available codec'}), 500

            frame_count = 0
            detection_count = 0
            logging.info(f"Processing video frame by frame...")
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                results = model(frame, save=False, verbose=False, conf=0.3)
                annotated_frame = results[0].plot()
                current_detections = len(results[0].boxes)
                if current_detections > 0:
                    detection_count += current_detections
                out.write(annotated_frame)

            cap.release()
            out.release()

            # Now convert AVI to MP4 using cv2.VideoWriter
            try:
                cap = cv2.VideoCapture(temp_avi)
                if not cap.isOpened():
                    raise Exception("Failed to open temporary AVI file")

                out_mp4 = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (frame_width, frame_height))
                if not out_mp4.isOpened():
                    raise Exception("Failed to create MP4 file")

                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out_mp4.write(frame)

                cap.release()
                out_mp4.release()
                os.remove(temp_avi)  # Clean up temporary file

            except Exception as e:
                logging.warning(f"Failed to convert to MP4, using AVI file: {str(e)}")
                # If conversion fails, just use the AVI file
                os.rename(temp_avi, output_path)

            logging.info(f"✅ Processed {frame_count} frames. Found {detection_count} total object detections.")

            # After processing, save metadata
            metadata = {
                'detection_count': detection_count,
                'frame_count': frame_count
            }
            metadata_path = os.path.join(user_output, f"{filename}.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)

            if os.path.exists(output_path):
                return jsonify({
                    'success': True,
                    'message': f'Video processing complete! Found {detection_count} object(s) across {frame_count} frames.',
                    'filename': filename,
                    'file_type': 'video',
                    'detection_count': detection_count,
                    'frame_count': frame_count
                })
            else:
                return jsonify({'error': 'Failed to save processed video'}), 500

    except Exception as e:
        logging.error(f"🚨 Error during processing: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# --- Error Handling ---
@app.errorhandler(413) # Handles 'RequestEntityTooLarge' error
def request_entity_too_large(error):
    flash(f'File is too large. Maximum size is {MAX_FILE_SIZE_MB} MB.', 'danger')
    return redirect(request.url)

# Optional: Serve static files directly (Flask does this by default, but explicit can be clearer)
# from flask import send_from_directory
# @app.route('/static/<path:filename>')
# def static_files(filename):
#    return send_from_directory(app.static_folder, filename)


# --- Run the App ---
if __name__ == '__main__':
    logging.info("🚀 Starting Flask development server...")
    # Use host='0.0.0.0' to make it accessible on your local network
    # Use port=5000 (default) or choose another
    # debug=True enables auto-reloading and provides detailed error pages (DISABLE in production)
    app.run(debug=True, host='0.0.0.0', port=5000)