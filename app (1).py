#!/usr/bin/env python3
"""
Incipit Genie Pro - MINIMAL WORKING VERSION
"""

from flask import Flask, render_template_string, request, send_file, redirect, url_for
from werkzeug.utils import secure_filename
import os
import tempfile
import shutil
from pathlib import Path
import zipfile
import xml.dom.minidom as minidom
import re
import traceback
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-12345')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
app.config['UPLOAD_FOLDER'] = '/tmp'

ALLOWED_EXTENSIONS = {'docx'}

# Embed the HTML template directly to avoid template issues
HTML_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
    <title>Incipit Genie PRO</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; text-align: center; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        input[type="file"] { margin: 20px 0; padding: 10px; }
        input[type="submit"] { background: #007bff; color: white; padding: 10px 30px; border: none; border-radius: 5px; cursor: pointer; }
        input[type="submit"]:hover { background: #0056b3; }
        .form-group { margin: 20px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>✨ Incipit Genie PRO</h1>
        <p style="text-align:center">Transform endnotes to Chicago-style citations</p>
        
        <form method="POST" enctype="multipart/form-data" action="/convert">
            <div class="form-group">
                <label>Upload Word Document (.docx)</label>
                <input type="file" name="file" accept=".docx" required>
            </div>
            
            <div class="form-group">
                <label>Incipit Words</label>
                <input type="number" name="word_count" value="3" min="1" max="10" style="padding:5px">
            </div>
            
            <div class="form-group">
                <label>Format Style</label>
                <select name="format_style" style="padding:5px">
                    <option value="bold">Bold</option>
                    <option value="italic">Italic</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Extract Incipit</label>
                <select name="extract_incipit" style="padding:5px">
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                </select>
            </div>
            
            <input type="submit" value="Convert Document">
        </form>
    </div>
</body>
</html>'''

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/convert', methods=['POST'])
def convert():
    try:
        if 'file' not in request.files:
            return 'No file uploaded', 400
        
        file = request.files['file']
        if file.filename == '':
            return 'No file selected', 400
        
        if not allowed_file(file.filename):
            return 'Invalid file type. Please upload a .docx file', 400
        
        # Get form options
        word_count = int(request.form.get('word_count', 3))
        format_style = request.form.get('format_style', 'bold')
        extract_incipit = request.form.get('extract_incipit', 'yes') == 'yes'
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_input = os.path.join(app.config['UPLOAD_FOLDER'], f"in_{timestamp}_{filename}")
        file.save(temp_input)
        
        # Process the document
        output_filename = filename.rsplit('.', 1)[0] + '_incipit.docx'
        temp_output = os.path.join(app.config['UPLOAD_FOLDER'], f"out_{timestamp}_{output_filename}")
        
        success = process_document(temp_input, temp_output, word_count, format_style == 'bold', extract_incipit)
        
        # Clean up input
        try:
            os.remove(temp_input)
        except:
            pass
        
        if success:
            response = send_file(
                temp_output,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                as_attachment=True,
                download_name=output_filename
            )
            
            @response.call_on_close
            def cleanup():
                try:
                    os.remove(temp_output)
                except:
                    pass
            
            return response
        else:
            return 'Error processing document', 500
            
    except Exception as e:
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        return f'Error: {str(e)}', 500

def process_document(input_path, output_path, word_count, format_bold, extract_incipit):
    """Simplified document processing"""
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Unpack docx
        with zipfile.ZipFile(input_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Check for endnotes
        endnotes_file = temp_dir / 'word' / 'endnotes.xml'
        if not endnotes_file.exists():
            return False
        
        # Simple processing - just copy the file for now to test
        # In production, this would have all the endnote processing
        shutil.copy(input_path, output_path)
        return True
        
    except Exception as e:
        print(f"Processing error: {str(e)}")
        return False
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

@app.route('/health')
def health():
    return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
