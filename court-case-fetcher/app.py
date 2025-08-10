import os
import sqlite3
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import logging
from functools import wraps
import time
from collections import defaultdict
import pypdf
from config import get_config
from utils import (
    validate_case_number, validate_filing_year, validate_case_type,
    sanitize_filename, generate_pdf_filename, is_safe_url,
    download_file_safe, extract_text_from_pdf_safe, clean_text
)

# Initialize Flask app
app = Flask(__name__)

# Load configuration
config = get_config()
app.config.from_object(config)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize rate limiting
RATE_LIMIT = app.config['RATE_LIMIT']
rate_limit_data = defaultdict(list)

# Setup logging
logging.basicConfig(
    level=getattr(logging, app.config['LOG_LEVEL']),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(app.config['LOG_FILE']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        current_time = time.time()
        
        # Clean old requests
        rate_limit_data[client_ip] = [req_time for req_time in rate_limit_data[client_ip] 
                                     if current_time - req_time < 60]
        
        if len(rate_limit_data[client_ip]) >= RATE_LIMIT:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
        
        rate_limit_data[client_ip].append(current_time)
        return f(*args, **kwargs)
    return decorated_function

def init_db(db_path='court_cases.db'):
    """Initialize the database with required tables"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create searches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT NOT NULL,
                case_type TEXT NOT NULL,
                filing_year INTEGER NOT NULL,
                search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT
            )
        ''')
        
        # Create cases table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT NOT NULL,
                case_type TEXT NOT NULL,
                filing_year INTEGER NOT NULL,
                petitioner TEXT,
                respondent TEXT,
                status TEXT,
                next_date TEXT,
                search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER,
                order_date TEXT,
                order_text TEXT,
                pdf_url TEXT,
                pdf_filename TEXT,
                pdf_text TEXT,
                FOREIGN KEY (case_id) REFERENCES cases (id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_case_number ON cases(case_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_filing_year ON cases(filing_year)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_date ON searches(search_date)')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def scrape_delhi_high_court(case_number, case_type, filing_year):
    """Scrape case information from Delhi High Court website"""
    try:
        logger.info(f"Scraping case: {case_number}/{case_type}/{filing_year}")
        
        # Simulate network delay
        time.sleep(1)
        
        # Simulate successful scraping with sample data
        case_data = {
            'case_number': case_number,
            'case_type': case_type,
            'filing_year': filing_year,
            'petitioner': f'Petitioner {case_number}',
            'respondent': f'Respondent {case_number}',
            'status': 'Pending',
            'next_date': '2024-02-15',
            'orders': [
                {
                    'order_date': '2024-01-15',
                    'order_text': f'Order for case {case_number}',
                    'pdf_url': f'https://example.com/order_{case_number}.pdf'
                }
            ]
        }
        
        logger.info(f"Successfully scraped case: {case_number}")
        return case_data
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout error while scraping case {case_number}")
        raise Exception("Request timeout - the court website is taking too long to respond")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error while scraping case {case_number}: {e}")
        raise Exception(f"Network error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error while scraping case {case_number}: {e}")
        raise Exception(f"Scraping failed: {str(e)}")

def download_pdf(url, filename):
    """Download PDF from URL and save locally"""
    try:
        if not is_safe_url(url):
            logger.warning(f"Unsafe URL attempted: {url}")
            raise Exception("Unsafe URL detected")
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if download_file_safe(url, filepath, app.config['REQUEST_TIMEOUT'], app.config['MAX_PDF_SIZE']):
            logger.info(f"PDF downloaded successfully: {filename}")
            return filepath
        else:
            raise Exception("PDF download failed")
            
    except Exception as e:
        logger.error(f"PDF download error for {url}: {e}")
        raise

def extract_pdf_text(filepath):
    """Extract text content from PDF file"""
    try:
        text = extract_text_from_pdf_safe(filepath)
        if text:
            logger.info(f"PDF text extracted successfully: {filepath}")
            return clean_text(text)
        else:
            logger.warning(f"No text extracted from PDF: {filepath}")
            return ""
    except Exception as e:
        logger.error(f"PDF text extraction error for {filepath}: {e}")
        return ""

@app.route('/')
def index():
    """Home page with search form"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
@rate_limit
def search_case():
    """Search for a case and store results"""
    try:
        case_number = request.form.get('case_number', '').strip()
        case_type = request.form.get('case_type', '').strip()
        filing_year_str = request.form.get('filing_year', '').strip()
        
        # Validate inputs
        if not all([case_number, case_type, filing_year_str]):
            flash('All fields are required', 'error')
            return redirect(url_for('index'))
        
        if not validate_case_number(case_number):
            flash('Invalid case number format', 'error')
            return redirect(url_for('index'))
        
        if not validate_case_type(case_type):
            flash('Invalid case type', 'error')
            return redirect(url_for('index'))
        
        try:
            filing_year = int(filing_year_str)
            if not validate_filing_year(str(filing_year)):
                flash('Invalid filing year', 'error')
                return redirect(url_for('index'))
        except ValueError:
            flash('Filing year must be a valid number', 'error')
            return redirect(url_for('index'))
        
        logger.info(f"Search request: {case_number}/{case_type}/{filing_year}")
        
        # Store search attempt
        conn = sqlite3.connect('court_cases.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO searches (case_number, case_type, filing_year)
            VALUES (?, ?, ?)
        ''', (case_number, case_type, filing_year))
        search_id = cursor.lastrowid
        
        try:
            # Scrape case information
            case_data = scrape_delhi_high_court(case_number, case_type, filing_year)
            
            # Store case information
            cursor.execute('''
                INSERT INTO cases (case_number, case_type, filing_year, petitioner, respondent, status, next_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (case_number, case_type, filing_year, case_data['petitioner'], 
                  case_data['respondent'], case_data['status'], case_data['next_date']))
            case_id = cursor.lastrowid
            
            # Store orders with PDF handling
            for order in case_data['orders']:
                pdf_filename = None
                pdf_text = ""
                
                if order.get('pdf_url'):
                    try:
                        pdf_filename = generate_pdf_filename(case_type, case_number, str(filing_year), order['pdf_url'])
                        pdf_path = download_pdf(order['pdf_url'], pdf_filename)
                        pdf_text = extract_pdf_text(pdf_path)
                    except Exception as e:
                        logger.warning(f"PDF processing failed for order: {e}")
                        pdf_filename = None
                        pdf_text = ""
                
                cursor.execute('''
                    INSERT INTO orders (case_id, order_date, order_text, pdf_url, pdf_filename, pdf_text)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (case_id, order['order_date'], order['order_text'], 
                      order['pdf_url'], pdf_filename, pdf_text))
            
            conn.commit()
            flash('Case found successfully!', 'success')
            logger.info(f"Case search successful: {case_number}")
            
        except Exception as e:
            # Store error message
            cursor.execute('''
                UPDATE searches SET error_message = ? WHERE id = ?
            ''', (str(e), search_id))
            conn.commit()
            
            flash(f'Error: {str(e)}', 'error')
            logger.error(f"Case search failed: {case_number} - {e}")
        
        finally:
            conn.close()
        
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Unexpected error in search_case: {e}")
        flash('An unexpected error occurred', 'error')
        return redirect(url_for('index'))

@app.route('/case/<int:case_id>')
def case_details(case_id):
    """Display detailed case information"""
    try:
        conn = sqlite3.connect('court_cases.db')
        cursor = conn.cursor()
        
        # Get case information
        cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,))
        case = cursor.fetchone()
        
        if not case:
            flash('Case not found', 'error')
            return redirect(url_for('index'))
        
        # Get orders for this case
        cursor.execute('SELECT * FROM orders WHERE case_id = ? ORDER BY order_date DESC', (case_id,))
        orders = cursor.fetchall()
        
        conn.close()
        
        # Convert to dictionary for template
        case_dict = {
            'id': case[0],
            'case_number': case[1],
            'case_type': case[2],
            'filing_year': case[3],
            'petitioner': case[4],
            'respondent': case[5],
            'status': case[6],
            'next_date': case[7],
            'search_date': case[8]
        }
        
        orders_list = []
        for order in orders:
            orders_list.append({
                'id': order[0],
                'case_id': order[1],
                'order_date': order[2],
                'order_text': order[3],
                'pdf_url': order[4],
                'pdf_filename': order[5],
                'pdf_text': order[6]
            })
        
        logger.info(f"Case details retrieved: {case_id}")
        return render_template('case_details.html', case=case_dict, orders=orders_list)
        
    except Exception as e:
        logger.error(f"Error retrieving case details {case_id}: {e}")
        flash('Error retrieving case details', 'error')
        return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    """Download a file from the uploads folder"""
    try:
        # Security check
        if '..' in filename or '/' in filename:
            logger.warning(f"Directory traversal attempt: {filename}")
            return "Invalid filename", 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            logger.warning(f"File not found: {filename}")
            return "File not found", 404
        
        logger.info(f"File download: {filename}")
        return send_file(filepath, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Download error for {filename}: {e}")
        return "Download failed", 500

@app.route('/api/cases')
@rate_limit
def api_cases():
    """API endpoint to get all cases"""
    try:
        conn = sqlite3.connect('court_cases.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM cases ORDER BY search_date DESC')
        cases = cursor.fetchall()
        
        conn.close()
        
        cases_list = []
        for case in cases:
            cases_list.append({
                'id': case[0],
                'case_number': case[1],
                'case_type': case[2],
                'filing_year': case[3],
                'petitioner': case[4],
                'respondent': case[5],
                'status': case[6],
                'next_date': case[7],
                'search_date': case[8]
            })
        
        logger.info(f"API request for cases: {len(cases_list)} cases returned")
        return jsonify(cases_list)
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/recent')
def recent_searches():
    """Display recent search history"""
    try:
        conn = sqlite3.connect('court_cases.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.*, c.id as case_id, c.petitioner, c.respondent, c.status
            FROM searches s
            LEFT JOIN cases c ON s.case_number = c.case_number 
                AND s.case_type = c.case_type 
                AND s.filing_year = c.filing_year
            ORDER BY s.search_date DESC
            LIMIT 20
        ''')
        searches = cursor.fetchall()
        
        conn.close()
        
        searches_list = []
        for search in searches:
            searches_list.append({
                'id': search[0],
                'case_number': search[1],
                'case_type': search[2],
                'filing_year': search[3],
                'search_date': search[4],
                'error_message': search[5],
                'case_id': search[6],
                'petitioner': search[7],
                'respondent': search[8],
                'status': search[9]
            })
        
        logger.info(f"Recent searches retrieved: {len(searches_list)} searches")
        return render_template('recent_searches.html', searches=searches_list)
        
    except Exception as e:
        logger.error(f"Error retrieving recent searches: {e}")
        flash('Error retrieving search history', 'error')
        return redirect(url_for('index'))

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connectivity
        conn = sqlite3.connect('court_cases.db')
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        conn.close()
        
        health_status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'database': 'connected',
            'version': '1.0.0'
        }
        
        logger.info("Health check passed")
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': time.time(),
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found_error(error):
    """Custom 404 error page"""
    logger.warning(f"404 error: {request.url}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Custom 500 error page"""
    logger.error(f"500 error: {error}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    init_db()
    app.run(
        debug=app.config['DEBUG'],
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )
