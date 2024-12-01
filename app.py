from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
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
        response = requests.get(resource_url, timeout=5, stream=True)
        response.raise_for_status()
        return sum(len(chunk) for chunk in response.iter_content(1024))
    except requests.RequestException as e:
        logger.warning("Failed to fetch %s: %s", resource_url, e)
        return 0

@app.route('/get_size', methods=['POST'])
def get_size():
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({"error": "URL is required"}), 400

        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        main_response = requests.get(url, timeout=10)
        main_response.raise_for_status()
        html_content = main_response.text
        html_size_bytes = len(html_content.encode('utf-8'))

        soup = BeautifulSoup(html_content, 'html.parser')
        domain = urlparse(url).netloc
        resource_tags = {'img': 'src', 'link': 'href', 'script': 'src'}

        images, css, js, external_resources = [], [], [], []

        for tag, attr in resource_tags.items():
            for element in soup.find_all(tag):
                resource_url = element.get(attr)
                if resource_url:
                    full_url = urljoin(url, resource_url)
                    if tag == 'img':
                        images.append(full_url)
                    elif tag == 'link' and element.get('rel') == ['stylesheet']:
                        css.append(full_url)
                    elif tag == 'script':
                        js.append(full_url)
                    if domain not in urlparse(full_url).netloc:
                        external_resources.append(full_url)

        css_background_images = []
        for css_url in css:
            try:
                css_response = requests.get(css_url, timeout=5)
                css_response.raise_for_status()
                css_content = css_response.text
                css_background_images.extend(
                    urljoin(css_url, match) for match in re.findall(r'url\((.*?)\)', css_content)
                )
            except requests.RequestException as e:
                logger.warning("Failed to fetch CSS: %s", e)

        images.extend(css_background_images)
        images = list(set(images))  # Remove duplicates

        all_resources = images + css + js + external_resources
        all_resource_sizes = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            sizes = list(executor.map(fetch_resource_size, all_resources))
            all_resource_sizes = dict(zip(all_resources, sizes))

        images_size = sum(all_resource_sizes[url] for url in images)
        css_size = sum(all_resource_sizes[url] for url in css)
        js_size = sum(all_resource_sizes[url] for url in js)
        external_size = sum(all_resource_sizes[url] for url in external_resources)

        total_size = html_size_bytes + images_size + css_size + js_size + external_size

        response_data = {
            "html_size_mb": round(html_size_bytes / (1024 * 1024), 2),
            "images_size_mb": round(images_size / (1024 * 1024), 2),
            "css_size_mb": round(css_size / (1024 * 1024), 2),
            "js_size_mb": round(js_size / (1024 * 1024), 2),
            "external_size_mb": round(external_size / (1024 * 1024), 2),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }

        logger.info(response_data)
        return jsonify(response_data)

    except requests.RequestException as e:
        logger.error("Request error: %s", e)
        return jsonify({"error": f"Request error: {str(e)}"}), 500
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
