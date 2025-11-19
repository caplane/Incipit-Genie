#!/usr/bin/env python3
"""
Incipit Genie Pro - Final Version with Unicode Smart Quote Support
Correctly handles all quote types and complex document structures
Created by Eric Caplan (caplane@gmail.com)
"""

from flask import Flask, render_template, request, send_file, flash, redirect, url_for
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
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

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
    """Intelligent incipit extraction with Unicode quote support"""
    
    def __init__(self, word_count=3):
        self.word_count = word_count
        self.endnote_contexts = {}
    
    def process_paragraph(self, para_element):
        """Process a single paragraph to extract incipits"""
        runs = para_element.getElementsByTagName('w:r')
        
        # Build complete paragraph text
        para_text = ""
        run_data = []
        
        for run in runs:
            start_pos = len(para_text)
            
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
            
            run_data.append((start_pos, end_pos, endnote_id))
        
        # Process each endnote
        results = {}
        for start_pos, end_pos, endnote_id in run_data:
            if endnote_id:
                incipit = self.extract_incipit_at_position(para_text, start_pos)
                if incipit:
                    results[endnote_id] = incipit
        
        return results
    
    def extract_incipit_at_position(self, text, endnote_pos):
        """Extract incipit text for an endnote at the given position"""
        text_before = text[:endnote_pos]
        
        if not text_before:
            return ""
        
        # Check if endnote comes after a closing quote (smart or regular)
        last_char = text_before[-1] if text_before else ''
        
        if last_char in [RIGHT_DOUBLE_QUOTE, '"', RIGHT_SINGLE_QUOTE, "'"]:
            # Find the matching opening quote
            quote_end = len(text_before) - 1
            
            # Search backwards for opening quote
            for i in range(quote_end - 1, max(0, quote_end - 1000), -1):
                char = text[i]
                
                # Check for opening quotes
                if char in [LEFT_DOUBLE_QUOTE, '"', LEFT_SINGLE_QUOTE, "'"]:
                    # Verify it's an opening quote (preceded by space, punctuation, or start)
                    if i == 0 or text[i-1] in [' ', ',', ':', '.', '!', '?', ';', '(', '—', '-', '\n', '\t']:
                        # Extract from inside the quote
                        quoted_text = text[i+1:quote_end].strip()
                        words = quoted_text.split()[:self.word_count]
                        return ' '.join(words)
        
        # Not after a quote - find sentence boundary
        boundaries = []
        
        # Find sentence boundaries (period, question mark, etc. followed by space)
        for marker in ['. ', '? ', '! ', ': ', '; ', '.\n', '?\n', '!\n']:
            pos = text_before.rfind(marker)
            if pos != -1:
                boundaries.append(pos + len(marker))
        
        # Also check for quote after punctuation
        for marker in ['. "', '. ' + LEFT_DOUBLE_QUOTE, ': "', ': ' + LEFT_DOUBLE_QUOTE]:
            pos = text_before.rfind(marker)
            if pos != -1:
                boundaries.append(pos + len(marker))
        
        if boundaries:
            start_pos = max(boundaries)
        else:
            # No clear boundary - use beginning or last 100 chars
            start_pos = max(0, endnote_pos - 100)
        
        # Extract text from start position
        context = text_before[start_pos:].strip()
        
        # Clean up leading punctuation and quotes
        context = re.sub(r'^["\'"".,;:!?\s]+', '', context)
        
        # Get specified number of words
        words = context.split()[:self.word_count]
        
        # Clean trailing punctuation from last word
        if words:
            words[-1] = re.sub(r'[.,;:!?"\'"]+$', '', words[-1])
        
        return ' '.join(words)
    
    def process_document(self, doc_xml_content):
        """Process entire document"""
        dom = minidom.parseString(doc_xml_content)
        all_contexts = {}
        
        for para in dom.getElementsByTagName('w:p'):
            contexts = self.process_paragraph(para)
            all_contexts.update(contexts)
        
        return all_contexts

def extract_endnotes_with_formatting(endnotes_path):
    """Extract endnote content preserving formatting"""
    with open(endnotes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    dom = minidom.parseString(content)
    endnotes = {}
    
    for endnote in dom.getElementsByTagName('w:endnote'):
        endnote_id = endnote.getAttribute('w:id')
        if endnote_id and endnote_id not in ['-1', '0']:
            endnote_runs = []
            paragraphs = endnote.getElementsByTagName('w:p')
            
            for para in paragraphs:
                runs = para.getElementsByTagName('w:r')
                
                for run in runs:
                    # Skip endnoteRef elements
                    if run.getElementsByTagName('w:endnoteRef'):
                        continue
                    
                    # Get text content
                    text_content = ""
                    for t_elem in run.getElementsByTagName('w:t'):
                        if t_elem.firstChild:
                            text_content += t_elem.firstChild.nodeValue
                    
                    # Skip standalone numbers
                    if text_content.strip() and text_content.strip().isdigit():
                        continue
                    
                    # Remove leading numbers
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
    
    return endnotes

def add_incipit_to_endnotes(endnotes, contexts, format_bold=True):
    """Add incipit text to endnotes"""
    enhanced_endnotes = {}
    
    for endnote_id, endnote_content in endnotes.items():
        if endnote_id in contexts:
            incipit_text = contexts[endnote_id]
            
            # Create formatted incipit
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
    """Replace endnote references with bookmarks"""
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
                
                # Create bookmark elements
                bookmark_start = dom.createElement('w:bookmarkStart')
                bookmark_start.setAttribute('w:id', str(bookmark_id))
                bookmark_start.setAttribute('w:name', bookmark_name)
                
                bookmark_end = dom.createElement('w:bookmarkEnd')
                bookmark_end.setAttribute('w:id', str(bookmark_id))
                
                # Insert bookmarks
                parent = run.parentNode
                parent.insertBefore(bookmark_start, run)
                parent.insertBefore(bookmark_end, run)
                
                # Remove endnote reference
                for ref in run.getElementsByTagName('w:endnoteReference'):
                    ref.parentNode.removeChild(ref)
                
                # Remove empty run if needed
                if not run.getElementsByTagName('w:t') and not run.childNodes:
                    parent.removeChild(run)
                
                bookmark_id += 1
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(dom.toxml())
    
    return references, total_endnotes

def create_notes_section_xml(endnotes, references):
    """Create the Notes section with page references"""
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
    for note_id in sorted(endnotes.keys(), key=lambda x: int(x)):
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
    
    return '\n'.join(notes_xml)

def add_notes_to_document(doc_path, notes_xml, output_path):
    """Add notes section to document"""
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
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def convert_document(input_path, output_path, word_count=3, format_bold=True, extract_incipit=True):
    """Main conversion function with smart quote support"""
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Unpack document
        unpack_docx(input_path, temp_dir)
        
        # Check for endnotes
        endnotes_file = temp_dir / 'word' / 'endnotes.xml'
        if not endnotes_file.exists():
            return False, "No endnotes found in this document."
        
        # Extract endnotes
        endnotes = extract_endnotes_with_formatting(endnotes_file)
        if not endnotes:
            return False, "No endnotes found."
        
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
        pack_docx(temp_dir, output_path)
        
        incipits_count = len(contexts) if extract_incipit else 0
        return True, f"Successfully converted {total_endnotes} endnotes ({incipits_count} with incipit text)"
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(traceback.format_exc())
        return False, error_msg
        
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

# Flask routes remain the same...
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if not allowed_file(file.filename):
        flash('Please upload a .docx file', 'error')
        return redirect(url_for('index'))
    
    # Get options
    word_count = int(request.form.get('word_count', 3))
    format_style = request.form.get('format_style', 'bold')
    extract_incipit = request.form.get('extract_incipit', 'yes') == 'yes'
    
    if file and allowed_file(file.filename):
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_input = os.path.join(app.config['UPLOAD_FOLDER'], f"in_{timestamp}_{filename}")
        file.save(temp_input)
        
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
            flash(message, 'error')
            return redirect(url_for('index'))

@app.errorhandler(413)
def too_large(e):
    flash('File is too large. Maximum size is 50MB.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
