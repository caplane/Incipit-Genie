#!/usr/bin/env python3
"""
Test script to verify Incipit Genie works locally before deployment
Run this with: python3 test_local.py
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    try:
        import flask
        print("✅ Flask imported successfully")
    except ImportError:
        print("❌ Flask not installed - run: pip install -r requirements.txt")
        return False
    
    try:
        import gunicorn
        print("✅ Gunicorn imported successfully")
    except ImportError:
        print("❌ Gunicorn not installed - run: pip install -r requirements.txt")
        return False
    
    return True

def test_files():
    """Test that all required files exist"""
    print("\nChecking required files...")
    required_files = [
        'app.py',
        'templates/index.html',
        'requirements.txt',
        'railway.json',
        'runtime.txt',
        'Procfile',
        '.gitignore',
        'LICENSE',
        'README.md'
    ]
    
    all_present = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} MISSING!")
            all_present = False
    
    return all_present

def test_app_syntax():
    """Test that app.py has valid Python syntax"""
    print("\nChecking app.py syntax...")
    try:
        with open('app.py', 'r') as f:
            code = f.read()
        compile(code, 'app.py', 'exec')
        print("✅ app.py syntax is valid")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in app.py: {e}")
        return False

def test_app_runs():
    """Test that the Flask app can be created"""
    print("\nTesting Flask app creation...")
    try:
        from app import app
        print("✅ Flask app created successfully")
        print(f"   Routes available: {len(app.url_map._rules)}")
        return True
    except Exception as e:
        print(f"❌ Error creating Flask app: {e}")
        return False

def main():
    print("=" * 60)
    print("🧞 INCIPIT GENIE LOCAL TEST")
    print("=" * 60)
    
    tests = [
        test_imports(),
        test_files(),
        test_app_syntax(),
        test_app_runs()
    ]
    
    print("\n" + "=" * 60)
    if all(tests):
        print("✅ ALL TESTS PASSED!")
        print("\nYour app is ready for deployment to Railway!")
        print("\nTo test locally, run:")
        print("  python3 app.py")
        print("Then visit: http://localhost:5000")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease fix the issues above before deploying.")
    print("=" * 60)

if __name__ == "__main__":
    main()
