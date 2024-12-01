# Improved Backend Calculation Logic
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import re
import concurrent.futures

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def fetch_resource_size(resource_url):
    try:
        resource_response = requests.get(resource_url, timeout=5, stream=True)
        resource_response.raise_for_status()
        return sum(len(chunk) for chunk in resource_response.iter_content(1024))
    except requests.RequestException as e:
        logger.warning("Failed to fetch %s: %s", resource_url, e)
        return 0

def get_size(url):
    try:
        # Fetch main page content
        main_response = requests.get(url, timeout=10)
        main_response.raise_for_status()
        html_content = main_response.text
        html_size_bytes = len(html_content.encode('utf-8'))

        # Parse HTML and find resources
        soup = BeautifulSoup(html_content, 'html.parser')
        total_size_bytes = html_size_bytes
        resources = {
            'images': [],
            'css': [],
            'js': [],
            'external': []
        }

        # Look for image sources, including inline CSS background images
        for img_tag in soup.find_all('img'):
            src = img_tag.get('src')
            if src:
                resource_url = urljoin(url, src)
                resources['images'].append(resource_url)

        # Look for CSS files (both external and background-image CSS)
        for link_tag in soup.find_all('link', rel='stylesheet'):
            href = link_tag.get('href')
            if href:
                resource_url = urljoin(url, href)
                resources['css'].append(resource_url)

        # Look for JavaScript files
        for script_tag in soup.find_all('script', src=True):
            src = script_tag.get('src')
            if src:
                resource_url = urljoin(url, src)
                resources['js'].append(resource_url)

        # Check for background-image URLs in CSS
        css_files = [link.get('href') for link in soup.find_all('link', rel='stylesheet')]
        for css_url in css_files:
            css_response = requests.get(urljoin(url, css_url))
            if css_response.status_code == 200:
                css_content = css_response.text
                # Regular expression to find all background image URLs
                background_images = re.findall(r'url\((["\']?)(.*?)\1\)', css_content)
                for img_url in background_images:
                    resources['images'].append(urljoin(url, img_url[1]))

        # Calculate sizes for resources
        image_size = sum(fetch_resource_size(url) for url in resources['images'])
        css_size = sum(fetch_resource_size(url) for url in resources['css'])
        js_size = sum(fetch_resource_size(url) for url in resources['js'])

        total_size_bytes += image_size + css_size + js_size

        # Convert sizes to MB
        html_size_mb = round(html_size_bytes / (1024 * 1024), 2)
        images_size_mb = round(image_size / (1024 * 1024), 2)
        css_size_mb = round(css_size / (1024 * 1024), 2)
        js_size_mb = round(js_size / (1024 * 1024), 2)
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)

        return {
            "html_size_mb": html_size_mb,
            "images_size_mb": images_size_mb,
            "css_size_mb": css_size_mb,
            "js_size_mb": js_size_mb,
            "total_size_mb": total_size_mb,
            "images": [{"url": url, "size": fetch_resource_size(url)} for url in resources['images']],
            "css": [{"url": url, "size": fetch_resource_size(url)} for url in resources['css']],
            "js": [{"url": url, "size": fetch_resource_size(url)} for url in resources['js']],
            "external_resources": []
        }

    except requests.RequestException as e:
        logger.error("Request error: %s", e)
        return {"error": f"Request error: {str(e)}"}
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return {"error": f"Unexpected error: {str(e)}"}

