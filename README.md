# 🧞 Incipit Genie

> *Your magical assistant for transforming academic citations*

Transform Word documents from traditional endnotes to page-referenced citations with the wave of a wand! Incipit Genie preserves formatting, maintains footer positions, and saves scholars countless hours of manual work.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Flask](https://img.shields.io/badge/Flask-3.0.0-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Railway](https://img.shields.io/badge/Deploy-Railway-purple)

## ✨ What is Incipit Genie?

Incipit Genie is a professional web application that automates the conversion of traditional endnotes to page-referenced citations in Word documents. Originally created to convert a 340-page manuscript with 750+ endnotes, it's now available to help academics worldwide.

### The Magic It Performs

- **🎯 Removes** all endnote numbers (including pesky superscripts)
- **💎 Preserves** bold text, italics, and quotation marks perfectly
- **📍 Maintains** footer positions and page number locations
- **🔮 Creates** dynamic PAGEREF fields that auto-update in Word
- **⚡ Processes** documents up to 50MB in seconds

## 🚀 Deploy to Railway in 3 Minutes

### Quick Deploy Steps

1. **Fork this repository** to your GitHub account
2. **Sign up** for Railway at [railway.app](https://railway.app)
3. **Click "New Project"** → "Deploy from GitHub repo"
4. **Select** your `Incipit Genie` repository
5. **Deploy** - Railway handles everything automatically!

Your app will be live at `https://incipit-genie.up.railway.app` in minutes!

### Railway Configuration

Railway automatically detects and configures everything, but you can customize:

```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn app:app --bind 0.0.0.0:$PORT"
  }
}
```

## 💻 Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/incipit-genie.git
cd incipit-genie

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

# Visit http://localhost:5000
```

## 📖 How Incipit Genie Works

The genie performs its magic by:

1. **📦 Unpacking** - Extracts the .docx file (which is actually a ZIP archive)
2. **🔍 Finding** - Locates all endnotes in the XML structure
3. **🏷️ Bookmarking** - Places invisible bookmarks where endnotes were
4. **✨ Transforming** - Creates page references using Word's PAGEREF fields
5. **💾 Preserving** - Maintains all original formatting and structure
6. **📤 Delivering** - Repackages everything into a perfect .docx file

## 🎯 Perfect For

- 📚 **Academic Authors** - Publishing with university presses
- 🎓 **Graduate Students** - Formatting dissertations and theses
- 🔬 **Researchers** - Preparing manuscripts for publication
- 📖 **Publishers** - Standardizing citation formats
- ✍️ **Writers** - Working with Chicago, MLA, or similar styles

## 📋 After the Magic

Once Incipit Genie works its magic:

1. Open your transformed document in Microsoft Word
2. Select all text (`Cmd+A` on Mac, `Ctrl+A` on PC)
3. Update fields (`F9`)
4. ✨ Your citations now show actual page numbers!

## 🛠️ Technology Stack

- **Backend**: Python 3.11, Flask 3.0
- **Document Magic**: XML parsing with minidom
- **File Alchemy**: zipfile for .docx manipulation
- **Server**: Gunicorn WSGI server
- **Deployment**: Railway (or any Python hosting)

## 📊 Success Stories

Incipit Genie has successfully:
- 📖 Converted manuscripts with 750+ endnotes
- ⏰ Saved authors 40-100 hours per manuscript
- ✅ Met requirements for major university presses
- 🌍 Helped academics worldwide

## 🤝 Contributing

Want to add more magic? Contributions are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-magic`)
3. Commit your changes (`git commit -m 'Add amazing magic'`)
4. Push to the branch (`git push origin feature/amazing-magic`)
5. Open a Pull Request

## 📝 Environment Variables

For production deployment on Railway:

```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
MAX_CONTENT_LENGTH=52428800
```

Railway automatically sets:
- `PORT` - The port your app should listen on
- `RAILWAY_ENVIRONMENT` - production/development

## 🚦 API Endpoints

- `GET /` - Main interface
- `POST /convert` - Upload and convert document
- Returns: Converted .docx file

## 🐛 Troubleshooting

### Common Issues

**File too large error**
- Maximum file size is 50MB
- Try splitting very large documents

**No endnotes found**
- Ensure your document uses Word's endnote feature
- Not compatible with manually typed references

**Page numbers not updating**
- Remember to select all (Cmd/Ctrl+A) and press F9 in Word

## 📧 Support & Contact

**Creator**: Eric Caplan  
**Email**: [caplane@gmail.com](mailto:caplane@gmail.com)  
**Issues**: Please use GitHub Issues for bug reports

## 📄 License

MIT License - Copyright (c) 2024 Eric Caplan

See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Developed for the academic community
- Inspired by the needs of university press publishing
- Special thanks to scholars who provided feedback

## 🌟 Why "Incipit Genie"?

"Incipit" (Latin: "it begins") refers to the first words of a text. Academic publishers often use the incipit format for citations, showing the beginning words of quoted passages. The Genie grants your wish by magically transforming traditional endnotes into this professional format!

---

**✨ Let Incipit Genie work its magic on your citations!**

*Transform your manuscript. Save your time. Focus on your research.*

Created with ❤️ and a touch of magic by Eric Caplan
