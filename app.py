from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/get_size', methods=['POST'])
def get_size():
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        response = requests.get(url, stream=True)
        total_size = sum(len(chunk) for chunk in response.iter_content(1024))
        size_mb = round(total_size / (1024 * 1024), 2)
        return jsonify({"size_mb": size_mb})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
