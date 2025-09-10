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


def cancel_job(job_id, force=False):
    """Cancel a running or queued conversion job."""
    
    # Check if API key is set
    if not API_KEY:
        print("Error: CONVERTHUB_API_KEY is not set")
        print("Get your API key at: https://converthub.com/api")
        print("\nSet it in .env file or use --api-key parameter")
        sys.exit(1)
    
    print("Cancel Job - ConvertHub API")
    print("=" * 28)
    print(f"Job ID: {job_id}")
    print("-" * 50 + "\n")
    
    try:
        headers = {
            'Authorization': f'Bearer {API_KEY}'
        }
        
        # First, check the current status
        print("→ Checking job status...")
        
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
        
        # Check if job can be cancelled
        if status == 'completed':
            print(f"\n{Fore.YELLOW}⚠️  Job already completed{Style.RESET_ALL}")
            print("The conversion has finished successfully.")
            if job.get('result', {}).get('download_url'):
                print(f"\nDownload URL: {job['result']['download_url']}")
            sys.exit(0)
        
        elif status == 'failed':
            print(f"\n{Fore.YELLOW}⚠️  Job already failed{Style.RESET_ALL}")
            if job.get('error'):
                print(f"Error: {job['error'].get('message', 'Unknown error')}")
            sys.exit(0)
        
        elif status == 'cancelled':
            print(f"\n{Fore.YELLOW}⚠️  Job already cancelled{Style.RESET_ALL}")
            sys.exit(0)
        
        # Display current status
        print(f"\nCurrent status: {Fore.CYAN}{status.capitalize()}{Style.RESET_ALL}")
        
        if job.get('source_format') and job.get('target_format'):
            print(f"Conversion: {job['source_format'].upper()} → {job['target_format'].upper()}")
        
        if job.get('created_at'):
            print(f"Created: {job['created_at']}")
        
        # Confirm cancellation
        if not force:
            print(f"\n{Fore.YELLOW}Warning: This action cannot be undone.{Style.RESET_ALL}")
            answer = input("Are you sure you want to cancel this job? (y/n): ")
            if answer.lower() != 'y':
                print("\n✗ Cancellation aborted")
                sys.exit(0)
        
        # Cancel the job
        print("\n→ Cancelling job...")
        
        response = requests.delete(
            f'{API_BASE_URL}/jobs/{job_id}',
            headers=headers
        )
        
        if response.status_code == 200 or response.status_code == 204:
            print(f"\n{Fore.GREEN}✓ Job cancelled successfully{Style.RESET_ALL}")
            
            # Show summary
            result = response.json() if response.text else {}
            if result.get('message'):
                print(f"  {result['message']}")
            
            print("\nThe conversion job has been cancelled.")
            
        elif response.status_code >= 400:
            error_data = response.json()
            error = error_data.get('error', {})
            print(f"\n✗ Failed to cancel job")
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
        description='Cancel a running or queued conversion job',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python cancel-job.py job_123e4567-e89b-12d3
  python cancel-job.py job_123e4567-e89b-12d3 --force
  
Get your API key at: https://converthub.com/api
        '''
    )
    
    parser.add_argument('job_id', help='The job ID to cancel')
    parser.add_argument('--force', action='store_true', help='Cancel without confirmation')
    parser.add_argument('--api-key', dest='api_key', help='Your API key')
    
    args = parser.parse_args()
    
    # Override API key if provided
    if args.api_key:
        global API_KEY
        API_KEY = args.api_key
    
    cancel_job(args.job_id, args.force)


if __name__ == '__main__':
    main()