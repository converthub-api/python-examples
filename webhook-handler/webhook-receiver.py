#!/usr/bin/env python3

import os
import sys
import json
import hmac
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

# Configuration
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')  # Optional: for signature verification
LOG_FILE = 'webhook_events.log'
PORT = int(os.getenv('WEBHOOK_PORT', 8080))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)


def verify_signature(payload, signature):
    """Verify webhook signature if secret is configured."""
    if not WEBHOOK_SECRET:
        return True  # No secret configured, skip verification
    
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)


def process_webhook_event(event_data):
    """Process the webhook event based on its type."""
    
    event_type = event_data.get('event')
    job_id = event_data.get('job_id')
    timestamp = event_data.get('timestamp', datetime.utcnow().isoformat())
    
    logger.info(f"Processing event: {event_type} for job: {job_id}")
    
    if event_type == 'conversion.completed':
        # Handle successful conversion
        result = event_data.get('result', {})
        logger.info(f"Conversion completed successfully")
        logger.info(f"  Job ID: {job_id}")
        logger.info(f"  Format: {result.get('format')}")
        logger.info(f"  Size: {result.get('file_size')} bytes")
        logger.info(f"  Download URL: {result.get('download_url')}")
        
        # Here you can add custom logic:
        # - Send email notification
        # - Update database
        # - Trigger download
        # - Send notification to user
        
        return {
            'status': 'success',
            'message': 'Conversion completed event processed',
            'job_id': job_id,
            'download_url': result.get('download_url')
        }
    
    elif event_type == 'conversion.failed':
        # Handle failed conversion
        error = event_data.get('error', {})
        logger.error(f"Conversion failed")
        logger.error(f"  Job ID: {job_id}")
        logger.error(f"  Error: {error.get('message')}")
        logger.error(f"  Code: {error.get('code')}")
        
        # Here you can add custom logic:
        # - Send error notification
        # - Log to error tracking service
        # - Retry conversion
        # - Alert admin
        
        return {
            'status': 'failed',
            'message': 'Conversion failed event processed',
            'job_id': job_id,
            'error': error.get('message')
        }
    
    elif event_type == 'conversion.progress':
        # Handle progress update
        progress = event_data.get('progress', {})
        logger.info(f"Conversion progress update")
        logger.info(f"  Job ID: {job_id}")
        logger.info(f"  Progress: {progress.get('percentage', 0)}%")
        logger.info(f"  Status: {progress.get('status')}")
        
        # Here you can add custom logic:
        # - Update progress in database
        # - Send real-time update to frontend
        # - Update progress bar
        
        return {
            'status': 'progress',
            'message': 'Progress update processed',
            'job_id': job_id,
            'progress': progress.get('percentage', 0)
        }
    
    elif event_type == 'upload.completed':
        # Handle upload completion (for chunked uploads)
        logger.info(f"Upload completed")
        logger.info(f"  Job ID: {job_id}")
        logger.info(f"  Session ID: {event_data.get('session_id')}")
        
        return {
            'status': 'uploaded',
            'message': 'Upload completed event processed',
            'job_id': job_id
        }
    
    else:
        # Unknown event type
        logger.warning(f"Unknown event type: {event_type}")
        return {
            'status': 'unknown',
            'message': f'Unknown event type: {event_type}',
            'job_id': job_id
        }


@app.route('/webhook', methods=['POST'])
def webhook():
    """Main webhook endpoint."""
    
    try:
        # Get raw request data
        raw_data = request.get_data()
        
        # Verify signature if configured
        signature = request.headers.get('X-Webhook-Signature', '')
        if WEBHOOK_SECRET and not verify_signature(raw_data, signature):
            logger.warning("Invalid webhook signature")
            return jsonify({'error': 'Invalid signature'}), 401
        
        # Parse JSON data
        try:
            event_data = json.loads(raw_data)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return jsonify({'error': 'Invalid JSON'}), 400
        
        # Log the raw event
        logger.info(f"Received webhook: {json.dumps(event_data, indent=2)}")
        
        # Process the event
        result = process_webhook_event(event_data)
        
        # Return success response
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'ConvertHub Webhook Receiver'
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with usage information."""
    return jsonify({
        'service': 'ConvertHub Webhook Receiver',
        'endpoints': {
            '/webhook': 'POST - Receive webhook events',
            '/health': 'GET - Health check',
            '/': 'GET - This message'
        },
        'documentation': 'https://converthub.com/api/docs',
        'log_file': LOG_FILE
    }), 200


def run_server():
    """Run the webhook server."""
    print("ConvertHub Webhook Receiver")
    print("=" * 28)
    print(f"Server starting on port {PORT}")
    print(f"Webhook endpoint: http://localhost:{PORT}/webhook")
    print(f"Health check: http://localhost:{PORT}/health")
    print(f"Logging to: {LOG_FILE}")
    
    if WEBHOOK_SECRET:
        print("✓ Signature verification enabled")
    else:
        print("⚠️  Warning: No WEBHOOK_SECRET configured")
        print("   Set WEBHOOK_SECRET in .env for signature verification")
    
    print("\nPress Ctrl+C to stop the server")
    print("-" * 50 + "\n")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=PORT, debug=False)


if __name__ == '__main__':
    # Command line usage
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
ConvertHub Webhook Receiver

Usage:
  python webhook-receiver.py        # Start the webhook server
  python webhook-receiver.py --help # Show this help message

Environment Variables:
  WEBHOOK_SECRET  - Secret key for signature verification (optional)
  WEBHOOK_PORT    - Port to listen on (default: 8080)

Example:
  1. Start the webhook server:
     python webhook-receiver.py
  
  2. Configure your ConvertHub API calls to use the webhook:
     webhook_url = "https://your-server.com/webhook"
  
  3. The server will log all events to webhook_events.log

For production deployment:
  - Use a proper WSGI server (gunicorn, uWSGI)
  - Configure HTTPS with a reverse proxy (nginx, Apache)
  - Set up proper logging and monitoring
  - Use a process manager (systemd, supervisor)

Example with gunicorn:
  gunicorn -w 4 -b 0.0.0.0:8080 webhook-receiver:app

Get your API key at: https://converthub.com/api
        """)
        sys.exit(0)
    
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n\nServer stopped")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)