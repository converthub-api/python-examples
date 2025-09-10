#!/usr/bin/env python3

import os
import sys
import time
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


def check_status(job_id, watch=False):
    """Check the status of a conversion job."""
    
    # Check if API key is set
    if not API_KEY:
        print("Error: CONVERTHUB_API_KEY is not set")
        print("Get your API key at: https://converthub.com/api")
        print("\nSet it in .env file or use --api-key parameter")
        sys.exit(1)
    
    print("Job Status - ConvertHub API")
    print("=" * 28)
    print(f"Job ID: {job_id}")
    print("-" * 50 + "\n")
    
    try:
        headers = {
            'Authorization': f'Bearer {API_KEY}'
        }
        
        if watch:
            print("→ Watching job progress...\n")
            
            attempts = 0
            max_attempts = 300  # 10 minutes max
            previous_status = None
            
            while attempts < max_attempts:
                response = requests.get(
                    f'{API_BASE_URL}/jobs/{job_id}',
                    headers=headers
                )
                
                if response.status_code >= 400:
                    error_data = response.json()
                    error = error_data.get('error', {})
                    print(f"✗ Error: {error.get('message', 'Failed to get job status')}")
                    if error.get('code'):
                        print(f"  Code: {error['code']}")
                    sys.exit(1)
                
                job = response.json()
                status = job['status']
                
                # Print status change
                if status != previous_status:
                    timestamp = time.strftime('%H:%M:%S')
                    
                    if status == 'queued':
                        print(f"[{timestamp}] {Fore.YELLOW}⏳ Job queued{Style.RESET_ALL}")
                    elif status == 'processing':
                        print(f"[{timestamp}] {Fore.CYAN}⚙️  Processing...{Style.RESET_ALL}")
                    elif status == 'completed':
                        print(f"[{timestamp}] {Fore.GREEN}✓ Conversion complete!{Style.RESET_ALL}\n")
                        display_job_details(job)
                        break
                    elif status == 'failed':
                        print(f"[{timestamp}] {Fore.RED}✗ Conversion failed{Style.RESET_ALL}\n")
                        if job.get('error'):
                            print(f"Error: {job['error'].get('message', 'Unknown error')}")
                            if job['error'].get('code'):
                                print(f"Code: {job['error']['code']}")
                        sys.exit(1)
                    elif status == 'cancelled':
                        print(f"[{timestamp}] {Fore.YELLOW}⚠️  Job cancelled{Style.RESET_ALL}")
                        sys.exit(0)
                    
                    previous_status = status
                
                # If completed, exit
                if status in ['completed', 'failed', 'cancelled']:
                    break
                
                time.sleep(2)
                attempts += 1
            
            if attempts >= max_attempts:
                print(f"\n{Fore.YELLOW}⚠️  Timeout: Job is taking longer than expected{Style.RESET_ALL}")
                print("The job may still be processing. Check again later.")
        
        else:
            # Single status check
            print("→ Checking job status...")
            
            response = requests.get(
                f'{API_BASE_URL}/jobs/{job_id}',
                headers=headers
            )
            
            if response.status_code >= 400:
                error_data = response.json()
                error = error_data.get('error', {})
                print(f"\n✗ Error: {error.get('message', 'Failed to get job status')}")
                if error.get('code'):
                    print(f"  Code: {error['code']}")
                sys.exit(1)
            
            job = response.json()
            status = job['status']
            
            print()
            
            # Display status with appropriate color
            if status == 'queued':
                print(f"Status: {Fore.YELLOW}Queued{Style.RESET_ALL}")
                print("\nThe job is waiting to be processed.")
            elif status == 'processing':
                print(f"Status: {Fore.CYAN}Processing{Style.RESET_ALL}")
                print("\nThe conversion is currently being processed.")
            elif status == 'completed':
                print(f"Status: {Fore.GREEN}Completed{Style.RESET_ALL}\n")
                display_job_details(job)
            elif status == 'failed':
                print(f"Status: {Fore.RED}Failed{Style.RESET_ALL}")
                if job.get('error'):
                    print(f"\nError: {job['error'].get('message', 'Unknown error')}")
                    if job['error'].get('code'):
                        print(f"Code: {job['error']['code']}")
            elif status == 'cancelled':
                print(f"Status: {Fore.YELLOW}Cancelled{Style.RESET_ALL}")
                print("\nThe job was cancelled.")
            
            # Show metadata if available
            if job.get('created_at'):
                print(f"\nCreated: {job['created_at']}")
            if job.get('updated_at'):
                print(f"Updated: {job['updated_at']}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n✗ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)


def display_job_details(job):
    """Display detailed job information."""
    if job.get('result'):
        result = job['result']
        
        print("-" * 50)
        print("Conversion Details:")
        print(f"  Source format: {job.get('source_format', 'N/A')}")
        print(f"  Target format: {result.get('format', 'N/A')}")
        print(f"  File size: {format_file_size(result.get('file_size', 0))}")
        
        if job.get('processing_time'):
            print(f"  Processing time: {job['processing_time']}")
        
        print(f"\nDownload URL:")
        print(f"  {result.get('download_url', 'N/A')}")
        
        if result.get('expires_at'):
            print(f"\nExpires: {result['expires_at']}")
        
        print("\n" + "-" * 50)
        print("Actions:")
        print(f"  Download: python job-management/download-result.py {job['job_id']}")
        print(f"  Delete: python job-management/delete-file.py {job['job_id']}")


def main():
    parser = argparse.ArgumentParser(
        description='Check the status of a conversion job',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python check-status.py job_123e4567-e89b-12d3
  python check-status.py job_123e4567-e89b-12d3 --watch
  
Get your API key at: https://converthub.com/api
        '''
    )
    
    parser.add_argument('job_id', help='The job ID to check')
    parser.add_argument('--watch', action='store_true', help='Watch the job until completion')
    parser.add_argument('--api-key', dest='api_key', help='Your API key')
    
    args = parser.parse_args()
    
    # Override API key if provided
    if args.api_key:
        global API_KEY
        API_KEY = args.api_key
    
    check_status(args.job_id, args.watch)


if __name__ == '__main__':
    main()