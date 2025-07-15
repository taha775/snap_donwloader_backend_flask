from flask import Flask
from flask_cors import CORS
from snapchat_downloader import SnapchatDownloader
from download_manager import DownloadManager
from api_routes import create_api_routes

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize components
downloader = SnapchatDownloader()
download_manager = DownloadManager(downloader)

# Create API routes
create_api_routes(app, downloader, download_manager)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)