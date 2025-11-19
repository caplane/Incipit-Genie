#!/usr/bin/env python3
"""
Incipit Genie - Academic Citation Formatter
Transforms traditional endnotes to page-referenced citations
Created by Eric Caplan (caplane@gmail.com)
Copyright 2024 - All Rights Reserved
Website: https://incipitgenie.com
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
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

ALLOWED_EXTENSIONS = {'docx'}

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

def extract_endnotes_with_formatting(endnotes_path):
    """Extract endnote content from endnotes.xml preserving all formatting"""
    with open(endnotes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    dom = minidom.parseString(content)
    endnotes = {}
    
    for endnote in dom.getElementsByTagName('w:endnote'):
        endnote_id = endnote.getAttribute('w:id')
        if endnote_id and endnote_id not in ['-1', '0']:
            # Collect all runs from this endnote, skipping the endnote reference
            endnote_runs = []
            
            # Get all paragraphs in the endnote
            paragraphs = endnote.getElementsByTagName('w:p')
            
            for para in paragraphs:
                runs = para.getElementsByTagName('w:r')
                
                for run in runs:
                    # Skip any run that contains an endnoteRef element
                    if run.getElementsByTagName('w:endnoteRef'):
                        continue
                    
                    # Check if this run is just a number at the beginning
                    text_content = ""
                    for t_elem in run.getElementsByTagName('w:t'):
                        if t_elem.firstChild:
                            text_content += t_elem.firstChild.nodeValue
                    
                    # Skip if it's just a standalone number
                    if text_content.strip() and text_content.strip().isdigit():
                        continue
                    
                    # If text starts with a number followed by content, remove the number
                    if text_content and text_content.strip():
                        cleaned_text = re.sub(r'^\s*\d+\s+', '', text_content)
                        if cleaned_text != text_content:
                            run_copy = run.cloneNode(deep=True)
                            for t_elem in run_copy.getElementsByTagName('w:t'):
                                if t_elem.firstChild:
                                    if t_elem.hasAttribute('xml:space'):
                                        t_elem.firstChild.nodeValue = cleaned_text
                                    else:
                                        t_elem.firstChild.nodeValue = cleaned_text.strip()
                            
                            if cleaned_text.strip():
                                endnote_runs.append(run_copy.toxml())
                            continue
                    
                    # Add this run as-is (preserves all formatting)
                    endnote_runs.append(run.toxml())
            
            endnotes[endnote_id] = ''.join(endnote_runs)
    
    return endnotes

def process_endnote_references(doc_path, output_path):
    """Replace endnote references with bookmarks"""
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    dom = minidom.parseString(content)
    references = {}
    bookmark_id = 1000
    total_endnotes = 0
    
    # Process all paragraphs
    paragraphs = dom.getElementsByTagName('w:p')
    
    for para in paragraphs:
        runs = para.getElementsByTagName('w:r')
        
        for run in runs:
            endnote_refs = run.getElementsByTagName('w:endnoteReference')
            
            if endnote_refs:
                endnote_id = endnote_refs[0].getAttribute('w:id')
                total_endnotes += 1
                
                # Create bookmark
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
                
                # Remove empty run
                if not run.getElementsByTagName('w:t') and not run.childNodes:
                    parent.removeChild(run)
                
                bookmark_id += 1
    
    # Save the modified document
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(dom.toxml())
    
    return references, total_endnotes

def create_notes_section_xml(endnotes, references):
    """Create the Notes section with page references and preserved formatting"""
    notes_xml = []
    
    # Add a simple page break
    notes_xml.append('''  <w:p>
    <w:pPr></w:pPr>
    <w:r>
      <w:br w:type="page"/>
    </w:r>
  </w:p>''')
    
    # Add Notes heading
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
      <w:t>[Missing reference] </w:t>
    </w:r>
    {citation_xml}
  </w:p>'''
        
        notes_xml.append(note_xml)
    
    return '\n'.join(notes_xml)

def add_notes_to_document(doc_path, notes_xml, output_path):
    """Add the notes section to the document while preserving all section properties"""
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the body element boundaries
    body_close_pos = content.rfind('</w:body>')
    
    if body_close_pos == -1:
        return False
    
    # Find all paragraph endings
    para_endings = []
    pos = 0
    while True:
        pos = content.find('</w:p>', pos)
        if pos == -1 or pos >= body_close_pos:
            break
        para_endings.append(pos)
        pos += 1
    
    # Find if there's a sectPr (section properties) element
    sect_pr_start = content.rfind('<w:sectPr', 0, body_close_pos)
    
    # Determine insertion point
    if para_endings:
        insert_after_para = para_endings[-1]
        
        if sect_pr_start != -1:
            for para_end in reversed(para_endings):
                if para_end < sect_pr_start:
                    insert_after_para = para_end
                    break
        
        insert_pos = insert_after_para + len('</w:p>')
    else:
        if sect_pr_start != -1:
            insert_pos = sect_pr_start
        else:
            insert_pos = body_close_pos
    
    # Insert the notes content
    new_content = content[:insert_pos] + '\n' + notes_xml + '\n' + content[insert_pos:]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def convert_document(input_path, output_path):
    """Main conversion function"""
    # Create temporary directory for extraction
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Unpack the document
        unpack_docx(input_path, temp_dir)
        
        # Check for endnotes
        endnotes_file = temp_dir / 'word' / 'endnotes.xml'
        if not endnotes_file.exists():
            return False, "No endnotes found in this document."
        
        # Extract endnotes with formatting
        endnotes = extract_endnotes_with_formatting(endnotes_file)
        
        if not endnotes:
            return False, "No endnotes found in this document."
        
        # Process document
        doc_file = temp_dir / 'word' / 'document.xml'
        doc_temp = temp_dir / 'word' / 'document_temp.xml'
        references, total_endnotes = process_endnote_references(doc_file, doc_temp)
        
        # Create notes section
        notes_xml = create_notes_section_xml(endnotes, references)
        
        # Add notes to document
        success = add_notes_to_document(doc_temp, notes_xml, doc_file)
        if not success:
            return False, "Failed to add notes section to document."
        
        doc_temp.unlink()
        
        # Pack the document
        pack_docx(temp_dir, output_path)
        
        return True, f"Successfully converted {total_endnotes} endnotes"
        
    except Exception as e:
        error_msg = f"Error during conversion: {str(e)}"
        print(traceback.format_exc())
        return False, error_msg
        
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

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
    
    if file and allowed_file(file.filename):
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_input = os.path.join(app.config['UPLOAD_FOLDER'], f"input_{timestamp}_{filename}")
        file.save(temp_input)
        
        # Prepare output filename
        output_filename = filename.rsplit('.', 1)[0] + '_converted.docx'
        temp_output = os.path.join(app.config['UPLOAD_FOLDER'], f"output_{timestamp}_{output_filename}")
        
        # Convert the document
        success, message = convert_document(temp_input, temp_output)
        
        # Clean up input file
        try:
            os.remove(temp_input)
        except:
            pass
        
        if success:
            # Send the converted file
            response = send_file(
                temp_output,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                as_attachment=True,
                download_name=output_filename
            )
            
            # Schedule cleanup of output file
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
