
from flask import request, jsonify, send_file
import threading
import time
import uuid
import os

def create_api_routes(app, downloader, download_manager):
    """Create all API routes"""
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "healthy", "message": "Advanced Snapchat Downloader API is running"})

    @app.route('/api/snapchat/stories', methods=['POST'])
    def get_snapchat_stories():
        """Get all stories and spotlight videos from a Snapchat user"""
        try:
            data = request.get_json()
            input_value = data.get('input', '').strip()
            
            if not input_value:
                return jsonify(success=False, message="Username or URL is required"), 400
            
            print(f"Extracting stories and spotlight for: {input_value}")
            
            result = downloader.extract_user_stories(input_value)
            
            return jsonify(success=True, data=result)
            
        except Exception as e:
            print(f"Error in get_snapchat_stories: {e}")
            return jsonify(success=False, message=str(e)), 500

    @app.route('/api/snapchat/download', methods=['POST'])
    def download_story():
        """Download a specific story with progress tracking"""
        try:
            data = request.get_json()
            content_url = data.get('url', '').strip()
            preferred_format = data.get('format', 'mp4')
            quality = data.get('quality', 'best')
            
            if not content_url:
                return jsonify(success=False, message="Content URL is required"), 400
            
            print(f"Starting download for URL: {content_url}")
            
            # Generate download ID
            download_id = str(uuid.uuid4())
            
            # Start download in background thread
            def download_worker():
                try:
                    download_manager.download_with_progress(content_url, preferred_format, quality, download_id)
                except Exception as e:
                    print(f"Download failed: {e}")
            
            thread = threading.Thread(target=download_worker)
            thread.daemon = True
            thread.start()
            
            return jsonify(success=True, download_id=download_id)
            
        except Exception as e:
            print(f"Error in download_story: {e}")
            return jsonify(success=False, message=str(e)), 500

    @app.route('/api/snapchat/download/status/<download_id>', methods=['GET'])
    def get_download_status(download_id):
        """Get download status and progress"""
        status = download_manager.get_download_status(download_id)
        if not status:
            return jsonify(success=False, message="Download not found"), 404
        
        return jsonify(success=True, status=status)

    @app.route('/api/snapchat/download/file/<download_id>', methods=['GET'])
    def download_file(download_id):
        """Download the completed file"""
        status = download_manager.get_download_status(download_id)
        if not status:
            return jsonify(success=False, message="Download not found"), 404
        
        if status['status'] != 'completed' or not status['file_path']:
            return jsonify(success=False, message="File not ready for download"), 400
        
        file_path = status['file_path']
        if not os.path.exists(file_path):
            return jsonify(success=False, message="File not found"), 404
        
        try:
            return send_file(
                file_path,
                as_attachment=True,
                download_name=f"snapchat_{download_id}.mp4"
            )
        except Exception as e:
            return jsonify(success=False, message=str(e)), 500
        finally:
            # Clean up file after download
            download_manager.cleanup_download(download_id)

    @app.route('/api/snapchat/batch-download', methods=['POST'])
    def batch_download():
        """Start batch download of multiple stories"""
        try:
            data = request.get_json()
            urls = data.get('urls', [])
            preferred_format = data.get('format', 'mp4')
            quality = data.get('quality', 'best')
            
            if not urls:
                return jsonify(success=False, message="No URLs provided"), 400
            
            download_ids = []
            
            for url in urls:
                download_id = str(uuid.uuid4())
                download_ids.append(download_id)
                
                # Start download in background thread
                def download_worker(url=url, download_id=download_id):
                    try:
                        time.sleep(1)  # Small delay between downloads
                        download_manager.download_with_progress(url, preferred_format, quality, download_id)
                    except Exception as e:
                        print(f"Batch download failed for {url}: {e}")
                
                thread = threading.Thread(target=download_worker)
                thread.daemon = True
                thread.start()
            
            return jsonify(success=True, download_ids=download_ids)
            
        except Exception as e:
            print(f"Error in batch_download: {e}")
            return jsonify(success=False, message=str(e)), 500