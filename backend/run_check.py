import requests
import sys
import os

# This script can be called by a local cron job or as a trigger.
# It simply hits the /api/check endpoint of the deployed application.

def run_check():
    # Use environment variable for the URL, default to local for testing
    base_url = os.environ.get("APP_URL", "http://localhost:5000")
    check_url = f"{base_url.rstrip('/')}/api/check"
    
    print(f"Triggering reservation check at: {check_url}")
    
    try:
        # We use a POST request to trigger the check
        response = requests.post(check_url, timeout=300) # Long timeout for scraping
        response.raise_for_status()
        print(f"Success: {response.json()}")
    except Exception as e:
        print(f"Error triggering check: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_check()
