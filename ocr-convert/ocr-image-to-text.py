#!/usr/bin/env python3
"""
ConvertHub API - OCR Image to Text Conversion

Extract text from images (PNG, JPG, TIFF, etc.) using OCR.
Supports multiple languages and outputs plain text.

Usage:
    python ocr-image-to-text.py <input_image> [--language eng] [--api-key KEY]

Examples:
    python ocr-image-to-text.py screenshot.png
    python ocr-image-to-text.py document.jpg --language deu
    python ocr-image-to-text.py scan.tiff --language eng+fra

Supported input formats: png, jpg, jpeg, tiff, tif, bmp, gif, webp
Supported languages: eng, deu, fra, spa, ita, por, nld, rus, chi_sim, chi_tra, jpn, kor, ara, hin

Get your API key at: https://converthub.com/api
"""

import argparse
import os
import sys
import time

import requests

# Load .env from parent directory
env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

API_BASE_URL = os.environ.get('CONVERTHUB_API_BASE_URL', 'https://api.converthub.com/v2')
SUPPORTED_FORMATS = ['png', 'jpg', 'jpeg', 'tiff', 'tif', 'bmp', 'gif', 'webp']


def format_file_size(size_bytes):
    """Format bytes to human-readable size."""
    return f"{size_bytes / 1048576:.2f} MB"


def download_and_display(download_url, input_file):
    """Download the converted text file and display its contents."""
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = os.path.join(os.path.dirname(input_file) or '.', base_name + '.txt')

    response = requests.get(download_url, stream=True)
    response.raise_for_status()

    with open(output_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Saved to: {output_file}\n")

    # Display extracted text
    with open(output_file, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()

    if text.strip():
        print("--- Extracted Text ---")
        print(text)
        print("--- End ---")
    else:
        print("(No text was extracted - the image may not contain readable text)")


def main():
    parser = argparse.ArgumentParser(
        description='OCR Image to Text - ConvertHub API',
        epilog='Supported formats: ' + ', '.join(SUPPORTED_FORMATS)
    )
    parser.add_argument('input_file', help='Path to the input image file')
    parser.add_argument('--language', default='eng',
                        help='OCR language code (default: eng). Use + for multiple: eng+fra')
    parser.add_argument('--api-key', default=None, help='ConvertHub API key')
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get('CONVERTHUB_API_KEY')
    if not api_key:
        print("Error: API key required. Set CONVERTHUB_API_KEY in .env or use --api-key parameter.")
        print("Get your API key at: https://converthub.com/api")
        sys.exit(1)

    input_file = args.input_file
    language = args.language

    # Validate input file
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)

    extension = os.path.splitext(input_file)[1].lower().lstrip('.')
    if extension not in SUPPORTED_FORMATS:
        print(f"Error: Unsupported format '{extension}'. Supported: {', '.join(SUPPORTED_FORMATS)}")
        sys.exit(1)

    file_size = os.path.getsize(input_file)
    if file_size > 52428800:  # 50MB
        print(f"Error: File size ({format_file_size(file_size)}) exceeds 50MB limit.")
        sys.exit(1)

    headers = {'Authorization': f'Bearer {api_key}'}

    print(f"OCR: {os.path.basename(input_file)} ({format_file_size(file_size)}) -> txt (language: {language})")
    print("=" * 50 + "\n")

    # Step 1: Submit file for OCR conversion
    print("-> Uploading file...")

    with open(input_file, 'rb') as f:
        files = {'file': (os.path.basename(input_file), f)}
        data = {
            'target_format': 'txt',
            'options[ocr]': 'true',
            'options[ocr_language]': language,
        }

        try:
            response = requests.post(f'{API_BASE_URL}/convert', headers=headers, files=files, data=data)
        except requests.ConnectionError:
            print("[ERROR] Failed to connect to API")
            sys.exit(1)

    # Handle errors
    if response.status_code >= 400:
        result = response.json()
        error = result.get('error', {})
        print(f"[ERROR] {error.get('message', 'Unknown error')}")
        details = error.get('details', {})
        for key, value in details.items():
            print(f"  {key}: {value}")
        sys.exit(1)

    result = response.json()

    # Check for cached result
    if response.status_code == 200 and result.get('result', {}).get('download_url'):
        print("[OK] OCR complete (cached result)\n")
        download_and_display(result['result']['download_url'], input_file)
        return

    job_id = result['job_id']
    print(f"[OK] Job created: {job_id}\n")

    # Step 2: Poll for job completion
    sys.stdout.write("-> Processing OCR")
    sys.stdout.flush()

    status = 'processing'
    job_status = None
    max_attempts = 150  # 5 minutes (2s intervals)

    for _ in range(max_attempts):
        if status not in ('processing', 'queued'):
            break

        time.sleep(2)
        sys.stdout.write(".")
        sys.stdout.flush()

        try:
            resp = requests.get(f'{API_BASE_URL}/jobs/{job_id}', headers=headers)
            job_status = resp.json()
            status = job_status.get('status', 'unknown')
        except Exception:
            continue

    print("\n")

    # Step 3: Handle result
    if status == 'completed':
        print("[OK] OCR complete!")
        print("=" * 50)
        print(f"Processing time: {job_status.get('processing_time', 'N/A')}")
        print(f"Download URL: {job_status['result']['download_url']}")
        print(f"Expires: {job_status['result']['expires_at']}\n")

        download_and_display(job_status['result']['download_url'], input_file)
    elif status == 'failed':
        print("[ERROR] OCR failed")
        error = job_status.get('error', {}) if job_status else {}
        print(f"Error: {error.get('message', 'Unknown error')}")
        sys.exit(1)
    else:
        print("[ERROR] Timeout: OCR is taking longer than expected")
        print(f"Check status with: python ../job-management/check-status.py {job_id}")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(1)
