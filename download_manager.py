
import yt_dlp
import requests
import tempfile
import os
import threading
import time
import uuid
from queue import Queue

# Global download tracking
download_queue = Queue()
download_status = {}

class DownloadManager:
    def __init__(self, snapchat_downloader):
        self.downloader = snapchat_downloader
    
    def progress_hook(self, d, download_id):
        """Progress hook for yt-dlp downloads"""
        if download_id in download_status:
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    progress = int((downloaded / total) * 100)
                    download_status[download_id]['progress'] = progress
                    download_status[download_id]['downloaded_bytes'] = downloaded
                    download_status[download_id]['total_bytes'] = total
            elif d['status'] == 'finished':
                download_status[download_id]['status'] = 'completed'
                download_status[download_id]['progress'] = 100
                download_status[download_id]['file_path'] = d['filename']
    
    def download_with_progress(self, url, format_type='mp4', quality='best', download_id=None):
        """Download content with progress tracking - REAL CONTENT ONLY"""
        if not download_id:
            download_id = str(uuid.uuid4())
        
        # Initialize download status
        download_status[download_id] = {
            'status': 'downloading',
            'progress': 0,
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'error': None,
            'file_path': None
        }
        
        try:
            # Use yt-dlp for all downloads
            temp_dir = tempfile.mkdtemp()
            
            # Configure yt-dlp options
            ydl_opts = {
                'format': f'bestvideo[ext={format_type}]+bestaudio[ext=m4a]/best[ext={format_type}]/best',
                'outtmpl': os.path.join(temp_dir, f'snapchat_{download_id}.%(ext)s'),
                'progress_hooks': [lambda d: self.progress_hook(d, download_id)],
                'quiet': False,  # Enable output for debugging
                'no_warnings': False,
                'headers': self.downloader.headers,
            }
            
            # Apply quality filter
            if quality != 'best':
                if quality.endswith('p'):
                    height = quality[:-1]
                    ydl_opts['format'] = f'best[height<={height}]/best'
            
            print(f"Starting yt-dlp download for: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Find the downloaded file
            files = os.listdir(temp_dir)
            if files:
                file_path = os.path.join(temp_dir, files[0])
                file_size = os.path.getsize(file_path)
                print(f"Downloaded file: {file_path}, Size: {file_size} bytes")
                
                download_status[download_id]['file_path'] = file_path
                download_status[download_id]['status'] = 'completed'
                download_status[download_id]['progress'] = 100
                download_status[download_id]['total_bytes'] = file_size
                return download_id, file_path
            else:
                raise Exception("No file was downloaded")
                
        except Exception as e:
            print(f"Download error: {e}")
            download_status[download_id]['status'] = 'failed'
            download_status[download_id]['error'] = str(e)
            raise e
    
    def get_download_status(self, download_id):
        """Get download status"""
        return download_status.get(download_id)
    
    def cleanup_download(self, download_id):
        """Clean up download files and status"""
        try:
            if download_id in download_status:
                file_path = download_status[download_id].get('file_path')
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    os.rmdir(os.path.dirname(file_path))
                del download_status[download_id]
        except:
            pass