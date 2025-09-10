# ConvertHub API Python Examples

Complete Python code examples for integrating with the [ConvertHub API](https://converthub.com/api) - a powerful file conversion service supporting 800+ format pairs.

## 🚀 Quick Start

1. **Get your API key** from [https://converthub.com/api](https://converthub.com/api)
2. **Clone this repository**:
   ```bash
   git clone https://github.com/converthub-api/python-examples.git
   cd python-examples
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure your API key**:
   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```
5. **Run any example**:
   ```bash
   python simple-convert/convert.py document.pdf docx
   ```

## 📁 Examples Directory Structure

Each directory contains working examples for specific API endpoints:

### 1. Simple Convert (`/simple-convert`)
Direct file upload and conversion (files up to 50MB).

- `convert.py` - Convert a local file with optional quality settings

```bash
# Basic conversion
python simple-convert/convert.py image.png jpg

# With options
python simple-convert/convert.py document.pdf docx --api-key=YOUR_KEY
```

### 2. URL Convert (`/url-convert`)
Convert files directly from URLs without downloading them first.

- `convert-from-url.py` - Convert a file from any public URL

```bash
python url-convert/convert-from-url.py https://example.com/file.pdf docx
```

### 3. Chunked Upload (`/chunked-upload`)
Upload and convert large files (up to 2GB) in chunks.

- `upload-large-file.py` - Upload large files in configurable chunks

```bash
# Default 5MB chunks
python chunked-upload/upload-large-file.py video.mov mp4

# Custom chunk size
python chunked-upload/upload-large-file.py large.pdf docx --chunk-size=10
```

### 4. Job Management (`/job-management`)
Track and manage conversion jobs with dedicated scripts for each operation.

- `check-status.py` - Check job status and optionally watch progress
- `cancel-job.py` - Cancel a running or queued job
- `delete-file.py` - Delete converted file from storage
- `download-result.py` - Download the converted file

```bash
# Check job status
python job-management/check-status.py job_123e4567-e89b-12d3

# Watch progress until complete
python job-management/check-status.py job_123e4567-e89b-12d3 --watch

# Cancel a running job
python job-management/cancel-job.py job_123e4567-e89b-12d3

# Delete a completed file (with confirmation)
python job-management/delete-file.py job_123e4567-e89b-12d3

# Force delete without confirmation
python job-management/delete-file.py job_123e4567-e89b-12d3 --force

# Download conversion result
python job-management/download-result.py job_123e4567-e89b-12d3

# Download with custom filename
python job-management/download-result.py job_123e4567-e89b-12d3 --output=myfile.pdf
```

### 5. Format Discovery (`/format-discovery`)
Explore supported formats and conversions.

- `list-formats.py` - List formats, check conversions, explore possibilities

```bash
# List all supported formats
python format-discovery/list-formats.py

# Show all conversions from PDF
python format-discovery/list-formats.py --from=pdf

# Check if specific conversion is supported
python format-discovery/list-formats.py --check=pdf:docx
```

### 6. Webhook Handler (`/webhook-handler`)
Receive real-time conversion notifications.

- `webhook-receiver.py` - Production-ready webhook endpoint

Start the webhook server:
```bash
python webhook-handler/webhook-receiver.py
```

Then use the webhook URL in your conversions:
```python
# When submitting conversions:
data = {
    'file': file,
    'target_format': 'pdf',
    'webhook_url': 'https://your-server.com/webhook'
}
```

## 🔑 Authentication

All API requests require a Bearer token. Get your API key at [https://converthub.com/api](https://converthub.com/api).

### Method 1: Environment File (Recommended)
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your key
CONVERTHUB_API_KEY="your_api_key_here"
```

### Method 2: Command Line Parameter
```bash
python simple-convert/convert.py file.pdf docx --api-key=your_key_here
```

### Method 3: Direct in Code
```python
API_KEY = 'your_api_key_here'
headers = {'Authorization': f'Bearer {API_KEY}'}
```

## 📊 Supported Conversions

The API supports 800+ format conversions, some popular ones include:

| Category | Formats |
|----------|---------|
| **Images** | JPG, PNG, WEBP, GIF, BMP, TIFF, SVG, HEIC, ICO, TGA |
| **Documents** | PDF, DOCX, DOC, TXT, RTF, ODT, HTML, MARKDOWN, TEX |
| **Spreadsheets** | XLSX, XLS, CSV, ODS, TSV |
| **Presentations** | PPTX, PPT, ODP, KEY |
| **Videos** | MP4, WEBM, AVI, MOV, MKV, WMV, FLV, MPG |
| **Audio** | MP3, WAV, OGG, M4A, FLAC, AAC, WMA, OPUS |
| **eBooks** | EPUB, MOBI, AZW3, FB2, LIT |
| **Archives** | ZIP, RAR, 7Z, TAR, GZ, BZ2 |

## ⚙️ Conversion Options

Customize your conversions with various options:

```bash
# In simple-convert/convert.py:
python convert.py image.png jpg --quality=85 --resolution=1920x1080

# Available options:
--quality=N        # Image quality (1-100)
--resolution=WxH   # Output resolution
--bitrate=RATE     # Audio/video bitrate (e.g., "320k")
--sample-rate=N    # Audio sample rate (e.g., 44100)
--output=FILENAME  # Custom output filename
```

## 🚦 Error Handling

All examples include comprehensive error handling:

```python
# Every script handles API errors properly:
if response.status_code >= 400:
    error_data = response.json()
    error = error_data.get('error', {})
    print(f"Error: {error.get('message', 'Unknown error')}")
    print(f"Code: {error.get('code')}")
```

Common error codes:
- `AUTHENTICATION_REQUIRED` - Missing or invalid API key
- `NO_MEMBERSHIP` - No active membership found
- `INSUFFICIENT_CREDITS` - No credits remaining
- `FILE_TOO_LARGE` - File exceeds size limit
- `UNSUPPORTED_FORMAT` - Format not supported
- `CONVERSION_FAILED` - Processing error

## 📈 Rate Limits

| Endpoint | Limit | Script |
|----------|-------|--------|
| Convert | 60/minute | `simple-convert/convert.py` |
| Convert URL | 60/minute | `url-convert/convert-from-url.py` |
| Status Check | 100/minute | `job-management/check-status.py` |
| Format Discovery | 200/minute | `format-discovery/list-formats.py` |
| Chunked Upload | 500/minute | `chunked-upload/upload-large-file.py` |

## 🔧 Requirements

- Python 3.7 or higher
- Dependencies in `requirements.txt`:
  - `requests` - HTTP client library
  - `python-dotenv` - Environment variable management
  - `colorama` - Cross-platform colored terminal output
  - `tqdm` - Progress bars for uploads/downloads
  - `Flask` - Web framework for webhook receiver

## 📚 File Descriptions

| File | Purpose |
|------|---------|
| `.env.example` | Environment configuration template |
| `requirements.txt` | Python package dependencies |
| **Simple Convert** | |
| `simple-convert/convert.py` | Convert local files up to 50MB |
| **URL Convert** | |
| `url-convert/convert-from-url.py` | Convert files from URLs |
| **Chunked Upload** | |
| `chunked-upload/upload-large-file.py` | Upload files up to 2GB in chunks |
| **Job Management** | |
| `job-management/check-status.py` | Check job status and watch progress |
| `job-management/cancel-job.py` | Cancel running or queued jobs |
| `job-management/delete-file.py` | Delete converted files from storage |
| `job-management/download-result.py` | Download conversion results |
| **Format Discovery** | |
| `format-discovery/list-formats.py` | Explore supported formats |
| **Webhook Handler** | |
| `webhook-handler/webhook-receiver.py` | Handle webhook notifications |

## 💡 Usage Examples

### Convert a PDF to Word
```bash
python simple-convert/convert.py document.pdf docx
```

### Convert an image from URL
```bash
python url-convert/convert-from-url.py https://example.com/photo.png jpg
```

### Upload a large video
```bash
python chunked-upload/upload-large-file.py movie.mov mp4 --chunk-size=10
```

### Monitor conversion progress
```bash
python job-management/check-status.py job_abc123 --watch
```

### Check if conversion is supported
```bash
python format-discovery/list-formats.py --check=heic:jpg
```

## 🐍 Python Code Examples

### Simple conversion
```python
import requests

API_KEY = 'your_api_key'
headers = {'Authorization': f'Bearer {API_KEY}'}

with open('document.pdf', 'rb') as f:
    files = {'file': ('document.pdf', f, 'application/pdf')}
    data = {'target_format': 'docx'}
    
    response = requests.post(
        'https://api.converthub.com/v2/convert',
        headers=headers,
        files=files,
        data=data
    )
    
    job = response.json()
    print(f"Job ID: {job['job_id']}")
```

### URL conversion
```python
import requests

API_KEY = 'your_api_key'
headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

data = {
    'url': 'https://example.com/file.pdf',
    'target_format': 'docx'
}

response = requests.post(
    'https://api.converthub.com/v2/convert/url',
    headers=headers,
    json=data
)

job = response.json()
print(f"Job ID: {job['job_id']}")
```

## 🚀 Production Deployment

For production webhook deployment:

### Using Gunicorn
```bash
# Install gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:8080 webhook-receiver:app
```

### Using systemd
```ini
# /etc/systemd/system/converthub-webhook.service
[Unit]
Description=ConvertHub Webhook Receiver
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/webhook-handler
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:8080 webhook-receiver:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### Using Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY webhook-handler/ .

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "webhook-receiver:app"]
```

## 🤝 Support

- **API Documentation**: [https://converthub.com/api/docs](https://converthub.com/api/docs)
- **Developer Dashboard**: [https://converthub.com/developers](https://converthub.com/developers)
- **Get API Key**: [https://converthub.com/api](https://converthub.com/api)
- **Email Support**: support@converthub.com

## 📄 License

These examples are provided under the MIT License. Feel free to use and modify them for your projects.

## 🙏 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

Built with ❤️ by [ConvertHub](https://converthub.com) - Making file conversion simple and powerful.