#!/usr/bin/env python3

import os
import sys
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

API_BASE_URL = os.getenv('CONVERTHUB_API_BASE_URL', 'https://api.converthub.com/v2')
API_KEY = os.getenv('CONVERTHUB_API_KEY')


def list_formats(from_format=None, check_conversion=None):
    """List supported formats and conversions."""
    
    # Check if API key is set
    if not API_KEY:
        print("Error: CONVERTHUB_API_KEY is not set")
        print("Get your API key at: https://converthub.com/api")
        print("\nSet it in .env file or use --api-key parameter")
        sys.exit(1)
    
    print("Format Discovery - ConvertHub API")
    print("=" * 34)
    
    try:
        headers = {
            'Authorization': f'Bearer {API_KEY}'
        }
        
        # Check specific conversion
        if check_conversion:
            if ':' not in check_conversion:
                print(f"Error: Invalid format. Use 'from:to' (e.g., pdf:docx)")
                sys.exit(1)
            
            from_fmt, to_fmt = check_conversion.split(':', 1)
            print(f"\n→ Checking conversion: {from_fmt.upper()} → {to_fmt.upper()}")
            
            response = requests.get(
                f'{API_BASE_URL}/formats/{from_fmt}/conversions',
                headers=headers
            )
            
            if response.status_code >= 400:
                error_data = response.json()
                error = error_data.get('error', {})
                print(f"\n✗ Error: {error.get('message', 'Format not supported')}")
                sys.exit(1)
            
            data = response.json()
            
            # Handle different response structures - API returns 'available_conversions'
            supported_formats = []
            if isinstance(data, dict):
                conv_data = data.get('available_conversions', data.get('conversions', data.get('supported_conversions', [])))
                if isinstance(conv_data, list):
                    supported_formats = conv_data
                elif isinstance(conv_data, dict):
                    for category, formats in conv_data.items():
                        if isinstance(formats, list):
                            for fmt in formats:
                                if isinstance(fmt, dict):
                                    supported_formats.append(fmt.get('target_format', fmt.get('extension', fmt.get('format', ''))))
                                elif isinstance(fmt, str):
                                    supported_formats.append(fmt)
            elif isinstance(data, list):
                supported_formats = data
            
            # Convert supported_formats to list of strings
            supported_format_strings = []
            for fmt in supported_formats:
                if isinstance(fmt, dict):
                    supported_format_strings.append(fmt.get('target_format', fmt.get('extension', fmt.get('format', ''))))
                else:
                    supported_format_strings.append(fmt)
            
            if to_fmt.lower() in [f.lower() for f in supported_format_strings]:
                print(f"\n{Fore.GREEN}✓ Conversion supported!{Style.RESET_ALL}")
                print(f"\nYou can convert {from_fmt.upper()} files to {to_fmt.upper()} format.")
                print("\nExample commands:")
                print(f"  python simple-convert/convert.py file.{from_fmt} {to_fmt}")
                print(f"  python url-convert/convert-from-url.py https://example.com/file.{from_fmt} {to_fmt}")
            else:
                print(f"\n{Fore.RED}✗ Conversion not supported{Style.RESET_ALL}")
                print(f"\n{from_fmt.upper()} cannot be converted to {to_fmt.upper()}")
                print(f"\nSupported conversions from {from_fmt.upper()}:")
                for i, fmt in enumerate(supported_format_strings[:10], 1):
                    print(f"  {i}. {fmt.upper()}")
                if len(supported_format_strings) > 10:
                    print(f"  ... and {len(supported_format_strings) - 10} more")
            
            return
        
        # List conversions from a specific format
        if from_format:
            print(f"\n→ Getting conversions from {from_format.upper()}...")
            
            response = requests.get(
                f'{API_BASE_URL}/formats/{from_format}/conversions',
                headers=headers
            )
            
            if response.status_code >= 400:
                error_data = response.json()
                error = error_data.get('error', {})
                print(f"\n✗ Error: {error.get('message', 'Format not supported')}")
                sys.exit(1)
            
            data = response.json()
            
            # Handle different response structures - API returns 'available_conversions'
            conversions = []
            if isinstance(data, dict):
                # Try different possible keys
                conv_data = data.get('available_conversions', data.get('conversions', data.get('supported_conversions', [])))
                if isinstance(conv_data, list):
                    conversions = conv_data
                elif isinstance(conv_data, dict):
                    # If it's a dict, extract the format extensions
                    for category, formats in conv_data.items():
                        if isinstance(formats, list):
                            for fmt in formats:
                                if isinstance(fmt, dict):
                                    conversions.append(fmt.get('target_format', fmt.get('extension', fmt.get('format', ''))))
                                elif isinstance(fmt, str):
                                    conversions.append(fmt)
            elif isinstance(data, list):
                conversions = data
            
            print(f"\n{Fore.CYAN}Available conversions from {from_format.upper()}:{Style.RESET_ALL}")
            print("-" * 50)
            
            # Group by category
            categories = {
                'Images': ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'svg', 'ico', 'heic'],
                'Documents': ['pdf', 'docx', 'doc', 'txt', 'rtf', 'odt', 'html', 'markdown', 'tex'],
                'Spreadsheets': ['xlsx', 'xls', 'csv', 'ods', 'tsv'],
                'Presentations': ['pptx', 'ppt', 'odp', 'key'],
                'Videos': ['mp4', 'webm', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'mpg'],
                'Audio': ['mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac', 'wma', 'opus'],
                'eBooks': ['epub', 'mobi', 'azw3', 'fb2', 'lit'],
                'Archives': ['zip', 'rar', '7z', 'tar', 'gz', 'bz2']
            }
            
            categorized = {}
            other = []
            
            for fmt in conversions:
                # Handle both string and dict formats
                if isinstance(fmt, dict):
                    fmt_str = fmt.get('target_format', fmt.get('extension', fmt.get('format', '')))
                else:
                    fmt_str = fmt
                
                found = False
                for category, formats in categories.items():
                    if fmt_str.lower() in formats:
                        if category not in categorized:
                            categorized[category] = []
                        categorized[category].append(fmt_str.upper())
                        found = True
                        break
                if not found:
                    other.append(fmt_str.upper())
            
            # Display categorized formats
            for category in categories.keys():
                if category in categorized:
                    print(f"\n{Fore.YELLOW}{category}:{Style.RESET_ALL}")
                    formats = categorized[category]
                    for i in range(0, len(formats), 10):
                        print("  " + ", ".join(formats[i:i+10]))
            
            if other:
                print(f"\n{Fore.YELLOW}Other:{Style.RESET_ALL}")
                for i in range(0, len(other), 10):
                    print("  " + ", ".join(other[i:i+10]))
            
            print(f"\n{Fore.GREEN}Total: {len(conversions)} formats supported{Style.RESET_ALL}")
            
            return
        
        # List all supported formats
        print("\n→ Getting all supported formats...")
        
        response = requests.get(
            f'{API_BASE_URL}/formats',
            headers=headers
        )
        
        if response.status_code >= 400:
            error_data = response.json()
            error = error_data.get('error', {})
            print(f"\n✗ Error: {error.get('message', 'Failed to get formats')}")
            sys.exit(1)
        
        data = response.json()
        
        # Handle the new API response structure
        raw_formats = data.get('formats', {})
        formats = {}
        
        # The API returns formats grouped by category
        if isinstance(raw_formats, dict):
            for category, format_list in raw_formats.items():
                if isinstance(format_list, list):
                    for fmt_info in format_list:
                        if isinstance(fmt_info, dict):
                            ext = fmt_info.get('extension', '')
                            formats[ext] = fmt_info
                        else:
                            # Handle simple string format
                            formats[fmt_info] = {'conversions': []}
                else:
                    # Direct format mapping
                    formats = raw_formats
                    break
        
        print(f"\n{Fore.CYAN}All Supported Formats:{Style.RESET_ALL}")
        print("-" * 50)
        
        # Group by category
        categories = {
            'Images': ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'svg', 'ico', 'heic', 'tga', 'psd'],
            'Documents': ['pdf', 'docx', 'doc', 'txt', 'rtf', 'odt', 'html', 'markdown', 'tex', 'xml'],
            'Spreadsheets': ['xlsx', 'xls', 'csv', 'ods', 'tsv'],
            'Presentations': ['pptx', 'ppt', 'odp', 'key'],
            'Videos': ['mp4', 'webm', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'mpg', 'm4v', '3gp'],
            'Audio': ['mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac', 'wma', 'opus', 'aiff'],
            'eBooks': ['epub', 'mobi', 'azw3', 'fb2', 'lit', 'pdb'],
            'Archives': ['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz'],
            'CAD': ['dwg', 'dxf', 'dwf', 'stl', 'obj'],
            'Fonts': ['ttf', 'otf', 'woff', 'woff2', 'eot']
        }
        
        categorized = {}
        other = []
        
        for fmt in formats.keys():
            found = False
            for category, format_list in categories.items():
                if fmt.lower() in format_list:
                    if category not in categorized:
                        categorized[category] = []
                    categorized[category].append(fmt.upper())
                    found = True
                    break
            if not found:
                other.append(fmt.upper())
        
        # Display categorized formats with conversion counts
        total_conversions = 0
        for category in categories.keys():
            if category in categorized:
                print(f"\n{Fore.YELLOW}{category}:{Style.RESET_ALL}")
                category_formats = categorized[category]
                for fmt in category_formats:
                    fmt_lower = fmt.lower()
                    if fmt_lower in formats:
                        fmt_data = formats[fmt_lower]
                        if isinstance(fmt_data, dict):
                            conversions = fmt_data.get('conversions', fmt_data.get('supported_conversions', []))
                            if isinstance(conversions, list):
                                num_conversions = len(conversions)
                            else:
                                num_conversions = 0
                        else:
                            num_conversions = 0
                        total_conversions += num_conversions
                        if num_conversions > 0:
                            print(f"  • {fmt} ({num_conversions} conversions)")
                        else:
                            print(f"  • {fmt}")
        
        if other:
            print(f"\n{Fore.YELLOW}Other:{Style.RESET_ALL}")
            for fmt in other:
                fmt_lower = fmt.lower()
                if fmt_lower in formats:
                    fmt_data = formats[fmt_lower]
                    if isinstance(fmt_data, dict):
                        conversions = fmt_data.get('conversions', fmt_data.get('supported_conversions', []))
                        if isinstance(conversions, list):
                            num_conversions = len(conversions)
                        else:
                            num_conversions = 0
                    else:
                        num_conversions = 0
                    total_conversions += num_conversions
                    if num_conversions > 0:
                        print(f"  • {fmt} ({num_conversions} conversions)")
                    else:
                        print(f"  • {fmt}")
        
        print(f"\n{Fore.GREEN}Summary:{Style.RESET_ALL}")
        print(f"  Total formats: {len(formats)}")
        print(f"  Total conversion pairs: {total_conversions}")
        
        print("\n" + "-" * 50)
        print("Usage examples:")
        print("  python list-formats.py --from=pdf")
        print("  python list-formats.py --check=pdf:docx")
        
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
        description='Explore supported formats and conversions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python list-formats.py                    # List all supported formats
  python list-formats.py --from=pdf         # Show all conversions from PDF
  python list-formats.py --check=pdf:docx   # Check if PDF to DOCX is supported
  
Get your API key at: https://converthub.com/api
        '''
    )
    
    parser.add_argument('--from', dest='from_format', help='List conversions from this format')
    parser.add_argument('--check', dest='check_conversion', help='Check if conversion is supported (format: from:to)')
    parser.add_argument('--api-key', dest='api_key', help='Your API key')
    
    args = parser.parse_args()
    
    # Override API key if provided
    if args.api_key:
        global API_KEY
        API_KEY = args.api_key
    
    # Validate arguments
    if args.from_format and args.check_conversion:
        print("Error: Please use only one of --from or --check")
        sys.exit(1)
    
    list_formats(
        from_format=args.from_format,
        check_conversion=args.check_conversion
    )


if __name__ == '__main__':
    main()