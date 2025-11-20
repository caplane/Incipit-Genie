#!/usr/bin/env python3
"""
Incipit Genie Pro - Optimized for Large Files
Handles documents with hundreds of endnotes efficiently
Created by Eric Caplan (caplane@gmail.com)
"""

from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
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
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Increase limits for large files
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'docx'}

# Define Unicode quote characters
LEFT_DOUBLE_QUOTE = chr(8220)   # "
RIGHT_DOUBLE_QUOTE = chr(8221)  # "
LEFT_SINGLE_QUOTE = chr(8216)   # '
RIGHT_SINGLE_QUOTE = chr(8217)  # '

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def unpack_docx(docx_path, extract_dir):
    """Extract a .docx file to a directory"""
    with zipfile.ZipFile(docx_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

def pack_docx(source_dir, output_path):
    """Pack a directory back into a .docx file"""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)

class SmartIncipitExtractor:
    """Optimized incipit extraction for large documents"""
    
    def __init__(self, word_count=3):
        self.word_count = word_count
        self.endnote_contexts = {}
        self.processed_count = 0
    
    def process_paragraph(self, para_element):
        """Process a single paragraph to extract incipits"""
        runs = para_element.getElementsByTagName('w:r')
        
        # Build complete paragraph text
        para_text = ""
        run_data = []
        has_italic = False
        
        for run in runs:
            start_pos = len(para_text)
            
            # Check for italic formatting
            rPr = run.getElementsByTagName('w:rPr')
            if rPr and rPr[0].getElementsByTagName('w:i'):
                has_italic = True
            
            # Get text
            text = ""
            for t in run.getElementsByTagName('w:t'):
                if t.firstChild:
                    text += t.firstChild.nodeValue
            
            para_text += text
            end_pos = len(para_text)
            
            # Check for endnote
            endnote_id = None
            refs = run.getElementsByTagName('w:endnoteReference')
            if refs:
                endnote_id = refs[0].getAttribute('w:id')
                self.processed_count += 1
                
                # Log progress every 50 notes
                if self.processed_count % 50 == 0:
                    logger.info(f"Processed {self.processed_count} endnote references...")
            
            run_data.append((start_pos, end_pos, endnote_id))
        
        # Check if this is likely an epigraph
        is_epigraph = False
        if para_text.strip() and len(para_text) < 500:
            if has_italic or para_text.count('.') <= 3:
                is_epigraph = True
        
        # Process each endnote
        results = {}
        for start_pos, end_pos, endnote_id in run_data:
            if endnote_id:
                if is_epigraph:
                    words = para_text.strip().split()[:self.word_count]
                    incipit = ' '.join(words)
                    if incipit:
                        incipit = re.sub(r'[.,;:!?"\'"]+$', '', incipit)
                    results[endnote_id] = incipit
                else:
                    incipit = self.extract_incipit_at_position(para_text, start_pos)
                    if incipit:
                        results[endnote_id] = incipit
        
        return results
    
    def extract_incipit_at_position(self, text, endnote_pos):
        """Optimized incipit extraction"""
        text_before = text[:endnote_pos]
        
        if not text_before:
            return ""
        
        # Fast path for common case - endnote after sentence
        if text_before and text_before[-1] in ['.', '!', '?']:
            sentence_text = text_before[:-1].strip()
            
            # Find sentence start
            sentence_start = 0
            for marker in ['. ', '? ', '! ']:
                pos = sentence_text.rfind(marker)
                if pos != -1 and pos + len(marker) > sentence_start:
                    sentence_start = pos + len(marker)
            
            current_sentence = sentence_text[sentence_start:].strip()
            
            # Handle em-dash
            if '—' in current_sentence:
                current_sentence = current_sentence.split('—')[0].strip()
            
            if current_sentence:
                words = current_sentence.split()[:self.word_count]
                if words:
                    words[-1] = re.sub(r'[.,;:!?"\'"]+$', '', words[-1])
                return ' '.join(words)
        
        # Handle other cases (simplified for performance)
        boundaries = []
        for marker in ['. ', '? ', '! ', ': ']:
            pos = text_before.rfind(marker)
            if pos != -1:
                boundaries.append(pos + len(marker))
        
        if boundaries:
            start_pos = max(boundaries)
        else:
            start_pos = max(0, endnote_pos - 100)
        
        working_text = text_before[start_pos:].strip()
        working_text = re.sub(r'^["\'"".,;:!?\s]+', '', working_text)
        
        words = working_text.split()[:self.word_count]
        if words:
            words[-1] = re.sub(r'[.,;:!?"\'"]+$', '', words[-1])
        
        return ' '.join(words)
    
    def process_document(self, doc_xml_content):
        """Process entire document with progress tracking"""
        logger.info("Starting document processing...")
        dom = minidom.parseString(doc_xml_content)
        all_contexts = {}
        
        paragraphs = dom.getElementsByTagName('w:p')
        total_paragraphs = len(paragraphs)
        
        for i, para in enumerate(paragraphs):
            if i % 100 == 0:
                logger.info(f"Processing paragraph {i}/{total_paragraphs}...")
            contexts = self.process_paragraph(para)
            all_contexts.update(contexts)
        
        logger.info(f"Completed processing {self.processed_count} endnotes")
        return all_contexts

def extract_endnotes_with_formatting(endnotes_path):
    """Extract endnote content preserving formatting - optimized"""
    logger.info("Extracting endnotes...")
    with open(endnotes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    dom = minidom.parseString(content)
    endnotes = {}
    
    all_endnotes = dom.getElementsByTagName('w:endnote')
    total = len(all_endnotes)
    
    for idx, endnote in enumerate(all_endnotes):
        if idx % 50 == 0:
            logger.info(f"Extracting endnote {idx}/{total}...")
            
        endnote_id = endnote.getAttribute('w:id')
        if endnote_id and endnote_id not in ['-1', '0']:
            endnote_runs = []
            paragraphs = endnote.getElementsByTagName('w:p')
            
            for para in paragraphs:
                runs = para.getElementsByTagName('w:r')
                
                for run in runs:
                    if run.getElementsByTagName('w:endnoteRef'):
                        continue
                    
                    text_content = ""
                    for t_elem in run.getElementsByTagName('w:t'):
                        if t_elem.firstChild:
                            text_content += t_elem.firstChild.nodeValue
                    
                    if text_content.strip() and text_content.strip().isdigit():
                        continue
                    
                    if text_content and text_content.strip():
                        cleaned_text = re.sub(r'^\s*\d+\s+', '', text_content)
                        if cleaned_text != text_content:
                            run_copy = run.cloneNode(deep=True)
                            for t_elem in run_copy.getElementsByTagName('w:t'):
                                if t_elem.firstChild:
                                    t_elem.firstChild.nodeValue = cleaned_text
                            
                            if cleaned_text.strip():
                                endnote_runs.append(run_copy.toxml())
                            continue
                    
                    endnote_runs.append(run.toxml())
            
            endnotes[endnote_id] = ''.join(endnote_runs)
    
    logger.info(f"Extracted {len(endnotes)} endnotes")
    return endnotes

def add_incipit_to_endnotes(endnotes, contexts, format_bold=True):
    """Add incipit text to endnotes - optimized"""
    logger.info("Adding incipits to endnotes...")
    enhanced_endnotes = {}
    
    for endnote_id, endnote_content in endnotes.items():
        if endnote_id in contexts:
            incipit_text = contexts[endnote_id]
            
            if format_bold:
                incipit_xml = f'''<w:r>
      <w:rPr>
        <w:b/>
      </w:rPr>
      <w:t>{incipit_text}:</w:t>
    </w:r>
    <w:r>
      <w:t xml:space="preserve"> </w:t>
    </w:r>'''
            else:
                incipit_xml = f'''<w:r>
      <w:rPr>
        <w:i/>
      </w:rPr>
      <w:t>{incipit_text}:</w:t>
    </w:r>
    <w:r>
      <w:t xml:space="preserve"> </w:t>
    </w:r>'''
            
            enhanced_endnotes[endnote_id] = incipit_xml + endnote_content
        else:
            enhanced_endnotes[endnote_id] = endnote_content
    
    return enhanced_endnotes

def process_endnote_references(doc_path, output_path):
    """Replace endnote references with bookmarks - optimized"""
    logger.info("Processing endnote references...")
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    dom = minidom.parseString(content)
    references = {}
    bookmark_id = 1000
    total_endnotes = 0
    
    paragraphs = dom.getElementsByTagName('w:p')
    
    for para in paragraphs:
        runs = para.getElementsByTagName('w:r')
        
        for run in runs:
            endnote_refs = run.getElementsByTagName('w:endnoteReference')
            
            if endnote_refs:
                endnote_id = endnote_refs[0].getAttribute('w:id')
                total_endnotes += 1
                
                bookmark_name = f"endnote_{endnote_id}"
                references[endnote_id] = {'bookmark': bookmark_name}
                
                bookmark_start = dom.createElement('w:bookmarkStart')
                bookmark_start.setAttribute('w:id', str(bookmark_id))
                bookmark_start.setAttribute('w:name', bookmark_name)
                
                bookmark_end = dom.createElement('w:bookmarkEnd')
                bookmark_end.setAttribute('w:id', str(bookmark_id))
                
                parent = run.parentNode
                parent.insertBefore(bookmark_start, run)
                parent.insertBefore(bookmark_end, run)
                
                for ref in run.getElementsByTagName('w:endnoteReference'):
                    ref.parentNode.removeChild(ref)
                
                if not run.getElementsByTagName('w:t') and not run.childNodes:
                    parent.removeChild(run)
                
                bookmark_id += 1
                
                if total_endnotes % 50 == 0:
                    logger.info(f"Processed {total_endnotes} references...")
    
    logger.info(f"Writing document with {total_endnotes} bookmarks...")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(dom.toxml())
    
    return references, total_endnotes

def create_notes_section_xml(endnotes, references):
    """Create the Notes section with page references - optimized"""
    logger.info("Creating notes section...")
    notes_xml = []
    
    # Page break
    notes_xml.append('''  <w:p>
    <w:pPr></w:pPr>
    <w:r>
      <w:br w:type="page"/>
    </w:r>
  </w:p>''')
    
    # Notes heading
    notes_xml.append('''  <w:p>
    <w:pPr>
      <w:pStyle w:val="Heading1"/>
    </w:pPr>
    <w:r>
      <w:t>Notes</w:t>
    </w:r>
  </w:p>''')
    
    # Add each note
    note_count = 0
    for note_id in sorted(endnotes.keys(), key=lambda x: int(x)):
        note_count += 1
        if note_count % 50 == 0:
            logger.info(f"Creating note {note_count}...")
            
        citation_xml = endnotes[note_id]
        
        if note_id in references:
            ref = references[note_id]
            bookmark_name = ref['bookmark']
            
            note_xml = f'''  <w:p>
    <w:pPr>
      <w:spacing w:after="120"/>
    </w:pPr>
    <w:r>
      <w:fldSimple w:instr=" PAGEREF {bookmark_name} \\h ">
        <w:r>
          <w:t>[Page]</w:t>
        </w:r>
      </w:fldSimple>
    </w:r>
    <w:r>
      <w:t xml:space="preserve">. </w:t>
    </w:r>
    {citation_xml}
  </w:p>'''
        else:
            note_xml = f'''  <w:p>
    <w:pPr>
      <w:spacing w:after="120"/>
    </w:pPr>
    <w:r>
      <w:t>[No ref]. </w:t>
    </w:r>
    {citation_xml}
  </w:p>'''
        
        notes_xml.append(note_xml)
    
    logger.info(f"Created {note_count} notes")
    return '\n'.join(notes_xml)

def add_notes_to_document(doc_path, notes_xml, output_path):
    """Add notes section to document - optimized"""
    logger.info("Adding notes section to document...")
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    body_close_pos = content.rfind('</w:body>')
    if body_close_pos == -1:
        return False
    
    # Find insertion point
    para_endings = []
    pos = 0
    while True:
        pos = content.find('</w:p>', pos)
        if pos == -1 or pos >= body_close_pos:
            break
        para_endings.append(pos)
        pos += 1
    
    sect_pr_start = content.rfind('<w:sectPr', 0, body_close_pos)
    
    if para_endings:
        insert_after_para = para_endings[-1]
        if sect_pr_start != -1:
            for para_end in reversed(para_endings):
                if para_end < sect_pr_start:
                    insert_after_para = para_end
                    break
        insert_pos = insert_after_para + len('</w:p>')
    else:
        insert_pos = sect_pr_start if sect_pr_start != -1 else body_close_pos
    
    new_content = content[:insert_pos] + '\n' + notes_xml + '\n' + content[insert_pos:]
    
    logger.info("Writing final document...")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def convert_document(input_path, output_path, word_count=3, format_bold=True, extract_incipit=True):
    """Main conversion function - optimized for large files"""
    start_time = time.time()
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Check file size
        file_size = os.path.getsize(input_path) / 1024  # KB
        logger.info(f"Processing file: {file_size:.1f} KB")
        
        # Unpack document
        logger.info("Unpacking document...")
        unpack_docx(input_path, temp_dir)
        
        # Check for endnotes
        endnotes_file = temp_dir / 'word' / 'endnotes.xml'
        if not endnotes_file.exists():
            return False, "No endnotes found in this document."
        
        # Extract endnotes
        endnotes = extract_endnotes_with_formatting(endnotes_file)
        if not endnotes:
            return False, "No endnotes found."
        
        logger.info(f"Found {len(endnotes)} endnotes")
        
        # Extract incipit contexts if requested
        contexts = {}
        if extract_incipit:
            doc_file = temp_dir / 'word' / 'document.xml'
            with open(doc_file, 'r', encoding='utf-8') as f:
                doc_content = f.read()
            
            extractor = SmartIncipitExtractor(word_count=word_count)
            contexts = extractor.process_document(doc_content)
        
        # Add incipit to endnotes
        enhanced_endnotes = add_incipit_to_endnotes(endnotes, contexts, format_bold)
        
        # Process references
        doc_file = temp_dir / 'word' / 'document.xml'
        doc_temp = temp_dir / 'word' / 'document_temp.xml'
        references, total_endnotes = process_endnote_references(doc_file, doc_temp)
        
        # Create notes section
        notes_xml = create_notes_section_xml(enhanced_endnotes, references)
        
        # Add to document
        success = add_notes_to_document(doc_temp, notes_xml, doc_file)
        if not success:
            return False, "Failed to add notes section."
        
        doc_temp.unlink()
        
        # Pack document
        logger.info("Creating final document...")
        pack_docx(temp_dir, output_path)
        
        elapsed_time = time.time() - start_time
        incipits_count = len(contexts) if extract_incipit else 0
        
        logger.info(f"Conversion completed in {elapsed_time:.1f} seconds")
        return True, f"Successfully converted {total_endnotes} endnotes ({incipits_count} with incipit text) in {elapsed_time:.1f} seconds"
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(traceback.format_exc())
        return False, error_msg
        
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    try:
        logger.info("Convert route called")
        
        if 'file' not in request.files:
            logger.error("No file in request")
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        file = request.files['file']
        
        if file.filename == '':
            logger.error("Empty filename")
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        if not allowed_file(file.filename):
            logger.error(f"Invalid file type: {file.filename}")
            flash('Please upload a .docx file', 'error')
            return redirect(url_for('index'))
        
        # Get options
        word_count = int(request.form.get('word_count', 3))
        format_style = request.form.get('format_style', 'bold')
        extract_incipit = request.form.get('extract_incipit', 'yes') == 'yes'
        
        logger.info(f"Processing file: {file.filename}")
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_input = os.path.join(app.config['UPLOAD_FOLDER'], f"in_{timestamp}_{filename}")
        file.save(temp_input)
        
        # Check file size for warning
        file_size_mb = os.path.getsize(temp_input) / (1024 * 1024)
        if file_size_mb > 5:
            logger.info(f"Large file detected: {file_size_mb:.1f} MB")
        
        # Prepare output
        output_filename = filename.rsplit('.', 1)[0] + '_incipit.docx'
        temp_output = os.path.join(app.config['UPLOAD_FOLDER'], f"out_{timestamp}_{output_filename}")
        
        # Convert
        success, message = convert_document(
            temp_input, 
            temp_output,
            word_count=word_count,
            format_bold=(format_style == 'bold'),
            extract_incipit=extract_incipit
        )
        
        # Clean input
        try:
            os.remove(temp_input)
        except Exception as e:
            logger.error(f"Failed to remove input file: {e}")
        
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
            flash(message, 'error')
            return redirect(url_for('index'))
            
    except Exception as e:
        logger.error(f"Convert route error: {str(e)}")
        logger.error(traceback.format_exc())
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('index'))

# Test endpoint
@app.route('/test-upload', methods=['POST'])
def test_upload():
    """Test endpoint to debug file uploads"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in request'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': f'Invalid file type. Only .docx allowed'}), 400
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"test_{timestamp}_{filename}")
        
        file.save(filepath)
        file_size = os.path.getsize(filepath)
        
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'size': file_size,
            'message': 'File upload successful!'
        }), 200
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    flash('File is too large. Maximum size is 100MB.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
