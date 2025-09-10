#!/usr/bin/env python3

import os
import sys
import time
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

API_BASE_URL = os.getenv('CONVERTHUB_API_BASE_URL', 'https://api.converthub.com/v2')
API_KEY = os.getenv('CONVERTHUB_API_KEY')


def format_file_size(bytes_size):
    """Format bytes to human readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def format_time(seconds):
    """Format seconds to human readable time."""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        return f"{seconds/60:.1f} minutes"
    else:
        return f"{seconds/3600:.1f} hours"


def convert_from_url(url, target_format, options=None):
    """Convert a file from URL to the specified format."""
    
    # Check if API key is set
    if not API_KEY:
        print("Error: CONVERTHUB_API_KEY is not set")
        print("Get your API key at: https://converthub.com/api")
        print("\nSet it in .env file or use --api-key parameter")
        sys.exit(1)
    
    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
        
        # Extract filename from URL
        filename = os.path.basename(parsed.path) or 'file'
        
    except Exception as e:
        print(f"Error: Invalid URL - {e}")
        sys.exit(1)
    
    print("URL Convert - ConvertHub API")
    print("=" * 29)
    print(f"URL: {url}")
    print(f"Filename: {filename}")
    print(f"Target format: {target_format}")
    
    if options:
        print("\nOptions:")
        for key, value in options.items():
            if key not in ['api_key', 'output', 'webhook']:
                print(f"  {key}: {value}")
    
    print("-" * 50 + "\n")
    
    try:
        # Step 1: Submit URL for conversion
        print("→ Submitting URL for conversion...")
        
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Prepare request data
        data = {
            'file_url': url,
            'target_format': target_format,
            'output_filename': filename
        }
        
        # Add webhook if provided
        webhook_url = options.get('webhook') if options else None
        if webhook_url:
            data['webhook_url'] = webhook_url
            print(f"  Webhook: {webhook_url}")
        
        # Add conversion options
        if options:
            conversion_options = {}
            for key, value in options.items():
                if key not in ['api_key', 'output', 'webhook']:
                    conversion_options[key] = value
            if conversion_options:
                data['options'] = conversion_options
        
        response = requests.post(
            f'{API_BASE_URL}/convert-url',
            headers=headers,
            json=data
        )
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error = error_data.get('error', {})
                print(f"✗ Error: {error.get('message', 'Unknown error')}")
                if error.get('code'):
                    print(f"  Code: {error['code']}")
                if error.get('details'):
                    for key, value in error['details'].items():
                        print(f"  {key}: {value}")
            except:
                print(f"✗ Error: HTTP {response.status_code}")
                print(f"  Response: {response.text}")
            sys.exit(1)
        
        job = response.json()
        job_id = job['job_id']
        status = job.get('status', 'processing')
        
        print(f"✓ Conversion job created: {job_id}")
        
        # Check if already completed (from cache)
        if status == 'completed' and job.get('result'):
            print("✓ Using cached result (instant conversion)\n")
            job_status = job
        else:
            # Step 2: Monitor progress
            print()
            sys.stdout.write("→ Downloading from URL and converting")
            sys.stdout.flush()
            
            attempts = 0
            max_attempts = 90  # 3 minutes for URL conversions
            job_status = None
            
            while status in ['processing', 'queued', 'pending'] and attempts < max_attempts:
                time.sleep(2)
                attempts += 1
                sys.stdout.write(".")
                sys.stdout.flush()
                
                response = requests.get(
                    f'{API_BASE_URL}/jobs/{job_id}',
                    headers=headers
                )
                
                if response.status_code >= 400:
                    print("\n✗ Failed to check status")
                    sys.exit(1)
                
                job_status = response.json()
                status = job_status.get('status', 'processing')
            
            print("\n")
        
        # Step 3: Handle results
        if status == 'completed' and job_status.get('result', {}).get('download_url'):
            print("✓ Conversion complete!\n")
            print("-" * 50)
            print("Results:")
            result = job_status['result']
            print(f"  Download URL: {result['download_url']}")
            print(f"  Format: {result['format']}")
            print(f"  Size: {format_file_size(result['file_size'])}")
            if job_status.get('processing_time'):
                print(f"  Processing time: {job_status['processing_time']}")
            print(f"  Expires: {result['expires_at']}")
            
            # Download file if output specified or ask user
            output_file = options.get('output') if options else None
            if not output_file:
                answer = input("\nDownload converted file? (y/n): ")
                if answer.lower() == 'y':
                    output_file = f"converted_{int(time.time())}.{target_format}"
            
            if output_file:
                print(f"\nDownloading to: {output_file}")
                download_response = requests.get(result['download_url'], stream=True)
                
                if download_response.status_code == 200:
                    total_size = int(download_response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(output_file, 'wb') as f:
                        for chunk in download_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    percent = (downloaded * 100) / total_size
                                    sys.stdout.write(f"\rDownloading: {percent:.1f}%")
                                    sys.stdout.flush()
                    
                    print(f"\n✓ File saved: {output_file}")
                else:
                    print("✗ Download failed")
        
        elif status == 'failed':
            print("✗ Conversion failed")
            if job_status.get('error'):
                print(f"Error: {job_status['error'].get('message', 'Unknown error')}")
            sys.exit(1)
        
        else:
            print("✗ Timeout: Conversion is taking longer than expected")
            print("URL downloads may take more time for large files.")
            print(f"Check status with: python job-management/check-status.py {job_id}")
            
            if webhook_url:
                print("You will receive a webhook notification when complete.")
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n✗ Conversion cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Convert files from URLs using ConvertHub API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python convert-from-url.py https://example.com/document.pdf docx
  python convert-from-url.py https://example.com/image.png jpg --quality=85
  python convert-from-url.py https://example.com/video.mp4 webm --webhook=https://your-server.com/webhook
  
Get your API key at: https://converthub.com/api
        '''
    )
    
    parser.add_argument('url', help='URL of the file to convert')
    parser.add_argument('target_format', help='Target format for conversion')
    parser.add_argument('--api-key', dest='api_key', help='Your API key')
    parser.add_argument('--quality', type=int, help='Output quality (1-100)')
    parser.add_argument('--resolution', help='Output resolution (e.g., 1920x1080)')
    parser.add_argument('--bitrate', help='Audio/video bitrate (e.g., 320k)')
    parser.add_argument('--sample-rate', dest='sample_rate', type=int, help='Audio sample rate')
    parser.add_argument('--webhook', help='Webhook URL for notifications')
    parser.add_argument('--output', help='Output filename')
    
    args = parser.parse_args()
    
    # Override API key if provided
    if args.api_key:
        global API_KEY
        API_KEY = args.api_key
    
    # Collect options
    options = {}
    if args.api_key:
        options['api_key'] = args.api_key
    if args.quality:
        options['quality'] = args.quality
    if args.resolution:
        options['resolution'] = args.resolution
    if args.bitrate:
        options['bitrate'] = args.bitrate
    if args.sample_rate:
        options['sample_rate'] = args.sample_rate
    if args.webhook:
        options['webhook'] = args.webhook
    if args.output:
        options['output'] = args.output
    
    convert_from_url(args.url, args.target_format.lower(), options)


if __name__ == '__main__':
    main()