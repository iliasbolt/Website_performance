from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import concurrent.futures
import re

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

def calculate_base64_size(base64_str):
    """Calculate the size of base64-encoded data"""
    match = re.match(r"^data:image/.+;base64,(.*)", base64_str)
    if match:
        base64_data = match.group(1)
        return len(base64_data) * 3 / 4  # Estimate size in bytes
    return 0

def fetch_css_and_find_resources(css_url):
    """Fetch external CSS file and find image resources in it"""
    css_response = requests.get(css_url)
    css_response.raise_for_status()
    css_content = css_response.text

    # Find background images or other resources in the CSS
    image_urls = re.findall(r'url\(["\']?(https?://[^"\']+)', css_content)
    return image_urls

# Helper function to fetch resource size
def fetch_resource_size(resource_url):
    try:
        resource_response = requests.get(resource_url, timeout=5, stream=True)
        resource_response.raise_for_status()
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

        # Initialize total size with HTML size
        total_size_bytes = html_size_bytes

        # Parse HTML content
        soup = BeautifulSoup(html_content, 'html.parser')

        # Array to track resources we need to check
        resource_urls = []
        fetched_resources = set()

        # Resource tags (img, script, link)
        resource_tags = {'img': 'src', 'script': 'src', 'link': 'href'}
        for tag, attr in resource_tags.items():
            for element in soup.find_all(tag):
                resource_url = element.get(attr)
                if resource_url:
                    full_url = urljoin(url, resource_url)
                    if full_url not in fetched_resources:
                        fetched_resources.add(full_url)
                        resource_urls.append(full_url)

        # Check for base64-encoded images
        for img_tag in soup.find_all('img'):
            src = img_tag.get('src')
            if src and src.startswith('data:image/'):
                base64_size = calculate_base64_size(src)
                total_size_bytes += base64_size
                logger.debug("Base64 image size: %d bytes", base64_size)

        # Check for resources in external CSS files
        for link_tag in soup.find_all('link', {'rel': 'stylesheet'}):
            href = link_tag.get('href')
            if href:
                full_url = urljoin(url, href)
                try:
                    css_images = fetch_css_and_find_resources(full_url)
                    for image_url in css_images:
                        if image_url not in fetched_resources:
                            fetched_resources.add(image_url)
                            resource_urls.append(image_url)
                except requests.RequestException as e:
                    logger.warning("Failed to fetch CSS resource %s: %s", full_url, e)

        # Use ThreadPoolExecutor to fetch resources concurrently
        with concurrent.futures.ThreadPoolExecutor() as executor:
            resource_sizes = list(executor.map(fetch_resource_size, resource_urls))
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
