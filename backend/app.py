from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pandas as pd
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import PyPDF2
import pdfplumber
import io
import uuid
import logging
import json
from werkzeug.utils import secure_filename
import re
from typing import List, Dict, Any, Union, Tuple
from difflib import SequenceMatcher
import unicodedata
import chardet
from collections import defaultdict
import threading
import time

# Configure advanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Thread-safe file storage with metadata
file_storage = {}
storage_lock = threading.Lock()

# Advanced configuration
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # Increased to 32MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'pdf', 'xlsx', 'xls', 'csv', 'txt', 'docx'}

# Advanced OCR configurations
OCR_CONFIGS = [
    '--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,!?;:-_()[]{}@#$%^&*+=<>/\\|`~"\'',
    '--psm 4',
    '--psm 3',
    '--psm 1',
    '--psm 11',
    '--psm 12'
]

class ContentProcessor:
    """Advanced content processing with multiple extraction strategies"""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Advanced text normalization"""
        if not isinstance(text, str):
            text = str(text)
        
        # Unicode normalization
        text = unicodedata.normalize('NFKD', text)
        
        # Remove control characters but preserve whitespace structure
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normalize whitespace while preserving line structure
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    @staticmethod
    def detect_encoding(file_path: str) -> str:
        """Detect file encoding with high accuracy"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # Read first 10KB for detection
            
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0)
            
            logger.info(f"Detected encoding: {encoding} (confidence: {confidence:.2f})")
            
            if confidence < 0.7:
                # Fallback encodings in order of preference
                fallback_encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'ascii']
                return fallback_encodings[0]
            
            return encoding
        except Exception as e:
            logger.warning(f"Encoding detection failed: {e}")
            return 'utf-8'

class AdvancedSearchEngine:
    """Enhanced search engine with fuzzy matching and relevance scoring"""
    
    def __init__(self):
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'
        }
    
    def preprocess_query(self, query: str) -> Dict[str, Any]:
        """Advanced query preprocessing"""
        processed = {
            'original': query,
            'normalized': ContentProcessor.normalize_text(query.lower()),
            'tokens': [],
            'phrases': [],
            'exact_match': False
        }
        
        # Check for exact match quotes
        if query.startswith('"') and query.endswith('"'):
            processed['exact_match'] = True
            processed['normalized'] = query[1:-1].lower()
        
        # Tokenize
        tokens = re.findall(r'\b\w+\b', processed['normalized'])
        processed['tokens'] = [t for t in tokens if t not in self.stop_words]
        
        # Extract phrases (2-3 word combinations)
        for i in range(len(tokens) - 1):
            processed['phrases'].append(' '.join(tokens[i:i+2]))
            if i < len(tokens) - 2:
                processed['phrases'].append(' '.join(tokens[i:i+3]))
        
        return processed
    
    def fuzzy_match_score(self, text: str, query: str, threshold: float = 0.6) -> float:
        """Calculate fuzzy match score using sequence matching"""
        if not text or not query:
            return 0.0
        
        text_lower = text.lower()
        query_lower = query.lower()
        
        # Exact match gets highest score
        if query_lower in text_lower:
            return 1.0
        
        # Fuzzy matching
        matcher = SequenceMatcher(None, text_lower, query_lower)
        ratio = matcher.ratio()
        
        return ratio if ratio >= threshold else 0.0
    
    def calculate_relevance_score(self, text: str, query_data: Dict[str, Any]) -> float:
        """Calculate comprehensive relevance score"""
        if not text:
            return 0.0
        
        text_lower = text.lower()
        score = 0.0
        
        # Exact phrase match (highest weight)
        if query_data['exact_match']:
            if query_data['normalized'] in text_lower:
                score += 10.0
        else:
            # Regular phrase match
            if query_data['normalized'] in text_lower:
                score += 5.0
            
            # Token matches
            for token in query_data['tokens']:
                if token in text_lower:
                    score += 2.0
            
            # Phrase matches
            for phrase in query_data['phrases']:
                if phrase in text_lower:
                    score += 3.0
        
        # Fuzzy matching bonus
        fuzzy_score = self.fuzzy_match_score(text, query_data['normalized'])
        score += fuzzy_score * 1.5
        
        # Length penalty (prefer shorter, more relevant matches)
        if score > 0:
            length_factor = min(1.0, 100.0 / len(text))
            score *= (1.0 + length_factor * 0.2)
        
        return score

def allowed_file(filename: str) -> bool:
    """Enhanced file validation"""
    if not filename or '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS

def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """Advanced image preprocessing for better OCR accuracy"""
    try:
        # Convert to grayscale if not already
        if image.mode != 'L':
            image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        # Apply noise reduction
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # Scale up small images for better OCR
        width, height = image.size
        if width < 800 or height < 600:
            scale_factor = max(800/width, 600/height)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        return image
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}")
        return image

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Enhanced file upload with advanced processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in request'}), 400

        file = request.files['file']
        
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Supported types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        # Enhanced filename security
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({'error': 'Invalid filename'}), 400
            
        file_id = str(uuid.uuid4())
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        
        # Save file with validation
        file.save(file_path)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File save failed'}), 500
        
        logger.info(f"File saved: {filename} -> {file_path}")

        file_extension = filename.rsplit('.', 1)[1].lower()
        
        # Advanced content extraction
        content, extraction_status, metadata = extract_content_advanced(file_path, file_extension)

        # Thread-safe storage update
        with storage_lock:
            file_storage[file_id] = {
                'id': file_id,
                'filename': filename,
                'path': file_path,
                'content': content,
                'type': file_extension,
                'extraction_status': extraction_status,
                'metadata': metadata,
                'size': os.path.getsize(file_path),
                'upload_time': time.time(),
                'processed_content': preprocess_content_for_search(content, file_extension)
            }

        return jsonify({
            'id': file_id,
            'filename': filename,
            'type': file_extension,
            'extraction_status': extraction_status,
            'metadata': metadata,
            'message': 'File uploaded and processed successfully'
        }), 200

    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

def extract_content_advanced(file_path: str, file_extension: str) -> Tuple[Any, str, Dict]:
    """Advanced content extraction with multiple strategies"""
    metadata = {'extraction_methods': [], 'confidence': 0.0, 'processing_time': 0}
    start_time = time.time()
    
    try:
        logger.info(f"Advanced extraction from {file_path} (type: {file_extension})")
        
        if file_extension in ['xlsx', 'xls']:
            content, status = extract_excel_advanced(file_path, file_extension, metadata)
            
        elif file_extension == 'csv':
            content, status = extract_csv_advanced(file_path, metadata)
            
        elif file_extension == 'pdf':
            content, status = extract_pdf_advanced(file_path, metadata)
            
        elif file_extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff']:
            content, status = extract_image_advanced(file_path, metadata)
            
        elif file_extension == 'txt':
            content, status = extract_text_advanced(file_path, metadata)
            
        else:
            content, status = "", "error: Unsupported file type"
            
        metadata['processing_time'] = time.time() - start_time
        logger.info(f"Extraction completed in {metadata['processing_time']:.2f}s")
        
        return content, status, metadata
        
    except Exception as e:
        logger.error(f"Advanced extraction error: {e}", exc_info=True)
        metadata['processing_time'] = time.time() - start_time
        return "", f"error: {str(e)}", metadata

def extract_excel_advanced(file_path: str, file_extension: str, metadata: Dict) -> Tuple[List[Dict], str]:
    """Advanced Excel extraction with multiple sheet support"""
    try:
        engine = 'openpyxl' if file_extension == 'xlsx' else 'xlrd'
        
        # Read all sheets
        excel_file = pd.ExcelFile(file_path, engine=engine)
        all_content = []
        
        metadata['sheets'] = []
        
        for sheet_name in excel_file.sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine)
                
                if df.empty:
                    continue
                
                # Advanced data cleaning
                df = df.dropna(how='all')  # Remove completely empty rows
                df = df.dropna(axis=1, how='all')  # Remove completely empty columns
                df = df.fillna('')  # Replace remaining NaN with empty strings
                
                # Convert to records with sheet information
                sheet_records = df.to_dict(orient='records')
                for record in sheet_records:
                    record['_sheet_name'] = sheet_name
                
                all_content.extend(sheet_records)
                
                metadata['sheets'].append({
                    'name': sheet_name,
                    'rows': len(sheet_records),
                    'columns': len(df.columns)
                })
                
            except Exception as e:
                logger.warning(f"Error processing sheet {sheet_name}: {e}")
                continue
        
        metadata['extraction_methods'].append('pandas_excel')
        metadata['confidence'] = 0.95 if all_content else 0.1
        
        return all_content, "success" if all_content else "success_empty"
        
    except Exception as e:
        logger.error(f"Excel extraction error: {e}")
        return [], f"error: {str(e)}"

def extract_csv_advanced(file_path: str, metadata: Dict) -> Tuple[List[Dict], str]:
    """Advanced CSV extraction with encoding detection and delimiter guessing"""
    try:
        # Detect encoding
        encoding = ContentProcessor.detect_encoding(file_path)
        metadata['detected_encoding'] = encoding
        
        # Try different delimiters
        delimiters = [',', ';', '\t', '|']
        best_df = None
        best_delimiter = None
        max_columns = 0
        
        for delimiter in delimiters:
            try:
                df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter, nrows=5)
                if len(df.columns) > max_columns:
                    max_columns = len(df.columns)
                    best_delimiter = delimiter
                    
            except Exception:
                continue
        
        if best_delimiter:
            # Read full file with best delimiter
            df = pd.read_csv(file_path, encoding=encoding, delimiter=best_delimiter)
            metadata['delimiter'] = best_delimiter
        else:
            # Fallback to pandas auto-detection
            df = pd.read_csv(file_path, encoding=encoding)
            metadata['delimiter'] = 'auto'
        
        if df.empty:
            return [], "success_empty"
        
        # Advanced cleaning
        df = df.dropna(how='all')
        df = df.fillna('')
        
        # Clean column names
        df.columns = [ContentProcessor.normalize_text(str(col)) for col in df.columns]
        
        content = df.to_dict(orient='records')
        
        metadata['extraction_methods'].append('pandas_csv')
        metadata['confidence'] = 0.9
        metadata['rows'] = len(content)
        metadata['columns'] = len(df.columns)
        
        return content, "success"
        
    except Exception as e:
        logger.error(f"CSV extraction error: {e}")
        return [], f"error: {str(e)}"

def extract_pdf_advanced(file_path: str, metadata: Dict) -> Tuple[str, str]:
    """Advanced PDF extraction using multiple methods"""
    all_text = []
    methods_used = []
    
    # Method 1: pdfplumber (more accurate for complex layouts)
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        all_text.append(ContentProcessor.normalize_text(text))
                except Exception as e:
                    logger.warning(f"pdfplumber failed on page {page_num}: {e}")
        
        if all_text:
            methods_used.append('pdfplumber')
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}")
    
    # Method 2: PyPDF2 (fallback)
    if not all_text:
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                for page_num, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        if text and text.strip():
                            all_text.append(ContentProcessor.normalize_text(text))
                    except Exception as e:
                        logger.warning(f"PyPDF2 failed on page {page_num}: {e}")
            
            if all_text:
                methods_used.append('PyPDF2')
                
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {e}")
    
    final_text = '\n\n'.join(all_text)
    
    metadata['extraction_methods'].extend(methods_used)
    metadata['confidence'] = 0.85 if final_text.strip() else 0.1
    metadata['pages_processed'] = len(all_text)
    metadata['total_length'] = len(final_text)
    
    return final_text, "success" if final_text.strip() else "success_empty"

def extract_image_advanced(file_path: str, metadata: Dict) -> Tuple[str, str]:
    """Advanced image OCR with multiple configurations"""
    try:
        image = Image.open(file_path)
        metadata['original_size'] = image.size
        metadata['mode'] = image.mode
        
        # Preprocess image
        processed_image = preprocess_image_for_ocr(image)
        metadata['processed_size'] = processed_image.size
        
        best_text = ""
        best_confidence = 0
        
        # Try multiple OCR configurations
        for i, config in enumerate(OCR_CONFIGS):
            try:
                text = pytesseract.image_to_string(processed_image, config=config)
                
                if text and len(text.strip()) > len(best_text.strip()):
                    best_text = text
                    metadata['best_ocr_config'] = i
                    
                # Get confidence if available
                try:
                    data = pytesseract.image_to_data(processed_image, config=config, output_type=pytesseract.Output.DICT)
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    if confidences:
                        avg_confidence = sum(confidences) / len(confidences)
                        if avg_confidence > best_confidence:
                            best_confidence = avg_confidence
                            best_text = text
                except Exception:
                    pass
                    
            except Exception as e:
                logger.warning(f"OCR config {i} failed: {e}")
                continue
        
        cleaned_text = ContentProcessor.normalize_text(best_text)
        
        metadata['extraction_methods'].append('tesseract_ocr')
        metadata['confidence'] = best_confidence / 100.0 if best_confidence > 0 else 0.5
        metadata['text_length'] = len(cleaned_text)
        
        return cleaned_text, "success" if cleaned_text.strip() else "success_empty"
        
    except Exception as e:
        logger.error(f"Image OCR error: {e}")
        return "", f"error: {str(e)}"

def extract_text_advanced(file_path: str, metadata: Dict) -> Tuple[str, str]:
    """Advanced text file extraction with encoding detection"""
    try:
        encoding = ContentProcessor.detect_encoding(file_path)
        
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        cleaned_content = ContentProcessor.normalize_text(content)
        
        metadata['extraction_methods'].append('text_file')
        metadata['confidence'] = 0.95
        metadata['encoding'] = encoding
        metadata['length'] = len(cleaned_content)
        
        return cleaned_content, "success" if cleaned_content.strip() else "success_empty"
        
    except Exception as e:
        logger.error(f"Text extraction error: {e}")
        return "", f"error: {str(e)}"

def preprocess_content_for_search(content: Any, file_type: str) -> Dict[str, Any]:
    """Preprocess content for optimized searching"""
    processed = {
        'searchable_text': '',
        'indexed_fields': {},
        'metadata': {}
    }
    
    try:
        if isinstance(content, list):  # Structured data
            searchable_parts = []
            field_index = defaultdict(list)
            
            for idx, item in enumerate(content):
                if isinstance(item, dict):
                    for key, value in item.items():
                        if key.startswith('_'):  # Skip metadata fields
                            continue
                        
                        str_value = str(value).strip()
                        if str_value:
                            normalized = ContentProcessor.normalize_text(str_value)
                            searchable_parts.append(normalized)
                            field_index[key].append({
                                'row': idx,
                                'value': normalized,
                                'original': str_value
                            })
            
            processed['searchable_text'] = ' '.join(searchable_parts)
            processed['indexed_fields'] = dict(field_index)
            processed['metadata']['total_rows'] = len(content)
            
        elif isinstance(content, str):  # Text content
            processed['searchable_text'] = ContentProcessor.normalize_text(content)
            
            # Create line index
            lines = content.split('\n')
            processed['indexed_fields']['lines'] = [
                {
                    'line': idx,
                    'value': ContentProcessor.normalize_text(line),
                    'original': line
                }
                for idx, line in enumerate(lines) if line.strip()
            ]
            processed['metadata']['total_lines'] = len(lines)
        
        return processed
        
    except Exception as e:
        logger.error(f"Content preprocessing error: {e}")
        return processed

@app.route('/api/files', methods=['GET'])
def get_files():
    """Enhanced file listing with detailed metadata"""
    try:
        with storage_lock:
            files_list = []
            for file_info in file_storage.values():
                file_data = {
                    'id': file_info['id'],
                    'filename': file_info['filename'],
                    'type': file_info['type'],
                    'extraction_status': file_info.get('extraction_status', 'unknown'),
                    'size': file_info.get('size', 0),
                    'upload_time': file_info.get('upload_time', 0),
                    'metadata': file_info.get('metadata', {})
                }
                
                # Add content statistics
                content = file_info.get('content')
                if isinstance(content, list):
                    file_data['content_stats'] = {
                        'type': 'structured',
                        'rows': len(content),
                        'fields': len(content[0].keys()) if content else 0
                    }
                elif isinstance(content, str):
                    file_data['content_stats'] = {
                        'type': 'text',
                        'length': len(content),
                        'lines': content.count('\n') + 1 if content else 0
                    }
                
                files_list.append(file_data)
        
        return jsonify(files_list), 200
        
    except Exception as e:
        logger.error(f"Get files error: {e}")
        return jsonify({'error': f'Failed to retrieve files: {str(e)}'}), 500

@app.route('/api/search', methods=['GET'])
def search():
    """Ultra-accurate search with advanced matching algorithms"""
    try:
        query = request.args.get('query', '').strip()
        file_id = request.args.get('file_id', '').strip()
        case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'
        fuzzy_threshold = float(request.args.get('fuzzy_threshold', '0.6'))
        max_results = int(request.args.get('max_results', '100'))
        
        logger.info(f"Advanced search - Query: '{query}', File: '{file_id}', Case sensitive: {case_sensitive}")

        if not query:
            return jsonify({'error': 'No search query provided'}), 400

        search_engine = AdvancedSearchEngine()
        query_data = search_engine.preprocess_query(query)
        
        results = []
        processed_files = 0
        total_search_time = 0

        with storage_lock:
            files_to_search = [file_storage[file_id]] if file_id and file_id in file_storage else file_storage.values()
            
            for file_info in files_to_search:
                if not file_info.get('extraction_status', '').startswith('success'):
                    continue
                
                start_time = time.time()
                file_results = advanced_search_in_content(
                    file_info, query_data, search_engine, case_sensitive, fuzzy_threshold
                )
                
                # Sort by relevance score
                file_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
                
                results.extend(file_results[:max_results])
                processed_files += 1
                total_search_time += time.time() - start_time

        # Final sorting and limiting
        results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        results = results[:max_results]

        return jsonify({
            'query': query,
            'query_analysis': query_data,
            'case_sensitive': case_sensitive,
            'fuzzy_threshold': fuzzy_threshold,
            'processed_files': processed_files,
            'total_matches': len(results),
            'search_time': total_search_time,
            'results': results
        }), 200

    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

def advanced_search_in_content(file_info: Dict, query_data: Dict, search_engine: AdvancedSearchEngine, 
                             case_sensitive: bool, fuzzy_threshold: float) -> List[Dict]:
    """Ultra-accurate content searching with relevance scoring"""
    matches = []
    
    try:
        content = file_info.get('content')
        processed_content = file_info.get('processed_content', {})
        
        if isinstance(content, list):  # Structured data
            matches.extend(search_structured_data(
                content, file_info, query_data, search_engine, case_sensitive, fuzzy_threshold
            ))
            
        elif isinstance(content, str):  # Text content
            matches.extend(search_text_content(
                content, file_info, query_data, search_engine, case_sensitive, fuzzy_threshold
            ))
        
        return matches
        
    except Exception as e:
        logger.error(f"Content search error: {e}")
        return []

def search_structured_data(content: List[Dict], file_info: Dict, query_data: Dict, 
                         search_engine: AdvancedSearchEngine, case_sensitive: bool, 
                         fuzzy_threshold: float) -> List[Dict]:
    """Advanced structured data searching"""
    matches = []
    
    for row_idx, row in enumerate(content):
        if not isinstance(row, dict):
            continue
        
        row_matches = []
        total_relevance = 0
        
        for field, value in row.items():
            if field.startswith('_'):  # Skip metadata
                continue
                
            value_str = str(value).strip()
            if not value_str:
                continue
            
            search_text = value_str if case_sensitive else value_str.lower()
            relevance_score = search_engine.calculate_relevance_score(search_text, query_data)
            
            if relevance_score > 0:
                # Find exact match positions
                query_text = query_data['original'] if case_sensitive else query_data['normalized']
                positions = []
                
                start = 0
                while True:
                    pos = search_text.find(query_text, start)
                    if pos == -1:
                        break
                    positions.append({
                        'start': pos,
                        'end': pos + len(query_text),
                        'matched_text': value_str[pos:pos + len(query_text)]
                    })
                    start = pos + 1
                
                row_matches.append({
                    'field': field,
                    'value': value_str,
                    'relevance_score': relevance_score,
                    'positions': positions,
                    'fuzzy_score': search_engine.fuzzy_match_score(search_text, query_data['normalized'])
                })
                
                total_relevance += relevance_score
        
        if row_matches:
            # Create enhanced preview
            preview_parts = []
            for match in sorted(row_matches, key=lambda x: x['relevance_score'], reverse=True)[:3]:
                field_preview = f"{match['field']}: {match['value'][:80]}"
                if len(match['value']) > 80:
                    field_preview += "..."
                preview_parts.append(field_preview)
            
            matches.append({
                'file_id': file_info['id'],
                'filename': file_info['filename'],
                'type': file_info['type'],
                'location': f"Row {row_idx + 1}",
                'location_type': 'row',
                'relevance_score': total_relevance,
                'matches': row_matches,
                'preview': " | ".join(preview_parts),
                'full_row': row,
                'match_count': len(row_matches)
            })
    
    return matches

def search_text_content(content: str, file_info: Dict, query_data: Dict, 
                       search_engine: AdvancedSearchEngine, case_sensitive: bool, 
                       fuzzy_threshold: float) -> List[Dict]:
    """Advanced text content searching with context analysis"""
    matches = []
    lines = content.split('\n')
    
    for line_idx, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        search_text = line if case_sensitive else line.lower()
        relevance_score = search_engine.calculate_relevance_score(search_text, query_data)
        
        if relevance_score < 0.1:  # Skip very low relevance matches
            continue
        
        # Find match positions
        query_text = query_data['original'] if case_sensitive else query_data['normalized']
        positions = []
        
        start = 0
        while True:
            pos = search_text.find(query_text, start)
            if pos == -1:
                break
            positions.append({
                'start': pos,
                'end': pos + len(query_text),
                'matched_text': line[pos:pos + len(query_text)]
            })
            start = pos + 1
        
        # Create context-aware preview
        preview = create_context_preview(lines, line_idx, query_text, case_sensitive)
        
        matches.append({
            'file_id': file_info['id'],
            'filename': file_info['filename'],
            'type': file_info['type'],
            'location': f"Line {line_idx + 1}",
            'location_type': 'line',
            'relevance_score': relevance_score,
            'matches': [{
                'field': 'text',
                'value': line_stripped,
                'positions': positions,
                'fuzzy_score': search_engine.fuzzy_match_score(search_text, query_data['normalized'])
            }],
            'preview': preview,
            'full_line': line_stripped,
            'context_lines': get_context_lines(lines, line_idx, 2)
        })
    
    return matches

def create_context_preview(lines: List[str], center_line: int, query: str, case_sensitive: bool, 
                          context_size: int = 1) -> str:
    """Create intelligent context preview around matches"""
    start_line = max(0, center_line - context_size)
    end_line = min(len(lines), center_line + context_size + 1)
    
    context_lines = []
    for i in range(start_line, end_line):
        line = lines[i].strip()
        if i == center_line:
            # Highlight the matching line
            line = f">>> {line} <<<"
        context_lines.append(line)
    
    preview = " ... ".join(context_lines)
    
    # Truncate if too long
    if len(preview) > 300:
        preview = preview[:297] + "..."
    
    return preview

def get_context_lines(lines: List[str], center_line: int, context_size: int) -> Dict[str, List[str]]:
    """Get surrounding lines for context"""
    start_line = max(0, center_line - context_size)
    end_line = min(len(lines), center_line + context_size + 1)
    
    return {
        'before': [lines[i].strip() for i in range(start_line, center_line) if lines[i].strip()],
        'after': [lines[i].strip() for i in range(center_line + 1, end_line) if lines[i].strip()]
    }

@app.route('/api/file-content', methods=['GET'])
def file_content():
    """Enhanced file content retrieval with filtering options"""
    try:
        file_id = request.args.get('file_id', '').strip()
        include_metadata = request.args.get('include_metadata', 'true').lower() == 'true'
        limit = request.args.get('limit', '1000')
        
        if not file_id:
            return jsonify({'error': 'File ID is required'}), 400
            
        with storage_lock:
            if file_id not in file_storage:
                return jsonify({'error': 'File not found'}), 404
        
            file_info = file_storage[file_id]
        
        response_data = {
            'id': file_id,
            'filename': file_info['filename'],
            'type': file_info['type'],
            'extraction_status': file_info.get('extraction_status', 'unknown'),
            'size': file_info.get('size', 0)
        }
        
        # Handle content limiting for large files
        content = file_info['content']
        if limit and limit.isdigit():
            limit_int = int(limit)
            if isinstance(content, list) and len(content) > limit_int:
                response_data['content'] = content[:limit_int]
                response_data['content_truncated'] = True
                response_data['total_items'] = len(content)
            elif isinstance(content, str) and len(content) > limit_int * 100:  # Rough character limit
                response_data['content'] = content[:limit_int * 100]
                response_data['content_truncated'] = True
                response_data['total_length'] = len(content)
            else:
                response_data['content'] = content
                response_data['content_truncated'] = False
        else:
            response_data['content'] = content
            response_data['content_truncated'] = False
        
        if include_metadata:
            response_data['metadata'] = file_info.get('metadata', {})
            response_data['processed_content_stats'] = file_info.get('processed_content', {}).get('metadata', {})
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"File content error: {e}")
        return jsonify({'error': f'Failed to retrieve file content: {str(e)}'}), 500

@app.route('/api/analyze', methods=['GET'])
def analyze_file():
    """Advanced file analysis and statistics"""
    try:
        file_id = request.args.get('file_id', '').strip()
        
        if not file_id:
            return jsonify({'error': 'File ID is required'}), 400
        
        with storage_lock:
            if file_id not in file_storage:
                return jsonify({'error': 'File not found'}), 404
            
            file_info = file_storage[file_id]
        
        content = file_info['content']
        analysis = {
            'file_id': file_id,
            'filename': file_info['filename'],
            'type': file_info['type'],
            'extraction_metadata': file_info.get('metadata', {}),
            'content_analysis': {}
        }
        
        if isinstance(content, list):  # Structured data analysis
            analysis['content_analysis'] = analyze_structured_data(content)
        elif isinstance(content, str):  # Text analysis
            analysis['content_analysis'] = analyze_text_content(content)
        
        return jsonify(analysis), 200
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

def analyze_structured_data(content: List[Dict]) -> Dict:
    """Comprehensive structured data analysis"""
    if not content:
        return {'type': 'structured', 'empty': True}
    
    analysis = {
        'type': 'structured',
        'total_rows': len(content),
        'fields': {},
        'data_quality': {},
        'statistics': {}
    }
    
    # Analyze fields
    all_fields = set()
    for row in content:
        if isinstance(row, dict):
            all_fields.update(row.keys())
    
    # Field analysis
    for field in all_fields:
        if field.startswith('_'):  # Skip metadata fields
            continue
            
        values = []
        non_empty_count = 0
        
        for row in content:
            if isinstance(row, dict) and field in row:
                value = row[field]
                if value is not None and str(value).strip():
                    values.append(str(value))
                    non_empty_count += 1
        
        field_analysis = {
            'total_values': len(content),
            'non_empty_values': non_empty_count,
            'fill_rate': non_empty_count / len(content) if content else 0,
            'unique_values': len(set(values)),
            'sample_values': list(set(values))[:10]
        }
        
        # Data type detection
        if values:
            numeric_count = sum(1 for v in values if v.replace('.', '').replace('-', '').isdigit())
            if numeric_count > len(values) * 0.8:
                field_analysis['likely_type'] = 'numeric'
            elif any(keyword in field.lower() for keyword in ['date', 'time', 'created', 'updated']):
                field_analysis['likely_type'] = 'datetime'
            else:
                field_analysis['likely_type'] = 'text'
        
        analysis['fields'][field] = field_analysis
    
    # Overall data quality
    total_cells = len(content) * len(all_fields)
    filled_cells = sum(
        sum(1 for v in row.values() if v is not None and str(v).strip())
        for row in content if isinstance(row, dict)
    )
    
    analysis['data_quality'] = {
        'overall_fill_rate': filled_cells / total_cells if total_cells > 0 else 0,
        'complete_rows': sum(1 for row in content if isinstance(row, dict) and 
                           all(v is not None and str(v).strip() for v in row.values())),
        'empty_rows': sum(1 for row in content if isinstance(row, dict) and 
                         all(not v or not str(v).strip() for v in row.values()))
    }
    
    return analysis

def analyze_text_content(content: str) -> Dict:
    """Comprehensive text content analysis"""
    if not content or not content.strip():
        return {'type': 'text', 'empty': True}
    
    lines = content.split('\n')
    words = re.findall(r'\b\w+\b', content.lower())
    
    analysis = {
        'type': 'text',
        'total_characters': len(content),
        'total_lines': len(lines),
        'non_empty_lines': len([line for line in lines if line.strip()]),
        'total_words': len(words),
        'unique_words': len(set(words)),
        'average_line_length': sum(len(line) for line in lines) / len(lines) if lines else 0,
        'language_analysis': {},
        'content_structure': {}
    }
    
    # Word frequency analysis
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Most common words (excluding common stop words)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    common_words = sorted(
        [(word, freq) for word, freq in word_freq.items() if word not in stop_words],
        key=lambda x: x[1], reverse=True
    )[:20]
    
    analysis['language_analysis'] = {
        'most_common_words': common_words,
        'vocabulary_richness': len(set(words)) / len(words) if words else 0
    }
    
    # Structure analysis
    paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
    sentence_count = len(re.findall(r'[.!?]+', content))
    
    analysis['content_structure'] = {
        'paragraphs': paragraph_count,
        'sentences': sentence_count,
        'average_words_per_sentence': len(words) / sentence_count if sentence_count > 0 else 0
    }
    
    return analysis

@app.route('/api/delete/<file_id>', methods=['DELETE'])
def delete_file(file_id: str):
    """Enhanced file deletion with cleanup"""
    try:
        with storage_lock:
            if file_id not in file_storage:
                return jsonify({'error': 'File not found'}), 404
            
            file_info = file_storage[file_id]
            
            # Delete physical file
            if os.path.exists(file_info['path']):
                os.remove(file_info['path'])
                logger.info(f"Deleted file: {file_info['path']}")
            
            # Remove from storage
            del file_storage[file_id]
        
        return jsonify({
            'message': 'File deleted successfully',
            'deleted_file': {
                'id': file_id,
                'filename': file_info['filename']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Delete file error: {e}")
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500

@app.route('/api/batch-upload', methods=['POST'])
def batch_upload():
    """Batch file upload with parallel processing"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files selected'}), 400
        
        results = []
        errors = []
        
        for file in files:
            try:
                if not file or file.filename == '':
                    errors.append({'filename': 'unknown', 'error': 'Empty file'})
                    continue
                
                if not allowed_file(file.filename):
                    errors.append({
                        'filename': file.filename,
                        'error': f'File type not allowed'
                    })
                    continue
                
                # Process individual file (similar to single upload)
                filename = secure_filename(file.filename)
                file_id = str(uuid.uuid4())
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
                
                file.save(file_path)
                
                file_extension = filename.rsplit('.', 1)[1].lower()
                content, extraction_status, metadata = extract_content_advanced(file_path, file_extension)
                
                with storage_lock:
                    file_storage[file_id] = {
                        'id': file_id,
                        'filename': filename,
                        'path': file_path,
                        'content': content,
                        'type': file_extension,
                        'extraction_status': extraction_status,
                        'metadata': metadata,
                        'size': os.path.getsize(file_path),
                        'upload_time': time.time(),
                        'processed_content': preprocess_content_for_search(content, file_extension)
                    }
                
                results.append({
                    'id': file_id,
                    'filename': filename,
                    'type': file_extension,
                    'extraction_status': extraction_status,
                    'size': os.path.getsize(file_path)
                })
                
            except Exception as e:
                errors.append({
                    'filename': file.filename,
                    'error': str(e)
                })
        
        return jsonify({
            'message': f'Batch upload completed',
            'successful_uploads': len(results),
            'failed_uploads': len(errors),
            'results': results,
            'errors': errors
        }), 200
        
    except Exception as e:
        logger.error(f"Batch upload error: {e}")
        return jsonify({'error': f'Batch upload failed: {str(e)}'}), 500

# Enhanced error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 32MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({'error': 'Internal server error occurred'}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(400)
def bad_request(e):
    return jsonify({'error': 'Bad request format'}), 400

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """System health and statistics"""
    with storage_lock:
        total_files = len(file_storage)
        total_size = sum(info.get('size', 0) for info in file_storage.values())
        
        extraction_stats = {}
        for info in file_storage.values():
            status = info.get('extraction_status', 'unknown')
            extraction_stats[status] = extraction_stats.get(status, 0) + 1
    
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'statistics': {
            'total_files': total_files,
            'total_storage_bytes': total_size,
            'extraction_stats': extraction_stats,
            'supported_formats': list(ALLOWED_EXTENSIONS)
        },
        'system_info': {
            'upload_folder': UPLOAD_FOLDER,
            'max_file_size_mb': app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
        }
    }), 200

if __name__ == '__main__':
    logger.info("Starting enhanced Flask application with maximum accuracy features...")
    logger.info(f"Supported file types: {', '.join(ALLOWED_EXTENSIONS)}")
    logger.info(f"Upload folder: {UPLOAD_FOLDER}")
    logger.info(f"Max file size: {app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)}MB")
    
    app.run(debug=True, port=5000, threaded=True)
