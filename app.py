from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import concurrent.futures

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response

# Helper function to fetch resource size
def fetch_resource_size(resource_url, processed_urls):
    if resource_url in processed_urls:
        return 0  # Skip this resource if it's already been processed
    try:
        resource_response = requests.get(resource_url, timeout=5, stream=True)
        resource_response.raise_for_status()
        # Mark the resource as processed
        processed_urls.add(resource_url)
        # Calculate the size of the resource
        return sum(len(chunk) for chunk in resource_response.iter_content(1024))
    except requests.RequestException as e:
        logger.warning("Failed to fetch %s: %s", resource_url, e)
        return 0

@app.route('/get_size', methods=['POST'])
def get_size():
    try:
        # Parse JSON
        data = request.get_json()
        logger.debug("Received request data: %s", data)
        
        url = data.get('url')
        if not url:
            logger.error("URL is missing")
            return jsonify({"error": "URL is required"}), 400

        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        logger.debug("Fetching URL: %s", url)

        # Fetch main page content
        main_response = requests.get(url, timeout=10)
        main_response.raise_for_status()
        html_content = main_response.text
        html_size_bytes = len(html_content.encode('utf-8'))
        logger.debug("HTML size in bytes: %d", html_size_bytes)

        # Parse and fetch resources (only images, CSS, and JS)
        soup = BeautifulSoup(html_content, 'html.parser')
        total_size_bytes = html_size_bytes
        processed_urls = set()  # Set to keep track of processed resource URLs

        # Define the resource tags to track
        resource_tags = {
            'img': 'src',   # Images
            'script': 'src',  # JavaScript
            'link': 'href',   # CSS
        }

        # Prepare list of resource URLs to fetch
        resource_urls = []
        for tag, attr in resource_tags.items():
            for element in soup.find_all(tag):
                resource_url = element.get(attr)
                if resource_url:
                    full_url = urljoin(url, resource_url)
                    resource_urls.append(full_url)

        # Use ThreadPoolExecutor to fetch resources concurrently
        with concurrent.futures.ThreadPoolExecutor() as executor:
            resource_sizes = list(executor.map(lambda url: fetch_resource_size(url, processed_urls), resource_urls))
            total_size_bytes += sum(resource_sizes)

        # Convert sizes to MB
        html_size_mb = round(html_size_bytes / (1024 * 1024), 2)
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)

        logger.info("HTML size: %s MB, Total page size: %s MB", html_size_mb, total_size_mb)
        return jsonify({"html_size_mb": html_size_mb, "total_size_mb": total_size_mb})

    except requests.RequestException as e:
        logger.error("Request error: %s", e)
        return jsonify({"error": f"Request error: {str(e)}"}), 500
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
