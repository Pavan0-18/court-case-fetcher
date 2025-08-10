# Court Case Fetcher

A Flask-based web application for fetching and managing court case information from the Delhi High Court website.

## Features

- **Case Search**: Search for cases by case number, type, and filing year
- **PDF Processing**: Download and extract text from court documents
- **Database Storage**: SQLite database for case and search history
- **Web Interface**: User-friendly web interface for case management
- **API Endpoints**: RESTful API for programmatic access
- **Rate Limiting**: Protection against abuse
- **Logging**: Comprehensive logging and error handling
- **Configuration Management**: Environment-based configuration system

### Technical Features
- **Database**: SQLite database with optimized indexes
- **File Storage**: Secure file upload and download system
- **Web Scraping**: BeautifulSoup-based court website scraping
- **Testing**: Comprehensive test suite with pytest

## Installation

### Prerequisites
- Python 3.11 or higher
- pip package manager
- Git (for cloning the repository)

### Local Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd court-case-fetcher
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env file with your configuration
   ```

5. **Initialize the database**
   ```bash
   python init_db.py
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

The application will be available at `http://localhost:5000`

## Configuration

The application uses environment variables for configuration. Key configuration options:

### Flask Configuration
- `FLASK_ENV`: Environment (development/production/testing)
- `SECRET_KEY`: Secret key for session management
- `DEBUG`: Enable/disable debug mode
- `PORT`: Application port

### Database Configuration
- `DATABASE_URL`: Database connection string

### File Upload Configuration
- `UPLOAD_FOLDER`: Directory for storing downloaded files
- `MAX_CONTENT_LENGTH`: Maximum file size limit
- `MAX_PDF_SIZE`: Maximum PDF file size

### Rate Limiting
- `RATE_LIMIT`: Maximum requests per minute per IP

### Logging Configuration
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)
- `LOG_FILE`: Log file path

## Usage

### Web Interface

1. **Home Page** (`/`)
   - Search form for case information
   - Input case number, type, and filing year

2. **Case Details** (`/case/<id>`)
   - View detailed case information
   - Download associated documents
   - View case history and orders

3. **Recent Searches** (`/recent`)
   - Browse search history
   - Quick access to previous searches

4. **API Endpoints** (`/api/*`)
   - Programmatic access to case data
   - JSON responses for integration

### API Usage

```bash
# Get all cases
GET /api/cases

# Search for cases
POST /search
{
    "case_number": "1234",
    "case_type": "WP(C)",
    "filing_year": 2023
}
```

## Monitoring

### Health Check Endpoint
- **URL**: `/health`
- **Purpose**: Application health monitoring
- **Response**: JSON status with timestamp

## Development

### Project Structure
```
court-case-fetcher/
├── app.py              # Main Flask application
├── config.py           # Configuration management
├── utils.py            # Utility functions
├── init_db.py          # Database initialization
├── test_app.py         # Test suite
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates
├── downloads/          # File storage
└── logs/              # Application logs
```

### Adding New Features

1. **Update Configuration**: Add new options to `config.py`
2. **Create Utilities**: Add helper functions to `utils.py`
3. **Update Database**: Modify schema in `init_db.py`
4. **Add Tests**: Include test coverage in `test_app.py`
5. **Update Documentation**: Modify this README

## Troubleshooting

### Common Issues

1. **Database Errors**
   - Ensure database file is writable
   - Check database initialization

2. **File Download Issues**
   - Verify upload folder permissions
   - Check file size limits

3. **Rate Limiting**
   - Adjust `RATE_LIMIT` configuration
   - Check client IP address

4. **Logging Issues**
   - Verify log file permissions
   - Check log level configuration

### Debug Mode

Enable debug mode for detailed error information:

```bash
export DEBUG=True
python app.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the logs for error information

## Changelog

### Version 1.0.0
- Initial release with core functionality
- PDF download and text extraction
- Comprehensive logging and error handling
- Rate limiting and security features
- Complete test suite
