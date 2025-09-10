#!/usr/bin/env python3

import os
import sys
import time
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
import math

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


def upload_large_file(input_file, target_format, options=None):
    """Upload and convert large files in chunks."""
    
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
    filename = input_path.name
    
    # Check file size limit (2GB)
    if file_size > 2147483648:
        print(f"Error: File size ({file_size_mb:.2f} MB) exceeds 2GB limit.")
        sys.exit(1)
    
    # Determine chunk size (default 5MB)
    chunk_size_mb = 5
    if options and 'chunk_size' in options:
        try:
            chunk_size_mb = int(options['chunk_size'])
        except ValueError:
            print(f"Warning: Invalid chunk size, using default 5MB")
    
    chunk_size = chunk_size_mb * 1048576
    total_chunks = math.ceil(file_size / chunk_size)
    
    print("Chunked Upload - ConvertHub API")
    print("=" * 32)
    print(f"File: {filename} ({format_file_size(file_size)})")
    print(f"Target format: {target_format}")
    print(f"Chunk size: {chunk_size_mb} MB")
    print(f"Total chunks: {total_chunks}")
    print("-" * 50 + "\n")
    
    try:
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Step 1: Initialize chunked upload session
        print("→ Initializing upload session...")
        
        init_data = {
            'filename': filename,
            'file_size': file_size,
            'total_chunks': total_chunks,
            'target_format': target_format
        }
        
        # Add optional webhook
        if options and 'webhook' in options:
            init_data['webhook_url'] = options['webhook']
        
        # Add metadata
        init_data['metadata'] = {
            'original_size': file_size,
            'chunk_size': chunk_size,
            'upload_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
        
        response = requests.post(
            f'{API_BASE_URL}/upload/init',
            headers=headers,
            json=init_data
        )
        
        if response.status_code >= 400:
            error_data = response.json()
            error = error_data.get('error', {})
            print(f"✗ Error: {error.get('message', 'Failed to initialize upload')}")
            if error.get('code'):
                print(f"  Code: {error['code']}")
            sys.exit(1)
        
        session = response.json()
        session_id = session['session_id']
        expires_at = session.get('expires_at', 'N/A')
        
        print(f"✓ Session created: {session_id}")
        print(f"  Expires at: {expires_at}\n")
        
        # Step 2: Upload chunks
        print("→ Uploading chunks...\n")
        
        start_time = time.time()
        
        with open(input_path, 'rb') as file:
            # Create progress bar
            with tqdm(total=total_chunks, desc="Uploading", unit="chunk", 
                     bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]') as pbar:
                
                for chunk_index in range(total_chunks):
                    # Read chunk data
                    chunk_data = file.read(chunk_size)
                    
                    # Upload chunk
                    files = {
                        'chunk': ('chunk', chunk_data, 'application/octet-stream')
                    }
                    
                    chunk_headers = {
                        'Authorization': f'Bearer {API_KEY}'
                    }
                    
                    chunk_response = requests.post(
                        f'{API_BASE_URL}/upload/{session_id}/chunks/{chunk_index}',
                        headers=chunk_headers,
                        files=files
                    )
                    
                    if chunk_response.status_code >= 400:
                        print(f"\n✗ Failed to upload chunk {chunk_index + 1}")
                        error_data = chunk_response.json()
                        error = error_data.get('error', {})
                        print(f"Error: {error.get('message', 'Unknown error')}")
                        sys.exit(1)
                    
                    # Update progress
                    pbar.update(1)
                    
                    # Calculate and display upload speed
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        speed = ((chunk_index + 1) * chunk_size) / elapsed / 1048576  # MB/s
                        pbar.set_postfix({'speed': f'{speed:.1f} MB/s'})
        
        upload_time = round(time.time() - start_time)
        print(f"\n✓ All chunks uploaded successfully in {format_time(upload_time)}\n")
        
        # Step 3: Complete upload and start conversion
        print("→ Finalizing upload and starting conversion...")
        
        complete_response = requests.post(
            f'{API_BASE_URL}/upload/{session_id}/complete',
            headers=headers,
            json={}
        )
        
        if complete_response.status_code >= 400:
            error_data = complete_response.json()
            error = error_data.get('error', {})
            print(f"✗ Error: {error.get('message', 'Failed to complete upload')}")
            sys.exit(1)
        
        job = complete_response.json()
        job_id = job['job_id']
        
        print("✓ Upload complete! Conversion started.")
        print(f"  Job ID: {job_id}\n")
        
        # Step 4: Monitor conversion progress
        sys.stdout.write("→ Converting")
        sys.stdout.flush()
        
        attempts = 0
        max_attempts = 180  # 6 minutes for large files
        status = 'processing'
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
            status = job_status['status']
        
        print("\n")
        
        # Step 5: Display results
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
            total_time = round(time.time() - start_time)
            print(f"  Total time: {format_time(total_time)}")
            print(f"  Expires: {result['expires_at']}")
            
            # Offer to download
            answer = input("\nDownload converted file? (y/n): ")
            if answer.lower() == 'y':
                download_large_file(result['download_url'], target_format)
        
        elif status == 'failed':
            print("✗ Conversion failed")
            if job_status.get('error'):
                print(f"Error: {job_status['error'].get('message', 'Unknown error')}")
            sys.exit(1)
        
        else:
            print("✗ Timeout: Conversion is taking longer than expected")
            print("Large files may take more time to process.")
            print(f"Check status later with: python job-management/check-status.py {job_id}")
            
            if options and 'webhook' in options:
                print("You will receive a webhook notification when complete.")
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n✗ Upload cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)


def download_large_file(url, format_ext):
    """Download the converted file with progress bar."""
    output_file = f"converted_{int(time.time())}.{format_ext}"
    print(f"Downloading to: {output_file}\n")
    
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_file, 'wb') as file:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        pbar.update(len(chunk))
        
        print(f"\n✓ File saved: {output_file} ({format_file_size(Path(output_file).stat().st_size)})")
        
    except Exception as e:
        print(f"\n✗ Download failed: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Upload and convert large files (up to 2GB) in chunks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python upload-large-file.py video.mov mp4
  python upload-large-file.py large.pdf docx --chunk-size=10
  python upload-large-file.py big-file.zip 7z --webhook=https://your-server.com/webhook
  
Get your API key at: https://converthub.com/api
        '''
    )
    
    parser.add_argument('input_file', help='Path to the input file')
    parser.add_argument('target_format', help='Target format for conversion')
    parser.add_argument('--chunk-size', dest='chunk_size', help='Chunk size in MB (default: 5)')
    parser.add_argument('--api-key', dest='api_key', help='Your API key')
    parser.add_argument('--webhook', help='Webhook URL for notifications')
    
    args = parser.parse_args()
    
    # Override API key if provided
    if args.api_key:
        global API_KEY
        API_KEY = args.api_key
    
    # Collect options
    options = {}
    if args.chunk_size:
        options['chunk_size'] = args.chunk_size
    if args.webhook:
        options['webhook'] = args.webhook
    
    upload_large_file(args.input_file, args.target_format.lower(), options)


if __name__ == '__main__':
    main()