from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pandas as pd
import pytesseract
from PIL import Image
import PyPDF2
import io
import uuid
import logging
from werkzeug.utils import secure_filename
import re
from typing import List, Dict, Any, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# In-memory storage for uploaded file metadata and content
file_storage = {}

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'xlsx', 'xls', 'csv'}

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_text(text: str) -> str:
    """Clean and normalize text for better searching"""
    if not isinstance(text, str):
        return str(text)
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    return text

def safe_to_string(obj: Any) -> str:
    """Safely convert object to string"""
    if obj is None:
        return ""
    if isinstance(obj, (int, float)):
        return str(obj)
    if isinstance(obj, str):
        return obj
    try:
        return str(obj)
    except Exception:
        return ""

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload and process file with enhanced error handling"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in request'}), 400

        file = request.files['file']

        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': f'File type not allowed. Supported types: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

        # Generate secure filename and unique ID
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({'error': 'Invalid filename'}), 400
            
        file_id = str(uuid.uuid4())
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        
        # Save file
        file.save(file_path)
        logger.info(f"File saved: {filename} -> {file_path}")

        # Extract file extension
        file_extension = filename.rsplit('.', 1)[1].lower()
        
        # Extract content with enhanced error handling
        content, extraction_status = extract_content(file_path, file_extension)

        # Store file information
        file_storage[file_id] = {
            'id': file_id,
            'filename': filename,
            'path': file_path,
            'content': content,
            'type': file_extension,
            'extraction_status': extraction_status,
            'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }

        return jsonify({
            'id': file_id,
            'filename': filename,
            'type': file_extension,
            'extraction_status': extraction_status,
            'message': 'File uploaded and processed successfully'
        }), 200

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

def extract_content(file_path: str, file_extension: str) -> tuple[Any, str]:
    """Extract content from various file types with comprehensive error handling"""
    try:
        logger.info(f"Extracting content from {file_path} (type: {file_extension})")
        
        if file_extension in ['xlsx', 'xls']:
            try:
                # Try different engines for better compatibility
                df = pd.read_excel(file_path, engine='openpyxl' if file_extension == 'xlsx' else 'xlrd')
                
                # Handle empty dataframes
                if df.empty:
                    return [], "success_empty"
                
                # Clean and convert to records
                df = df.fillna('')  # Replace NaN with empty strings
                content = df.to_dict(orient='records')
                
                logger.info(f"Extracted {len(content)} rows from Excel file")
                return content, "success"
                
            except Exception as e:
                logger.error(f"Excel extraction error: {e}")
                return [], f"error: {str(e)}"
                
        elif file_extension == 'csv':
            try:
                # Try different encodings for better compatibility
                encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                df = None
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        logger.info(f"CSV read successfully with {encoding} encoding")
                        break
                    except UnicodeDecodeError:
                        continue
                
                if df is None:
                    return [], "error: Unable to decode CSV file"
                
                if df.empty:
                    return [], "success_empty"
                
                # Clean and convert to records
                df = df.fillna('')  # Replace NaN with empty strings
                content = df.to_dict(orient='records')
                
                logger.info(f"Extracted {len(content)} rows from CSV file")
                return content, "success"
                
            except Exception as e:
                logger.error(f"CSV extraction error: {e}")
                return [], f"error: {str(e)}"
                
        elif file_extension == 'pdf':
            try:
                text_content = []
                
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    
                    if len(reader.pages) == 0:
                        return "", "success_empty"
                    
                    for page_num, page in enumerate(reader.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text_content.append(clean_text(page_text))
                        except Exception as e:
                            logger.warning(f"Error extracting page {page_num}: {e}")
                            continue
                
                full_text = '\n'.join(text_content)
                logger.info(f"Extracted {len(full_text)} characters from PDF")
                return full_text, "success" if full_text.strip() else "success_empty"
                
            except Exception as e:
                logger.error(f"PDF extraction error: {e}")
                return "", f"error: {str(e)}"
                
        elif file_extension in ['png', 'jpg', 'jpeg']:
            try:
                image = Image.open(file_path)
                
                # Convert to RGB if necessary
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Extract text using OCR
                extracted_text = pytesseract.image_to_string(image, config='--psm 6')
                cleaned_text = clean_text(extracted_text)
                
                logger.info(f"Extracted {len(cleaned_text)} characters from image via OCR")
                return cleaned_text, "success" if cleaned_text.strip() else "success_empty"
                
            except Exception as e:
                logger.error(f"Image OCR error: {e}")
                return "", f"error: {str(e)}"
        else:
            return "", "error: Unsupported file type"
            
    except Exception as e:
        logger.error(f"General extraction error: {e}")
        return "", f"error: {str(e)}"

@app.route('/api/files', methods=['GET'])
def get_files():
    """Get list of all uploaded files with metadata"""
    try:
        files_list = []
        for file_info in file_storage.values():
            files_list.append({
                'id': file_info['id'],
                'filename': file_info['filename'],
                'type': file_info['type'],
                'extraction_status': file_info.get('extraction_status', 'unknown'),
                'size': file_info.get('size', 0)
            })
        
        return jsonify(files_list), 200
        
    except Exception as e:
        logger.error(f"Get files error: {e}")
        return jsonify({'error': f'Failed to retrieve files: {str(e)}'}), 500

@app.route('/api/search', methods=['GET'])
def search():
    """Enhanced search with better accuracy and error handling"""
    try:
        query = request.args.get('query', '').strip()
        file_id = request.args.get('file_id', '').strip()
        case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'
        
        logger.info(f"Search query: '{query}', File ID: '{file_id}', Case sensitive: {case_sensitive}")

        if not query:
            return jsonify({'error': 'No search query provided'}), 400

        results = []
        processed_files = 0

        if file_id and file_id in file_storage:
            # Search in specific file
            file_info = file_storage[file_id]
            if file_info.get('extraction_status', '').startswith('success'):
                results = search_in_content(file_info['content'], query, file_info, case_sensitive)
                processed_files = 1
            else:
                return jsonify({
                    'error': f'File content not available: {file_info.get("extraction_status", "unknown error")}'
                }), 400
        else:
            # Search across all files
            for file_info in file_storage.values():
                if file_info.get('extraction_status', '').startswith('success'):
                    file_results = search_in_content(file_info['content'], query, file_info, case_sensitive)
                    results.extend(file_results)
                    processed_files += 1

        return jsonify({
            'query': query,
            'case_sensitive': case_sensitive,
            'processed_files': processed_files,
            'total_matches': len(results),
            'results': results
        }), 200

    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

def search_in_content(content: Union[List[Dict], str], query: str, file_info: Dict, case_sensitive: bool = False) -> List[Dict]:
    """Enhanced content search with better accuracy"""
    matches = []
    
    try:
        # Prepare search query
        search_query = query if case_sensitive else query.lower()
        
        if isinstance(content, list):  # Excel/CSV data
            for idx, row in enumerate(content):
                if not isinstance(row, dict):
                    continue
                    
                # Search in all fields of the row
                row_matches = []
                for key, value in row.items():
                    value_str = safe_to_string(value)
                    search_text = value_str if case_sensitive else value_str.lower()
                    
                    if search_query in search_text:
                        # Find exact match positions for highlighting
                        start_pos = search_text.find(search_query)
                        end_pos = start_pos + len(search_query)
                        
                        row_matches.append({
                            'field': str(key),
                            'value': value_str,
                            'match_start': start_pos,
                            'match_end': end_pos
                        })
                
                if row_matches:
                    # Create preview with highlighted matches
                    preview_parts = []
                    for match in row_matches[:3]:  # Limit to first 3 matches per row
                        field_preview = f"{match['field']}: {match['value'][:100]}"
                        if len(match['value']) > 100:
                            field_preview += "..."
                        preview_parts.append(field_preview)
                    
                    preview = " | ".join(preview_parts)
                    
                    matches.append({
                        'file_id': file_info['id'],
                        'filename': file_info['filename'],
                        'type': file_info['type'],
                        'location': f"Row {idx + 1}",
                        'matches': row_matches,
                        'preview': preview,
                        'full_row': row
                    })

        elif isinstance(content, str):  # Text from PDFs or images
            lines = content.splitlines()
            for line_idx, line in enumerate(lines):
                search_text = line if case_sensitive else line.lower()
                
                if search_query in search_text:
                    # Find all occurrences in the line
                    start = 0
                    line_matches = []
                    
                    while True:
                        pos = search_text.find(search_query, start)
                        if pos == -1:
                            break
                        line_matches.append({
                            'match_start': pos,
                            'match_end': pos + len(search_query)
                        })
                        start = pos + 1
                    
                    # Create preview with context
                    preview = line.strip()
                    if len(preview) > 200:
                        # Try to center the first match in the preview
                        first_match = line_matches[0]['match_start']
                        start_preview = max(0, first_match - 100)
                        end_preview = min(len(line), first_match + 100)
                        preview = line[start_preview:end_preview].strip()
                        if start_preview > 0:
                            preview = "..." + preview
                        if end_preview < len(line):
                            preview = preview + "..."
                    
                    matches.append({
                        'file_id': file_info['id'],
                        'filename': file_info['filename'],
                        'type': file_info['type'],
                        'location': f"Line {line_idx + 1}",
                        'matches': line_matches,
                        'preview': preview,
                        'full_line': line.strip()
                    })

    except Exception as e:
        logger.error(f"Content search error: {e}")
    
    return matches

@app.route('/api/file-content', methods=['GET'])
def file_content():
    """Get complete file content with metadata"""
    try:
        file_id = request.args.get('file_id', '').strip()
        
        if not file_id:
            return jsonify({'error': 'File ID is required'}), 400
            
        if file_id not in file_storage:
            return jsonify({'error': 'File not found'}), 404
        
        file_info = file_storage[file_id]
        
        return jsonify({
            'id': file_id,
            'filename': file_info['filename'],
            'type': file_info['type'],
            'extraction_status': file_info.get('extraction_status', 'unknown'),
            'size': file_info.get('size', 0),
            'content': file_info['content']
        }), 200
        
    except Exception as e:
        logger.error(f"File content error: {e}")
        return jsonify({'error': f'Failed to retrieve file content: {str(e)}'}), 500

@app.route('/api/delete/<file_id>', methods=['DELETE'])
def delete_file(file_id: str):
    """Delete uploaded file and clean up storage"""
    try:
        if file_id not in file_storage:
            return jsonify({'error': 'File not found'}), 404
        
        file_info = file_storage[file_id]
        
        # Delete physical file
        if os.path.exists(file_info['path']):
            os.remove(file_info['path'])
            logger.info(f"Deleted file: {file_info['path']}")
        
        # Remove from storage
        del file_storage[file_id]
        
        return jsonify({'message': 'File deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Delete file error: {e}")
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    app.run(debug=True, port=5000)
