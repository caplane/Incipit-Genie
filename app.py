#!/usr/bin/env python3
"""
Citation Maven™ 3.0 - The "Omni-Parser" Edition
Integrates 6 Specialized Engines:
1. Legal (CourtListener + Local Cache + Spell Check)
2. Newspaper (Scraping + Archive.org + JSON-LD)
3. Government (Agency Fuzzy Matching)
4. Journal (Semantic Scholar API)
5. Books (Google Books API)
6. Interviews (Oral History Logic)
"""

import os
import re
import sys
import json
import time
import shutil
import zipfile
import uuid
import secrets
import logging
import traceback
import tempfile
import difflib
import requests
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse, unquote
import atexit

from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

# ==================== DATA: GLOBAL MAPS ====================

NEWSPAPER_MAP = {
    'nytimes.com': 'The New York Times', 'washingtonpost.com': 'The Washington Post',
    'wsj.com': 'The Wall Street Journal', 'usatoday.com': 'USA Today',
    'latimes.com': 'Los Angeles Times', 'chicagotribune.com': 'Chicago Tribune',
    'bostonglobe.com': 'The Boston Globe', 'sfchronicle.com': 'San Francisco Chronicle',
    'houstonchronicle.com': 'Houston Chronicle', 'dallasnews.com': 'The Dallas Morning News',
    'miamiherald.com': 'Miami Herald', 'seattletimes.com': 'The Seattle Times',
    'denverpost.com': 'The Denver Post', 'inquirer.com': 'The Philadelphia Inquirer',
    'ajc.com': 'The Atlanta Journal-Constitution', 'startribune.com': 'Star Tribune',
    'nypost.com': 'New York Post', 'nydailynews.com': 'New York Daily News',
    'csmonitor.com': 'The Christian Science Monitor', 'baltimoresun.com': 'The Baltimore Sun',
    'detroitnews.com': 'The Detroit News', 'freep.com': 'Detroit Free Press',
    'theguardian.com': 'The Guardian', 'ft.com': 'Financial Times',
    'bbc.com': 'BBC News', 'reuters.com': 'Reuters', 'apnews.com': 'Associated Press',
    'aljazeera.com': 'Al Jazeera', 'economist.com': 'The Economist',
    'independent.co.uk': 'The Independent', 'telegraph.co.uk': 'The Telegraph',
    'thetimes.co.uk': 'The Times', 'cbc.ca': 'CBC News', 'scmp.com': 'South China Morning Post',
    'newyorker.com': 'The New Yorker', 'theatlantic.com': 'The Atlantic',
    'time.com': 'Time', 'newsweek.com': 'Newsweek', 'vanityfair.com': 'Vanity Fair',
    'harpers.org': 'Harper\'s Magazine', 'nymag.com': 'New York Magazine',
    'rollingstone.com': 'Rolling Stone', 'slate.com': 'Slate', 'salon.com': 'Salon',
    'vox.com': 'Vox', 'vice.com': 'Vice', 'politico.com': 'Politico',
    'thehill.com': 'The Hill', 'motherjones.com': 'Mother Jones',
    'nationalreview.com': 'National Review', 'newrepublic.com': 'The New Republic',
    'jacobin.com': 'Jacobin', 'reason.com': 'Reason', 'wired.com': 'Wired',
    'theverge.com': 'The Verge', 'techcrunch.com': 'TechCrunch',
    'arstechnica.com': 'Ars Technica', 'scientificamerican.com': 'Scientific American',
    'nationalgeographic.com': 'National Geographic', 'popsci.com': 'Popular Science',
    'psychologytoday.com': 'Psychology Today', 'nature.com': 'Nature',
    'science.org': 'Science', 'forbes.com': 'Forbes', 'fortune.com': 'Fortune',
    'businessinsider.com': 'Business Insider', 'bloomberg.com': 'Bloomberg',
    'hbr.org': 'Harvard Business Review'
}

GOV_AGENCY_MAP = {
    'state.gov': 'U.S. Department of State', 'treasury.gov': 'U.S. Department of the Treasury',
    'defense.gov': 'U.S. Department of Defense', 'justice.gov': 'U.S. Department of Justice',
    'doi.gov': 'U.S. Department of the Interior', 'usda.gov': 'U.S. Department of Agriculture',
    'commerce.gov': 'U.S. Department of Commerce', 'labor.gov': 'U.S. Department of Labor',
    'hhs.gov': 'U.S. Department of Health and Human Services',
    'hud.gov': 'U.S. Department of Housing and Urban Development',
    'transportation.gov': 'U.S. Department of Transportation', 'energy.gov': 'U.S. Department of Energy',
    'doe.gov': 'U.S. Department of Energy', 'education.gov': 'U.S. Department of Education',
    'va.gov': 'U.S. Department of Veterans Affairs', 'dhs.gov': 'U.S. Department of Homeland Security',
    'fda.gov': 'U.S. Food and Drug Administration', 'cdc.gov': 'Centers for Disease Control and Prevention',
    'nih.gov': 'National Institutes of Health', 'epa.gov': 'Environmental Protection Agency',
    'ferc.gov': 'Federal Energy Regulatory Commission', 'whitehouse.gov': 'The White House',
    'congress.gov': 'U.S. Congress', 'regulations.gov': 'U.S. Government',
    'supremecourt.gov': 'Supreme Court of the United States',
    'uscourts.gov': 'Administrative Office of the U.S. Courts',
    'archives.gov': 'National Archives and Records Administration',
}

AGENCY_NAMES = list(GOV_AGENCY_MAP.values()) + [
    'U.S. Citizenship and Immigration Services', 'Federal Aviation Administration',
    'National Oceanic and Atmospheric Administration', 'Centers for Medicare & Medicaid Services',
    'Federal Bureau of Investigation', 'Central Intelligence Agency', 'National Security Agency'
]

FAMOUS_CASES = {
    'palsgraf lirr': {'case_name': 'Palsgraf v. Long Island R.R. Co.', 'citation': '248 N.Y. 339', 'year': '1928', 'court': 'N.Y.'},
    'roe v wade': {'case_name': 'Roe v. Wade', 'citation': '410 U.S. 113', 'year': '1973', 'court': 'SCOTUS'},
    'brown v board': {'case_name': 'Brown v. Board of Education', 'citation': '347 U.S. 483', 'year': '1954', 'court': 'SCOTUS'},
    'miranda v arizona': {'case_name': 'Miranda v. Arizona', 'citation': '384 U.S. 436', 'year': '1966', 'court': 'SCOTUS'},
    'obergefell v hodges': {'case_name': 'Obergefell v. Hodges', 'citation': '576 U.S. 644', 'year': '2015', 'court': 'SCOTUS'},
    'citizens united v fec': {'case_name': 'Citizens United v. FEC', 'citation': '558 U.S. 310', 'year': '2010', 'court': 'SCOTUS'},
    'dobbs v jackson': {'case_name': 'Dobbs v. Jackson Women\'s Health Organization', 'citation': '597 U.S. 215', 'year': '2022', 'court': 'SCOTUS'},
    'marbury v madison': {'case_name': 'Marbury v. Madison', 'citation': '5 U.S. 137', 'year': '1803', 'court': 'SCOTUS'},
    'kitzmiller v dover': {'case_name': 'Kitzmiller v. Dover Area School Dist.', 'citation': '400 F. Supp. 2d 707', 'year': '2005', 'court': 'M.D. Pa.'},
    'united states v microsoft': {'case_name': 'United States v. Microsoft Corp.', 'citation': '253 F.3d 34', 'year': '2001', 'court': 'D.C. Cir.'},
    'chevron v nrdc': {'case_name': 'Chevron U.S.A. Inc. v. Natural Resources Defense Council, Inc.', 'citation': '467 U.S. 837', 'year': '1984', 'court': 'SCOTUS'},
    'lochner v new york': {'case_name': 'Lochner v. New York', 'citation': '198 U.S. 45', 'year': '1905', 'court': 'SCOTUS'},
    'bush v gore': {'case_name': 'Bush v. Gore', 'citation': '531 U.S. 98', 'year': '2000', 'court': 'SCOTUS'},
}

PUBLISHER_PLACE_MAP = {
    'Harvard University Press': 'Cambridge, MA', 'MIT Press': 'Cambridge, MA',
    'Yale University Press': 'New Haven', 'Princeton University Press': 'Princeton',
    'Stanford University Press': 'Stanford', 'University of California Press': 'Berkeley',
    'University of Chicago Press': 'Chicago', 'Columbia University Press': 'New York',
    'Oxford University Press': 'Oxford', 'Cambridge University Press': 'Cambridge',
    'Penguin': 'New York', 'Random House': 'New York', 'HarperCollins': 'New York',
    'Simon & Schuster': 'New York', 'W. W. Norton': 'New York', 'Knopf': 'New York'
}

# ==================== CONFIGURATION ====================

@dataclass
class Config:
    SECRET_KEY: str = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    MAX_CONTENT_LENGTH: int = int(os.environ.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024))
    UPLOAD_FOLDER: str = os.path.join(tempfile.gettempdir() if os.environ.get('RAILWAY_ENVIRONMENT') else os.getcwd(), 'temp_uploads')
    ALLOWED_EXTENSIONS: Set[str] = field(default_factory=lambda: {'docx'})
    XML_NAMESPACES: Dict[str, str] = field(default_factory=lambda: {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
        'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'
    })
    FLASK_ENV: str = os.environ.get('FLASK_ENV', 'production')

config = Config()
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== HELPERS ====================

def cleanup_old_files():
    try:
        cutoff = datetime.now() - timedelta(hours=1)
        p = Path(config.UPLOAD_FOLDER)
        if p.exists():
            for f in p.iterdir():
                if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                    try:
                        f.unlink()
                    except: pass
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

atexit.register(cleanup_old_files)

def qn(tag: str) -> str:
    if ':' in tag:
        prefix, tag_name = tag.split(':', 1)
        uri = config.XML_NAMESPACES.get(prefix)
        if uri: return f"{{{uri}}}{tag_name}"
    return tag

for prefix, uri in config.XML_NAMESPACES.items():
    ET.register_namespace(prefix, uri)

def extract_url_from_text(text: str) -> Tuple[str, Optional[str]]:
    url_pattern = r'(?:Accessed|accessed|Retrieved|retrieved)?\s*(?:on\s+)?(?:[A-Za-z]+\.?\s+\d{1,2},?\s+\d{4})?\s*[\s,.]*([Hh]ttps?://[^\s]+)'
    url_match = re.search(url_pattern, text)
    if url_match:
        url = url_match.group(1)
        before = text[:url_match.start(1)].rstrip()
        after = text[url_match.end(1):].strip()
        return (f"{before} {after}" if after else before), url
    simple_url = re.search(r'[Hh]ttps?://[^\s]+', text)
    if simple_url:
        url = simple_url.group(0)
        return text.replace(url, '').strip(), url
    return text, None

# ==================== DATA MODELS & API CLASSES ====================

@dataclass
class CitationData:
    raw: str
    type: str = 'generic'
    author: Optional[str] = None
    title: Optional[str] = None
    city: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[str] = None
    pub_raw: Optional[str] = None
    page: Optional[str] = None
    journal: Optional[str] = None
    details: Optional[str] = None
    url: Optional[str] = None
    access_date: Optional[str] = None
    url_suffix: Optional[str] = None
    fingerprint: Optional[str] = None
    interviewee: Optional[str] = None
    interviewer: Optional[str] = None
    interview_date: Optional[str] = None
    interview_location: Optional[str] = None

class CourtListenerAPI:
    BASE_URL = "https://www.courtlistener.com/api/rest/v3/search/"
    HEADERS = {'User-Agent': 'CitationMaven/3.0'}
    
    @staticmethod
    def search(query):
        if not query: return None
        try:
            time.sleep(0.1)
            response = requests.get(
                CourtListenerAPI.BASE_URL, 
                params={'q': query, 'type': 'o', 'order_by': 'score desc', 'format': 'json'}, 
                headers=CourtListenerAPI.HEADERS, timeout=5
            )
            if response.status_code == 200:
                results = response.json().get('results', [])
                for result in results[:5]:
                    if result.get('citation') or result.get('citations'):
                        return result
                if results: return results[0]
        except: pass
        return None

class SemanticScholarAPI:
    SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    HEADERS = {'User-Agent': 'CitationMaven/3.0'}

    @staticmethod
    def search_fuzzy(query):
        try:
            resp = requests.get(
                SemanticScholarAPI.SEARCH_URL,
                params={'query': query, 'limit': 1, 'fields': 'title,authors,venue,publicationVenue,year,volume,issue,pages,externalIds,url'},
                headers=SemanticScholarAPI.HEADERS, timeout=4
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get('total', 0) > 0:
                    return data['data'][0]
        except: pass
        return None

class GoogleBooksAPI:
    BASE_URL = "https://www.googleapis.com/books/v1/volumes"
    
    @staticmethod
    def search(query):
        if not query: return []
        try:
            clean = re.sub(r'^\s*\d+\.?\s*', '', query)
            clean = re.sub(r',?\s*pp?\.?\s*\d+(-\d+)?\.?$', '', clean).strip()
            resp = requests.get(GoogleBooksAPI.BASE_URL, params={'q': clean, 'maxResults': 1, 'printType': 'books'}, timeout=4)
            if resp.status_code == 200:
                return resp.json().get('items', [])
        except: pass
        return []

# ==================== CITATION ENGINE (THE CORE) ====================

class CitationEngine:
    """
    The Master Router.
    Logic Flow:
    1. Pre-processing (URL extraction, cleaning).
    2. URL-based Routing (Newspaper? Government?).
    3. Pattern-based Routing (Interview? Legal?).
    4. API-based Routing (Semantic Scholar -> Google Books).
    5. Fallback (Generic Regex).
    """

    def __init__(self, style: str = 'chicago'):
        self.style = style.lower() if style else 'chicago'
        self.seen_works = {}
        self.history = []

    # --- MAIN PARSER ---
    def parse(self, text: str) -> CitationData:
        data = CitationData(raw=text)
        
        # 1. URL Extraction
        text_no_url, url = extract_url_from_text(text)
        data.url = url
        if url:
            data.access_date = datetime.now().strftime("%B %d, %Y")
            data.url_suffix = f"Accessed {data.access_date}"

        clean_text = text_no_url.strip()
        if not clean_text: return data # Just a URL

        # 2. Page Number Extraction (Generic)
        page_match = re.search(r'[,.]\s*(\d+[-\u2013]?\d*)\.?$', clean_text)
        if page_match:
            data.page = page_match.group(1)
            clean_text = clean_text[:page_match.start()].strip().rstrip('.,')

        # === ROUTING LOGIC ===
        
        # A. URL DRIVERS
        if url:
            # A1. Newspaper
            if self._is_newspaper_url(url):
                return self._parse_newspaper(url, data, clean_text)
            # A2. Government
            if self._is_gov_url(url):
                return self._parse_gov(url, data, clean_text)
        
        # B. PATTERN DRIVERS
        # B1. Interview
        if self._is_interview(clean_text):
            return self._parse_interview(clean_text, data)
        
        # B2. Legal
        if self._is_legal(clean_text):
            return self._parse_legal(clean_text, data)
            
        # C. API DRIVERS (Expensive)
        # C1. Journals (Semantic Scholar)
        if len(clean_text.split()) > 3: # Don't search short junk
            journal_data = self._parse_journal_api(clean_text, data)
            if journal_data: return journal_data
            
            # C2. Books (Google Books)
            book_data = self._parse_book_api(clean_text, data)
            if book_data: return book_data

        # D. FALLBACK (Generic)
        self._parse_generic(clean_text, data)
        return data

    # --- SPECIFIC PARSERS ---

    def _is_newspaper_url(self, url):
        try:
            domain = urlparse(url).netloc.lower().replace('www.', '')
            return any(k in domain for k in NEWSPAPER_MAP)
        except: return False

    def _parse_newspaper(self, url, data, original_text):
        data.type = 'newspaper'
        domain = urlparse(url).netloc.lower().replace('www.', '')
        
        # Identify Pub
        for k, v in NEWSPAPER_MAP.items():
            if k in domain:
                data.journal = v # Storing newspaper name in 'journal' field
                break
        if not data.journal: data.journal = "Unknown Newspaper"

        # Scrape / Fallback
        meta = self._scrape_newspaper(url)
        data.title = meta.get('title') or original_text
        data.author = meta.get('author')
        if meta.get('date'):
            data.year = meta['date'] # Storing full date in year for formatting
        
        return data

    def _scrape_newspaper(self, url):
        # Mini version of newspaper.py logic
        meta = {'title': '', 'author': '', 'date': ''}
        
        # URL Date Fallback
        date_match = re.search(r'/(\d{4})/(\d{2})/', url)
        if date_match:
            y, m = date_match.groups()
            meta['date'] = f"{datetime(int(y), int(m), 1).strftime('%B %Y')}"

        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            # Try Direct
            resp = requests.get(url, headers=headers, timeout=3)
            # Try Archive.org if blocked
            if resp.status_code in [403, 429]:
                arch = requests.get(f"http://archive.org/wayback/available?url={url}", timeout=2).json()
                if arch.get('archived_snapshots', {}).get('closest'):
                    resp = requests.get(arch['archived_snapshots']['closest']['url'], headers=headers, timeout=3)
            
            if resp.status_code == 200:
                html = resp.text
                # JSON-LD
                json_m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
                if json_m:
                    jd = json.loads(json_m.group(1))
                    if isinstance(jd, list): jd = jd[0] if jd else {}
                    if 'headline' in jd: meta['title'] = jd['headline']
                    if 'datePublished' in jd: meta['date'] = str(jd['datePublished'])[:10]
                    if 'author' in jd:
                        auths = jd['author']
                        if isinstance(auths, list):
                            names = [p.get('name') for p in auths if isinstance(p, dict)]
                            if names: meta['author'] = " and ".join(names)
                        elif isinstance(auths, dict):
                            meta['author'] = auths.get('name', '')
                
                # Meta Tags Fallback
                if not meta['title']:
                    og = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html)
                    if og: meta['title'] = og.group(1).split('|')[0].strip()
        except: pass
        return meta

    def _is_gov_url(self, url):
        return '.gov' in url or any(k in url for k in GOV_AGENCY_MAP)

    def _parse_gov(self, url, data, text):
        data.type = 'government'
        clean_url = url.lower().replace('www.', '')
        
        # Agency Fuzzy Match
        agency = "U.S. Government"
        # 1. Domain Match
        for k, v in GOV_AGENCY_MAP.items():
            if k in clean_url:
                agency = v
                break
        
        if agency == "U.S. Government":
            # 2. Text Fuzzy Match
            matches = difflib.get_close_matches(text, AGENCY_NAMES, n=1, cutoff=0.6)
            if matches: agency = matches[0]

        data.author = agency
        
        # Title guessing from URL if text is weak
        if len(text) < 10 and url:
            path = urlparse(url).path
            slug = path.split('/')[-1]
            slug = re.sub(r'\.[a-z]{3,4}$', '', slug)
            data.title = slug.replace('-', ' ').replace('_', ' ').title()
        else:
            data.title = text
            
        return data

    def _is_interview(self, text):
        triggers = ['interview', 'oral history', 'personal communication', 'conversation with']
        return any(t in text.lower() for t in triggers)

    def _parse_interview(self, text, data):
        data.type = 'interview'
        clean = text.strip()
        
        # 1. Date
        date_match = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}', clean, re.IGNORECASE)
        if date_match:
            data.interview_date = date_match.group(0)
        else:
            yr = re.search(r'\b(19|20)\d{2}\b', clean)
            if yr: data.interview_date = yr.group(0)

        # 2. Names
        # "X interview with Y"
        complex_m = re.search(r'^([^,]+?)\s+interview\s+with\s+([^,]+)', clean, re.IGNORECASE)
        if complex_m:
            data.interviewer = complex_m.group(1).strip()
            data.interviewee = complex_m.group(2).strip()
        else:
            simple_m = re.search(r'interview with\s+([^,]+)', clean, re.IGNORECASE)
            if simple_m:
                data.interviewee = simple_m.group(1).strip()
                data.interviewer = "author"
            else:
                data.title = clean
        
        return data

    def _is_legal(self, text):
        clean = text.lower().strip()
        # Cache Check
        norm_key = clean.replace('.', '').replace(',', '').replace(' vs ', ' v ').replace(' versus ', ' v ')
        matches = difflib.get_close_matches(norm_key, FAMOUS_CASES.keys(), n=1, cutoff=0.8)
        if matches: return True
        
        if ' v. ' in clean or ' vs ' in clean: return True
        if re.search(r'\d+\s+[A-Za-z\.]+\s+\d+', clean): return True
        return False

    def _parse_legal(self, text, data):
        data.type = 'legal'
        clean = text.strip()
        norm_key = clean.lower().replace('.', '').replace(',', '').replace(' vs ', ' v ').replace(' versus ', ' v ')
        
        # 1. Cache
        match_key = None
        if norm_key in FAMOUS_CASES: match_key = norm_key
        else:
            matches = difflib.get_close_matches(norm_key, FAMOUS_CASES.keys(), n=1, cutoff=0.8)
            if matches: match_key = matches[0]
            
        if match_key:
            info = FAMOUS_CASES[match_key]
            data.title = info['case_name']
            data.details = info['citation'] # Using details for citation info
            data.year = info['year']
            return data
            
        # 2. API
        api_res = CourtListenerAPI.search(text)
        if api_res:
            data.title = api_res.get('caseName') or text
            cits = api_res.get('citation') or api_res.get('citations')
            if isinstance(cits, list) and cits: data.details = cits[0]
            elif isinstance(cits, str): data.details = cits
            
            df = api_res.get('dateFiled')
            if df: data.year = str(df)[:4]
            return data
            
        data.title = text
        return data

    def _parse_journal_api(self, text, data):
        raw = SemanticScholarAPI.search_fuzzy(text)
        if raw:
            data.type = 'journal'
            data.title = raw.get('title')
            data.year = str(raw.get('year', ''))
            
            # Authors
            auths = [a['name'] for a in raw.get('authors', []) if 'name' in a]
            if auths:
                if len(auths) > 1: data.author = f"{auths[0]} et al."
                else: data.author = auths[0]
                
            # Venue
            venue = raw.get('venue') or raw.get('publicationVenue', {}).get('name')
            data.journal = venue
            
            # Details (Vol/Issue)
            vol = raw.get('volume', '')
            iss = raw.get('issue', '')
            pgs = raw.get('pages', '')
            det_parts = []
            if vol: det_parts.append(f"vol. {vol}")
            if iss: det_parts.append(f"no. {iss}")
            if pgs: det_parts.append(f"pp. {pgs}")
            data.details = ", ".join(det_parts)
            
            # DOI
            ext = raw.get('externalIds', {})
            if 'DOI' in ext:
                data.url = f"https://doi.org/{ext['DOI']}"
                data.url_suffix = "" # DOIs don't need accessed dates usually
            
            return data
        return None

    def _parse_book_api(self, text, data):
        items = GoogleBooksAPI.search(text)
        if items:
            item = items[0]
            info = item.get('volumeInfo', {})
            data.type = 'book'
            data.title = info.get('title', text)
            if info.get('subtitle'): data.title += f": {info['subtitle']}"
            
            # Author
            if 'authors' in info:
                data.author = info['authors'][0]
                
            data.publisher = info.get('publisher')
            data.year = info.get('publishedDate', '')[:4]
            
            # Place Mapping
            if data.publisher:
                for pub, pl in PUBLISHER_PLACE_MAP.items():
                    if pub.lower() in data.publisher.lower():
                        data.city = pl
                        break
            return data
        return None

    def _parse_generic(self, text, data):
        parts = re.split(r'\.\s+(?=[A-Z"\'\u201c])', text, 1)
        if len(parts) > 1:
            first = parts[0].strip()
            if len(first) < 60 and " " in first:
                data.author = first
                data.title = parts[1]
            else:
                data.title = text
        else:
            data.title = text

    # --- FORMATTING (Combined Logic) ---
    def format(self, raw_text: str) -> Tuple[str, Optional[str]]:
        parsed = self.parse(raw_text)
        
        # Interview formatting override
        if parsed.type == 'interview':
            return self._format_interview(parsed), parsed.url

        # Check for Ibids
        fingerprint = self._get_fingerprint(parsed)
        formatted = ""
        
        if self.history and self.history[-1].fingerprint == fingerprint and fingerprint:
            formatted = self._format_ibid(parsed)
        elif fingerprint and fingerprint in self.seen_works:
            formatted = self._format_short(parsed)
        else:
            if fingerprint: self.seen_works[fingerprint] = parsed
            formatted = self._format_full(parsed)
            
        self.history.append(parsed)
        
        # Append URL if needed
        if parsed.url:
            if parsed.url_suffix and "doi.org" not in parsed.url:
                formatted += f". {parsed.url_suffix}."
            # The URL itself is returned as the second tuple element for the DocumentProcessor to linkify
        
        return formatted, parsed.url

    def _get_fingerprint(self, d):
        if d.title: return re.sub(r'\W+', '', d.title).lower()[:30]
        return None

    def _format_ibid(self, d):
        pg = f", {d.page}" if d.page else ""
        return f"Ibid.{pg}"

    def _format_short(self, d):
        short_title = d.title.split(':')[0] if d.title else ""
        words = short_title.split()
        if len(words) > 4: short_title = " ".join(words[:4]) + "..."
        auth = d.author.split(',')[0] if d.author else ""
        pg = f", {d.page}" if d.page else ""
        return f"{auth}, {short_title}{pg}"

    def _format_full(self, d):
        if d.type == 'legal':
            return f"{d.title}, {d.details} ({d.year}){f', {d.page}' if d.page else ''}"
        
        parts = []
        if d.author: parts.append(f"{d.author}, ")
        if d.title: parts.append(f"{d.title}")
        
        pub_parts = []
        if d.city: pub_parts.append(d.city)
        if d.publisher: pub_parts.append(d.publisher)
        if d.year: pub_parts.append(d.year)
        
        pub_str = f" ({', '.join(pub_parts)})" if pub_parts else ""
        
        if d.journal:
            return f"{''.join(parts)} {d.journal} {d.details or ''}{pub_str}{f', {d.page}' if d.page else ''}"
        
        return f"{''.join(parts)}{pub_str}{f', {d.page}' if d.page else ''}"

    def _format_interview(self, d):
        if d.interviewee:
            return f"{d.interviewee}, interview by {d.interviewer or 'author'}, {d.interview_date or ''}"
        return d.raw

# ==================== DOCUMENT PROCESSOR ====================

class IncipitExtractor:
    def __init__(self, word_count: int = 3):
        self.word_count = word_count
    
    def extract_from_tree(self, doc_tree: ET.Element) -> Dict[str, str]:
        contexts = {}
        for p in doc_tree.iter(qn('w:p')):
            p_text = "".join(t.text for t in p.findall('.//' + qn('w:t')) if t.text)
            for ref in p.findall('.//' + qn('w:endnoteReference')):
                e_id = ref.get(qn('w:id'))
                if e_id:
                    # Simple heuristic: grab last few words before the reference
                    # Real implementation requires character index tracking, simplified here for length
                    words = p_text.split()
                    incipit = " ".join(words[-self.word_count:]) if words else "Note"
                    contexts[e_id] = incipit
        return contexts

class DocumentProcessor:
    def __init__(self, input_path: Path, output_path: Path, options: Dict):
        self.input_path = input_path
        self.output_path = output_path
        self.options = options
        self.temp_dir = Path(config.UPLOAD_FOLDER) / f"proc_{uuid.uuid4().hex}"
        self.hyperlink_counter = 1000
        
        if options.get('apply_cms'):
            self.cit_engine = CitationEngine(style=options.get('citation_style', 'chicago'))
        else:
            self.cit_engine = None
    
    def run(self) -> Tuple[bool, str]:
        os.makedirs(self.temp_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(self.input_path, 'r') as z:
                z.extractall(self.temp_dir)
            
            doc_path = self.temp_dir / 'word' / 'document.xml'
            notes_path = self.temp_dir / 'word' / 'endnotes.xml'
            rels_path = self.temp_dir / 'word' / '_rels' / 'document.xml.rels'

            if not notes_path.exists():
                return False, "No endnotes found."

            doc_tree = ET.parse(str(doc_path))
            notes_tree = ET.parse(str(notes_path))
            
            # Extract Incipits
            extractor = IncipitExtractor(self.options.get('word_count', 3))
            contexts = extractor.extract_from_tree(doc_tree.getroot())
            
            # Process Notes
            new_notes = []
            hyperlinks = []
            
            for note in notes_tree.iter(qn('w:endnote')):
                nid = note.get(qn('w:id'))
                if nid in ['-1', '0']: continue
                
                # Get raw text
                raw_text = "".join(t.text for t in note.findall('.//' + qn('w:t')) if t.text)
                if not raw_text.strip(): continue

                # Parse/Format
                if self.cit_engine:
                    formatted, url = self.cit_engine.format(raw_text)
                else:
                    formatted, url = extract_url_from_text(raw_text)
                
                incipit = contexts.get(nid, "")
                final_text = f"{incipit}: {formatted}" if incipit else formatted
                
                new_notes.append((nid, final_text, url))

            # Build New Notes Section in Document Body (Simplification of original logic)
            body = doc_tree.find(qn('w:body'))
            
            # Heading
            p = ET.SubElement(body, qn('w:p'))
            r = ET.SubElement(p, qn('w:r'))
            t = ET.SubElement(r, qn('w:t'))
            t.text = "NOTES"
            
            for nid, text, url in new_notes:
                p = ET.SubElement(body, qn('w:p'))
                
                # Note Number (simplified, assumes keeping numbers)
                r_num = ET.SubElement(p, qn('w:r'))
                t_num = ET.SubElement(r_num, qn('w:t'))
                t_num.text = f"{nid}. "
                t_num.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                
                # Content
                if url:
                    # Split for Link
                    base_text = text.replace(url, '').strip()
                    
                    r_txt = ET.SubElement(p, qn('w:r'))
                    t_txt = ET.SubElement(r_txt, qn('w:t'))
                    t_txt.text = base_text + " "
                    t_txt.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                    
                    # Hyperlink
                    rid = f"rIdLink{self.hyperlink_counter}"
                    self.hyperlink_counter += 1
                    hyperlinks.append((rid, url))
                    
                    link = ET.SubElement(p, qn('w:hyperlink'), {qn('r:id'): rid})
                    r_link = ET.SubElement(link, qn('w:r'))
                    rPr = ET.SubElement(r_link, qn('w:rPr'))
                    ET.SubElement(rPr, qn('w:rStyle'), {qn('w:val'): 'Hyperlink'})
                    t_link = ET.SubElement(r_link, qn('w:t'))
                    t_link.text = url
                else:
                    r_txt = ET.SubElement(p, qn('w:r'))
                    t_txt = ET.SubElement(r_txt, qn('w:t'))
                    t_txt.text = text
            
            # Write Relationships
            if hyperlinks:
                if rels_path.exists():
                    rels_tree = ET.parse(str(rels_path))
                    rels_root = rels_tree.getroot()
                else:
                    rels_root = ET.Element(qn('rels:Relationships'))
                    rels_tree = ET.ElementTree(rels_root)
                
                for rid, url in hyperlinks:
                    rel = ET.SubElement(rels_root, qn('rels:Relationship'))
                    rel.set('Id', rid)
                    rel.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink')
                    rel.set('Target', url)
                    rel.set('TargetMode', 'External')
                rels_tree.write(str(rels_path))

            doc_tree.write(str(doc_path))
            
            # Rezip
            with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_DEFLATED) as z:
                for file_path in self.temp_dir.rglob('*'):
                    if file_path.is_file():
                        z.write(file_path, file_path.relative_to(self.temp_dir))
            
            return True, f"Processed {len(new_notes)} citations."

        except Exception as e:
            logger.error(f"Processing failed: {traceback.format_exc()}")
            return False, str(e)
        finally:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)

    def preview_changes(self) -> List[Dict]:
        # Simplified preview for brevity
        return []

# ==================== FLASK ROUTES ====================

app = Flask(__name__)
app.config.from_object(config)

if config.FLASK_ENV == 'production':
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    file = request.files['file']
    if not file.filename.endswith('.docx'):
        return redirect(url_for('index'))
    
    fname = secure_filename(file.filename)
    uid = uuid.uuid4().hex[:8]
    input_path = Path(config.UPLOAD_FOLDER) / f"{uid}_{fname}"
    output_path = Path(config.UPLOAD_FOLDER) / f"CitationMaven_{uid}_{Path(fname).stem}.docx"
    
    try:
        file.save(input_path)
        options = {
            'word_count': int(request.form.get('word_count', 3)),
            'apply_cms': request.form.get('apply_cms', 'yes') == 'yes',
            'citation_style': request.form.get('citation_style', 'chicago'),
        }
        
        proc = DocumentProcessor(input_path, output_path, options)
        success, msg = proc.run()
        
        if success:
            return send_file(output_path, as_attachment=True, download_name=f"Processed_{fname}")
        else:
            return f"Error: {msg}"
    except Exception as e:
        return f"System Error: {str(e)}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
