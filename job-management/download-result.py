#!/usr/bin/env python3

import os
import sys
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
from colorama import init, Fore, Style

# Initialize colorama
init()

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


def download_result(job_id, output_file=None):
    """Download the converted file from a completed job."""
    
    # Check if API key is set
    if not API_KEY:
        print("Error: CONVERTHUB_API_KEY is not set")
        print("Get your API key at: https://converthub.com/api")
        print("\nSet it in .env file or use --api-key parameter")
        sys.exit(1)
    
    print("Download Result - ConvertHub API")
    print("=" * 32)
    print(f"Job ID: {job_id}")
    print("-" * 50 + "\n")
    
    try:
        headers = {
            'Authorization': f'Bearer {API_KEY}'
        }
        
        # First, get the job details
        print("→ Retrieving job information...")
        
        response = requests.get(
            f'{API_BASE_URL}/jobs/{job_id}',
            headers=headers
        )
        
        if response.status_code >= 400:
            error_data = response.json()
            error = error_data.get('error', {})
            print(f"\n✗ Error: {error.get('message', 'Job not found')}")
            if error.get('code'):
                print(f"  Code: {error['code']}")
            sys.exit(1)
        
        job_response = response.json()
        
        # Handle both dict and list responses
        if isinstance(job_response, list):
            # If response is a list, take the first item
            if len(job_response) > 0:
                job = job_response[0]
            else:
                print("\n✗ Error: Empty response from API")
                sys.exit(1)
        else:
            job = job_response
            
        status = job.get('status', 'unknown')
        
        # Check if file is available
        if status != 'completed':
            print(f"\n{Fore.YELLOW}⚠️  File not available{Style.RESET_ALL}")
            print(f"Job status: {status}")
            
            if status == 'processing':
                print("\nThe conversion is still in progress.")
                print(f"Check status: python job-management/check-status.py {job_id} --watch")
            elif status == 'queued':
                print("\nThe job is queued and hasn't started yet.")
                print(f"Check status: python job-management/check-status.py {job_id} --watch")
            elif status == 'failed':
                print("\nThe conversion failed.")
                if job.get('error'):
                    print(f"Error: {job['error'].get('message', 'Unknown error')}")
            elif status == 'cancelled':
                print("\nThe job was cancelled.")
            
            sys.exit(1)
        
        result = job.get('result', {})
        if not result.get('download_url'):
            print(f"\n{Fore.YELLOW}⚠️  No download URL available{Style.RESET_ALL}")
            print("The file may have been deleted or expired.")
            sys.exit(1)
        
        # Display file information
        print(f"\n{Fore.CYAN}File Information:{Style.RESET_ALL}")
        print(f"  Format: {result.get('format', 'N/A').upper()}")
        print(f"  Size: {format_file_size(result.get('file_size', 0))}")
        
        if job.get('source_format'):
            print(f"  Source: {job.get('source_format', 'N/A').upper()}")
        
        if job.get('processing_time'):
            print(f"  Processing time: {job.get('processing_time', 'N/A')}")
        
        if result.get('expires_at'):
            print(f"  Expires: {result['expires_at']}")
        
        # Determine output filename
        if not output_file:
            # Generate default filename
            format_ext = result.get('format', 'bin')
            
            # Try to get original filename from metadata
            original_name = 'converted'
            metadata = job.get('metadata', {})
            if isinstance(metadata, dict) and metadata.get('original_filename'):
                original_name = Path(metadata['original_filename']).stem
            
            output_file = f"{original_name}_{job_id[:8]}.{format_ext}"
        
        print(f"\nOutput file: {output_file}")
        
        # Download the file
        print("\n→ Downloading file...")
        
        download_url = result.get('download_url', '')
        if not download_url:
            print(f"\n✗ No download URL available")
            sys.exit(1)
        response = requests.get(download_url, stream=True)
        
        if response.status_code != 200:
            print(f"\n✗ Failed to download file")
            print(f"HTTP Status: {response.status_code}")
            sys.exit(1)
        
        # Get total file size
        total_size = int(response.headers.get('content-length', 0))
        
        # Download with progress bar
        with open(output_file, 'wb') as file:
            with tqdm(total=total_size, unit='B', unit_scale=True, 
                     desc="Progress", bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]') as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        pbar.update(len(chunk))
        
        # Verify download
        actual_size = Path(output_file).stat().st_size
        print(f"\n{Fore.GREEN}✓ Download complete!{Style.RESET_ALL}")
        print(f"  File: {output_file}")
        print(f"  Size: {format_file_size(actual_size)}")
        
        if actual_size != total_size and total_size > 0:
            print(f"\n{Fore.YELLOW}⚠️  Warning: File size mismatch{Style.RESET_ALL}")
            print(f"  Expected: {format_file_size(total_size)}")
            print(f"  Downloaded: {format_file_size(actual_size)}")
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n✗ Download cancelled by user")
        # Clean up partial file
        if output_file and Path(output_file).exists():
            Path(output_file).unlink()
            print(f"Partial file deleted: {output_file}")
        sys.exit(1)
    except IOError as e:
        print(f"\n✗ File write error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Download the converted file from a completed job',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python download-result.py job_123e4567-e89b-12d3
  python download-result.py job_123e4567-e89b-12d3 --output=myfile.pdf
  
Get your API key at: https://converthub.com/api
        '''
    )
    
    parser.add_argument('job_id', help='The job ID to download')
    parser.add_argument('--output', help='Output filename (default: auto-generated)')
    parser.add_argument('--api-key', dest='api_key', help='Your API key')
    
    args = parser.parse_args()
    
    # Override API key if provided
    if args.api_key:
        global API_KEY
        API_KEY = args.api_key
    
    download_result(args.job_id, args.output)


if __name__ == '__main__':
    main()