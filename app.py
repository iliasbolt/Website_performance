from flask import Flask, request, jsonify
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

# Helper function to fetch the resource size
def fetch_resource_size(resource_url):
    try:
        # Use stream=True to download the resource in chunks
        response = requests.get(resource_url, timeout=5, stream=True)
        response.raise_for_status()
        return sum(len(chunk) for chunk in response.iter_content(1024))
    except requests.RequestException as e:
        logger.warning("Failed to fetch %s: %s", resource_url, e)
        return 0

@app.route('/get_size', methods=['POST'])
def get_size():
    try:
        # Parse JSON
        data = request.get_json()
        url = data.get('url')
        if not url:
            logger.error("URL is missing")
            return jsonify({"error": "URL is required"}), 400

        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        logger.debug("Fetching URL: %s", url)

        # Fetch the main page content (HTML)
        main_response = requests.get(url, timeout=10)
        main_response.raise_for_status()
        html_content = main_response.text
        html_size_bytes = len(html_content.encode('utf-8'))
        logger.debug("HTML size in bytes: %d", html_size_bytes)

        # Parse the HTML content to find resource links
        soup = BeautifulSoup(html_content, 'html.parser')
        total_size_bytes = html_size_bytes
        resource_tags = {'img': 'src', 'link': 'href', 'script': 'src'}

        # List to store resource URLs
        resource_urls = []

        # Collect URLs of images, CSS, and JS files
        for tag, attr in resource_tags.items():
            for element in soup.find_all(tag):
                resource_url = element.get(attr)
                if resource_url:
                    full_url = urljoin(url, resource_url)
                    resource_urls.append(full_url)

        # Remove duplicate URLs
        resource_urls = list(set(resource_urls))

        # Use ThreadPoolExecutor to fetch resources concurrently
        with concurrent.futures.ThreadPoolExecutor() as executor:
            resource_sizes = list(executor.map(fetch_resource_size, resource_urls))
            total_size_bytes += sum(resource_sizes)

        # Calculate sizes in MB
        html_size_mb = round(html_size_bytes / (1024 * 1024), 2)
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)

        # Prepare resource sizes for images, CSS, and JS
        images_size = sum(size for url, size in zip(resource_urls, resource_sizes) if url.endswith(('jpg', 'jpeg', 'png', 'gif', 'svg')))
        css_size = sum(size for url, size in zip(resource_urls, resource_sizes) if url.endswith('css'))
        js_size = sum(size for url, size in zip(resource_urls, resource_sizes) if url.endswith('js'))

        images_size_mb = round(images_size / (1024 * 1024), 2)
        css_size_mb = round(css_size / (1024 * 1024), 2)
        js_size_mb = round(js_size / (1024 * 1024), 2)

        logger.info("HTML size: %s MB, Images size: %s MB, CSS size: %s MB, JS size: %s MB, Total page size: %s MB",
                     html_size_mb, images_size_mb, css_size_mb, js_size_mb, total_size_mb)

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
