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
def fetch_resource_size(resource_url, processed_urls, resource_type):
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
        logger.debug(f"Fetched {resource_type} resource: %s, size: %d bytes", resource_url, size)
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

        # Fetch main page content (HTML)
        main_response = requests.get(url, timeout=10)
        main_response.raise_for_status()
        html_content = main_response.text
        html_size_bytes = len(html_content.encode('utf-8'))
        logger.debug("HTML size in bytes: %d", html_size_bytes)

        # Parse the page to extract all resource URLs
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Initialize counters for each resource category
        html_size = html_size_bytes
        images_size = 0
        css_size = 0
        js_size = 0
        processed_urls = set()  # To track URLs we've already processed

        # Resource tags to consider for fetching external resources
        resource_tags = {'img': 'src', 'script': 'src', 'link': 'href'}
        resource_urls = {
            'images': [],
            'css': [],
            'js': []
        }

        # Categorize resources into images, CSS, and JS
        for tag, attr in resource_tags.items():
            for element in soup.find_all(tag):
                resource_url = element.get(attr)
                if resource_url:
                    full_url = urljoin(url, resource_url)
                    if full_url not in processed_urls:
                        processed_urls.add(full_url)
                        if tag == 'img':  # Categorize images
                            resource_urls['images'].append(full_url)
                        elif tag == 'link' and 'stylesheet' in element.get('rel', []):  # Categorize CSS
                            resource_urls['css'].append(full_url)
                        elif tag == 'script':  # Categorize JS
                            resource_urls['js'].append(full_url)

        # Log the resources we're about to fetch
        logger.debug("Resources to fetch: %s", resource_urls)

        # Use ThreadPoolExecutor to fetch resources concurrently
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Fetch images, CSS, and JS sizes separately
            images_size = sum(executor.map(fetch_resource_size, resource_urls['images'], [processed_urls]*len(resource_urls['images']), ['image']*len(resource_urls['images'])))
            css_size = sum(executor.map(fetch_resource_size, resource_urls['css'], [processed_urls]*len(resource_urls['css']), ['css']*len(resource_urls['css'])))
            js_size = sum(executor.map(fetch_resource_size, resource_urls['js'], [processed_urls]*len(resource_urls['js']), ['js']*len(resource_urls['js'])))

        total_size_bytes = html_size + images_size + css_size + js_size

        # Convert sizes to MB
        html_size_mb = round(html_size / (1024 * 1024), 2)
        images_size_mb = round(images_size / (1024 * 1024), 2)
        css_size_mb = round(css_size / (1024 * 1024), 2)
        js_size_mb = round(js_size / (1024 * 1024), 2)
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)

        logger.info(f"HTML size: {html_size_mb} MB, Images size: {images_size_mb} MB, CSS size: {css_size_mb} MB, JS size: {js_size_mb} MB, Total page size: {total_size_mb} MB")

        return jsonify({
            "html_size_mb": html_size_mb,
            "images_size_mb": images_size_mb,
            "css_size_mb": css_size_mb,
            "js_size_mb": js_size_mb,
            "total_size_mb": total_size_mb
        })

    except requests.RequestException as e:
        logger.error("Request error: %s", e)
        return jsonify({"error": f"Request error: {str(e)}"}), 500
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
