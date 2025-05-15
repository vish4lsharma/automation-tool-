from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pandas as pd
import pytesseract
from PIL import Image
import PyPDF2
import io
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# In-memory storage for uploaded file metadata and content
file_storage = {}

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'xlsx', 'xls', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        file.save(file_path)

        file_extension = filename.rsplit('.', 1)[1].lower()
        content = extract_content(file_path, file_extension)

        file_storage[file_id] = {
            'id': file_id,  # ✅ Added this to fix search response
            'filename': filename,
            'path': file_path,
            'content': content,
            'type': file_extension
        }

        return jsonify({
            'id': file_id,
            'filename': filename,
            'type': file_extension,
            'message': 'File uploaded successfully'
        }), 200

    return jsonify({'error': 'File type not allowed'}), 400

def extract_content(file_path, file_extension):
    """Extract searchable content from various file types"""
    try:
        if file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(file_path)
            return df.to_dict(orient='records')
        elif file_extension == 'csv':
            df = pd.read_csv(file_path)
            return df.to_dict(orient='records')
        elif file_extension == 'pdf':
            text = ""
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return text
        elif file_extension in ['png', 'jpg', 'jpeg']:
            image = Image.open(file_path)
            return pytesseract.image_to_string(image)
            print(f"[DEBUG] Extracted content from {file_path}:\n{content[:500]}") 
        else:
            return "Unsupported file type"
    except Exception as e:
        print(f"[ERROR] Failed to extract content: {e}")
        return f"Error: {e}"

@app.route('/api/files', methods=['GET'])
def get_files():
    return jsonify([
        {
            'id': file_info['id'],
            'filename': file_info['filename'],
            'type': file_info['type']
        }
        for file_info in file_storage.values()
    ])

@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('query', '').lower()
    file_id = request.args.get('file_id')
    print("Search query:", query)

    if not query:
        return jsonify({'error': 'No search query provided'}), 400

    results = []

    if file_id and file_id in file_storage:
        # Search in a specific file
        file_info = file_storage[file_id]
        results = search_in_content(file_info['content'], query, file_info)
    else:
        # Search across all files
        for file_info in file_storage.values():
            results.extend(search_in_content(file_info['content'], query, file_info))

    return jsonify({
        'query': query,
        'results': results
    })
    print(f"[DEBUG] Search query: '{query}', File ID: {file_id}")


def search_in_content(content, query, file_info):
    matches = []

    if isinstance(content, list):  # Excel/CSV data
        for idx, row in enumerate(content):
            row_text = str(row).lower()
            if query in row_text:
                preview = str(row)[:100] + "..." if len(str(row)) > 100 else str(row)
                matches.append({
                    'file_id': file_info['id'],
                    'filename': file_info['filename'],
                    'type': file_info['type'],
                    'match': f"Row {idx + 1}: {row}",
                    'preview': preview
                })
        print(f"[DEBUG] Searching in: {file_info['filename']}, content type: {type(content)}")

    elif isinstance(content, str):  # Text from PDFs or images
        for idx, line in enumerate(content.splitlines()):
            if query in line.lower():
                preview = line[:100] + "..." if len(line) > 100 else line
                matches.append({
                    'file_id': file_info['id'],
                    'filename': file_info['filename'],
                    'type': file_info['type'],
                    'match': f"Line {idx + 1}: {line}",
                    'preview': preview
                })

    return matches
@app.route('/api/file-content', methods=['GET'])
def file_content():
    file_id = request.args.get('file_id')
    if not file_id or file_id not in file_storage:
        return jsonify({'error': 'File not found'}), 404
    return jsonify({
        'id': file_id,
        'filename': file_storage[file_id]['filename'],
        'type': file_storage[file_id]['type'],
        'content': file_storage[file_id]['content']
    })



if __name__ == '__main__':
    app.run(debug=True, port=5000)
