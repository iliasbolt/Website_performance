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
    # Check if resource has already been processed to avoid duplication
    if resource_url in processed_urls:
        logger.debug("Skipping already processed URL: %s", resource_url)
        return 0  # Skip if already processed

    processed_urls.add(resource_url)  # Mark the resource as processed

    try:
        resource_response = requests.get(resource_url, timeout=5, stream=True)
        resource_response.raise_for_status()
        # Calculate the size of the resource by summing up the chunks
        size = sum(len(chunk) for chunk in resource_response.iter_content(1024))
        logger.debug("Fetched resource: %s, size: %d bytes", resource_url, size)
        return size
    except requests.RequestException as e:
        logger.warning("Failed to fetch %s: %s", resource_url, e)
        return 0

@app.route('/get_size', methods=['POST'])
def get_size():
    try:
        # Parse JSON request data
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            logger.error("URL is missing")
            return jsonify({"error": "URL is required"}), 400

        # Normalize the URL if necessary
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        logger.debug("Fetching URL: %s", url)

        # Fetch main page content
        main_response = requests.get(url, timeout=10)
        main_response.raise_for_status()
        html_content = main_response.text
        html_size_bytes = len(html_content.encode('utf-8'))
        logger.debug("HTML size in bytes: %d", html_size_bytes)

        # Parse the page to extract all resource URLs
        soup = BeautifulSoup(html_content, 'html.parser')
        total_size_bytes = html_size_bytes
        processed_urls = set()  # To track URLs we've already processed

        # Resource tags to consider for fetching external resources
        resource_tags = {'img': 'src', 'script': 'src', 'link': 'href'}
        resource_urls = []

        # Prepare the list of resources to fetch, checking for duplicates before adding to the list
        for tag, attr in resource_tags.items():
            for element in soup.find_all(tag):
                resource_url = element.get(attr)
                if resource_url:
                    full_url = urljoin(url, resource_url)
                    # Only add URL to list if it hasn't been processed already
                    if full_url not in processed_urls:
                        processed_urls.add(full_url)
                        resource_urls.append(full_url)

        # Use ThreadPoolExecutor to fetch resources concurrently
        with concurrent.futures.ThreadPoolExecutor() as executor:
            resource_sizes = list(executor.map(fetch_resource_size, resource_urls, [processed_urls]*len(resource_urls)))
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
