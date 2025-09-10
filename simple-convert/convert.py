#!/usr/bin/env python3

import os
import sys
import time
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

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


def convert_file(input_file, target_format, options=None):
    """Convert a file to the specified format."""
    
    # Check if API key is set
    if not API_KEY:
        print("Error: CONVERTHUB_API_KEY is not set")
        print("Get your API key at: https://converthub.com/api")
        print("\nSet it in .env file or use --api-key parameter")
        sys.exit(1)
    
    # Validate input file
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)
    
    file_size = input_path.stat().st_size
    file_size_mb = file_size / 1048576
    
    # Check file size limit
    if file_size_mb > 50:
        print(f"Error: File size ({file_size_mb:.2f} MB) exceeds 50MB limit.")
        print("Use chunked-upload/upload-large-file.py for larger files.")
        sys.exit(1)
    
    print("Simple Convert - ConvertHub API")
    print("=" * 32)
    print(f"File: {input_path.name} ({format_file_size(file_size)})")
    print(f"Target format: {target_format}")
    
    if options:
        print("\nOptions:")
        for key, value in options.items():
            if key not in ['api_key', 'output']:
                print(f"  {key}: {value}")
    
    print("-" * 50 + "\n")
    
    try:
        # Step 1: Upload file and convert
        print("→ Uploading and converting file...")
        
        headers = {
            'Authorization': f'Bearer {API_KEY}'
        }
        
        # Prepare form data
        with open(input_path, 'rb') as f:
            files = {
                'file': (input_path.name, f, 'application/octet-stream')
            }
            
            data = {
                'target_format': target_format
            }
            
            # Add conversion options
            if options:
                conversion_options = {}
                for key, value in options.items():
                    if key not in ['api_key', 'output']:
                        conversion_options[key] = value
                if conversion_options:
                    import json
                    data['options'] = json.dumps(conversion_options)
            
            response = requests.post(
                f'{API_BASE_URL}/convert',
                headers=headers,
                files=files,
                data=data
            )
        
        if response.status_code >= 400:
            error_data = response.json()
            error = error_data.get('error', {})
            print(f"✗ Error: {error.get('message', 'Unknown error')}")
            if error.get('code'):
                print(f"  Code: {error['code']}")
            if error.get('details'):
                for key, value in error['details'].items():
                    print(f"  {key}: {value}")
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
            sys.stdout.write("→ Converting")
            sys.stdout.flush()
            
            attempts = 0
            max_attempts = 60  # 2 minutes for simple conversions
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
            
            # Download file if output specified
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
            print(f"Check status with: python job-management/check-status.py {job_id}")
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
        description='Convert files using ConvertHub API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python convert.py document.pdf docx
  python convert.py image.png jpg --quality=85
  python convert.py video.mp4 webm --bitrate=1000k
  
Get your API key at: https://converthub.com/api
        '''
    )
    
    parser.add_argument('input_file', help='Path to the input file')
    parser.add_argument('target_format', help='Target format for conversion')
    parser.add_argument('--api-key', dest='api_key', help='Your API key')
    parser.add_argument('--quality', type=int, help='Output quality (1-100)')
    parser.add_argument('--resolution', help='Output resolution (e.g., 1920x1080)')
    parser.add_argument('--bitrate', help='Audio/video bitrate (e.g., 320k)')
    parser.add_argument('--sample-rate', dest='sample_rate', type=int, help='Audio sample rate')
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
    if args.output:
        options['output'] = args.output
    
    convert_file(args.input_file, args.target_format.lower(), options)


if __name__ == '__main__':
    main()