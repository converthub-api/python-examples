#!/usr/bin/env python3

import os
import sys
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv
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


def delete_file(job_id, force=False):
    """Delete a converted file from storage."""
    
    # Check if API key is set
    if not API_KEY:
        print("Error: CONVERTHUB_API_KEY is not set")
        print("Get your API key at: https://converthub.com/api")
        print("\nSet it in .env file or use --api-key parameter")
        sys.exit(1)
    
    print("Delete File - ConvertHub API")
    print("=" * 29)
    print(f"Job ID: {job_id}")
    print("-" * 50 + "\n")
    
    try:
        headers = {
            'Authorization': f'Bearer {API_KEY}'
        }
        
        # First, check the job status and get file info
        print("→ Retrieving file information...")
        
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
        
        job = response.json()
        status = job['status']
        
        # Check if file exists
        if status != 'completed':
            print(f"\n{Fore.YELLOW}⚠️  No file to delete{Style.RESET_ALL}")
            print(f"Job status: {status}")
            
            if status == 'processing':
                print("The conversion is still in progress.")
            elif status == 'queued':
                print("The job is queued and hasn't started yet.")
            elif status == 'failed':
                print("The conversion failed - no file was created.")
            elif status == 'cancelled':
                print("The job was cancelled - no file was created.")
            
            sys.exit(0)
        
        result = job.get('result', {})
        if not result.get('download_url'):
            print(f"\n{Fore.YELLOW}⚠️  No file available{Style.RESET_ALL}")
            print("The conversion completed but no file is available.")
            sys.exit(0)
        
        # Display file information
        print(f"\n{Fore.CYAN}File Information:{Style.RESET_ALL}")
        print(f"  Format: {result.get('format', 'N/A').upper()}")
        print(f"  Size: {format_file_size(result.get('file_size', 0))}")
        
        if job.get('source_format'):
            print(f"  Source: {job['source_format'].upper()}")
        
        if result.get('expires_at'):
            print(f"  Expires: {result['expires_at']}")
        
        print(f"\nDownload URL:")
        print(f"  {result['download_url']}")
        
        # Confirm deletion
        if not force:
            print(f"\n{Fore.RED}⚠️  Warning: This action cannot be undone!{Style.RESET_ALL}")
            print("Once deleted, the file cannot be recovered.")
            answer = input("\nAre you sure you want to delete this file? (y/n): ")
            if answer.lower() != 'y':
                print("\n✗ Deletion cancelled")
                sys.exit(0)
        
        # Delete the file
        print("\n→ Deleting file...")
        
        response = requests.delete(
            f'{API_BASE_URL}/jobs/{job_id}/destroy',
            headers=headers
        )
        
        if response.status_code == 200 or response.status_code == 204:
            print(f"\n{Fore.GREEN}✓ File deleted successfully{Style.RESET_ALL}")
            
            # Show summary
            result = response.json() if response.text else {}
            if result.get('message'):
                print(f"  {result['message']}")
            
            print("\nThe converted file has been permanently deleted from storage.")
            print("The job record remains for reference but the file is no longer available.")
            
        elif response.status_code == 404:
            print(f"\n{Fore.YELLOW}⚠️  File not found{Style.RESET_ALL}")
            print("The file may have already been deleted or expired.")
            
        elif response.status_code >= 400:
            error_data = response.json()
            error = error_data.get('error', {})
            print(f"\n✗ Failed to delete file")
            print(f"Error: {error.get('message', 'Unknown error')}")
            if error.get('code'):
                print(f"Code: {error['code']}")
            sys.exit(1)
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n✗ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Delete a converted file from storage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python delete-file.py job_123e4567-e89b-12d3
  python delete-file.py job_123e4567-e89b-12d3 --force
  
Note: This permanently deletes the converted file from storage.
      The job record remains but the file cannot be recovered.
  
Get your API key at: https://converthub.com/api
        '''
    )
    
    parser.add_argument('job_id', help='The job ID of the file to delete')
    parser.add_argument('--force', action='store_true', help='Delete without confirmation')
    parser.add_argument('--api-key', dest='api_key', help='Your API key')
    
    args = parser.parse_args()
    
    # Override API key if provided
    if args.api_key:
        global API_KEY
        API_KEY = args.api_key
    
    delete_file(args.job_id, args.force)


if __name__ == '__main__':
    main()