import yt_dlp
from urllib.parse import urlparse, parse_qs
import requests
import tempfile
import os
from datetime import datetime
import time
import uuid
import re

class SnapchatDownloader:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.snapchat.com/'
        }
    
    def is_snapchat_url(self, text):
        """Check if input is a Snapchat URL"""
        try:
            parsed = urlparse(text)
            return 'snapchat.com' in parsed.netloc or 't.snapchat.com' in parsed.netloc
        except:
            return False
    
    def is_valid_video_url(self, url):
        """Check if URL is a valid video URL, not a profile/website URL"""
        if not url:
            return False
        
        # Valid patterns that indicate actual content (more permissive approach)
        valid_patterns = [
            'cf-st.sc-cdn.net',
            'cf-st.snap-dev.net',
            'snap-dev.net',
            'snapchat.com/t/',  # Direct story links
            'snapchat.com/story/',
            'snapchat.com/p/',  # Story permalinks like /p/{id}/{timestamp}
            '/spotlight/',  # Spotlight content - matches @username/spotlight/id pattern
            '.mp4',
            '.m3u8'
        ]
        
        # Check for spotlight URLs pattern: /@username/spotlight/id
        if '/@' in url and '/spotlight/' in url:
            # Pattern: https://www.snapchat.com/@username/spotlight/W7_EDlXWTBiXAEEniNoMPwAA...
            return True
        
        # Check for story permalinks pattern: /p/id/timestamp
        if '/p/' in url:
            # Pattern: https://www.snapchat.com/p/uuid/timestamp
            path_parts = url.split('/p/')[-1].split('/')
            if len(path_parts) >= 2 and path_parts[0] and path_parts[1]:
                return True
        
        # Check for direct content URLs
        for pattern in valid_patterns:
            if pattern in url:
                return True
        
        # Only exclude clearly invalid patterns
        invalid_patterns = [
            'snapchat.com/add/' + ('' if '?' in url else ''),  # Only basic add URLs without params
            'snapchat.com/discover' + ('' if '/spotlight' in url else ''),  # Only discover home
        ]
        
        for pattern in invalid_patterns:
            if pattern in url and pattern.strip():
                return False
        
        return False
    
    def normalize_snapchat_url(self, url):
        """Normalize Snapchat URL to improve extraction success"""
        if not self.is_snapchat_url(url):
            return url
        
        # Extract spotlight ID from direct spotlight URLs
        spotlight_match = re.search(r'/spotlight/([A-Za-z0-9_-]+)', url)
        if spotlight_match:
            spotlight_id = spotlight_match.group(1)
            # Try to convert direct spotlight URL to user-context URL
            # First try with snapchat official account
            return f"https://www.snapchat.com/@snapchat/spotlight/{spotlight_id}"
        
        return url
    
    def build_snapchat_url_from_username(self, username):
        """Build Snapchat profile URL from username"""
        username = username.replace('@', '').strip()
        return f"https://www.snapchat.com/add/{username}"
    
    def extract_user_stories(self, username_or_url):
        """Extract all stories and spotlight videos from a Snapchat user - REAL CONTENT ONLY"""
        try:
            if self.is_snapchat_url(username_or_url):
                url = self.normalize_snapchat_url(username_or_url)
                # Extract username from different URL patterns
                if '/add/' in url:
                    username = url.split('/add/')[-1]
                elif '/@' in url:
                    username_part = url.split('/@')[1]
                    username = username_part.split('/')[0]  # Get first part after /@
                elif '/t/' in url:
                    username = 'snapchat_user'
                elif '/spotlight/' in url:
                    # For spotlight URLs, try to extract from context or use default
                    if '/@' in url:
                        username_part = url.split('/@')[1]
                        username = username_part.split('/')[0]
                    else:
                        username = 'snapchat'  # Default to snapchat for direct spotlight links
                else:
                    username = url.split('/')[-1].split('?')[0]  # Remove query params
            else:
                username = username_or_url.replace('@', '').strip()
                url = username_or_url
            
            print(f"Processing: {username_or_url}")
            print(f"Normalized URL: {url}")
            print(f"Extracted username: {username}")
            
            all_stories = []
            all_spotlight = []
            
            # If it's a direct Snapchat story/spotlight URL, process it directly
            if self.is_snapchat_url(username_or_url):
                try:
                    # Try original URL first
                    extracted_data = self.extract_from_url(username_or_url, username)
                    all_stories.extend(extracted_data['stories'])
                    all_spotlight.extend(extracted_data['spotlight'])
                    print(f"Original URL extraction: {len(all_stories)} stories, {len(all_spotlight)} spotlight")
                    
                    # If original URL didn't work and we have a normalized version, try that
                    if url != username_or_url and (len(all_stories) + len(all_spotlight) == 0):
                        print(f"Trying normalized URL: {url}")
                        extracted_data = self.extract_from_url(url, username)
                        all_stories.extend(extracted_data['stories'])
                        all_spotlight.extend(extracted_data['spotlight'])
                        print(f"Normalized URL extraction: {len(all_stories)} stories, {len(all_spotlight)} spotlight")
                        
                except Exception as e:
                    print(f"Direct URL extraction failed: {e}")
            
            # Try comprehensive profile-based extraction for usernames or if direct extraction failed
            if not self.is_snapchat_url(username_or_url) or len(all_stories) + len(all_spotlight) < 1:
                # Focus on URLs that are more likely to contain actual content
                profile_urls = [
                    f"https://www.snapchat.com/@{username}",
                    f"https://story.snapchat.com/@{username}",
                    f"https://www.snapchat.com/@{username}/spotlight",
                    f"https://www.snapchat.com/add/{username}",
                    f"https://www.snapchat.com/discover/{username}",
                    f"https://www.snapchat.com/spotlight/@{username}",
                ]
                
                for i, try_url in enumerate(profile_urls):
                    try:
                        print(f"Trying profile URL {i+1}/{len(profile_urls)}: {try_url}")
                        extracted_data = self.extract_from_url(try_url, username)
                        
                        # Add new stories (avoid duplicates and filter valid content)
                        new_stories = [s for s in extracted_data['stories'] 
                                     if (not any(existing['id'] == s['id'] for existing in all_stories) and
                                         self.is_valid_content_entry(s))]
                        all_stories.extend(new_stories)
                        
                        # Add new spotlight videos (avoid duplicates and filter valid content)
                        new_spotlight = [s for s in extracted_data['spotlight'] 
                                       if (not any(existing['id'] == s['id'] for existing in all_spotlight) and
                                           self.is_valid_content_entry(s))]
                        all_spotlight.extend(new_spotlight)
                        
                        if new_stories or new_spotlight:
                            print(f"Found {len(new_stories)} new valid stories, {len(new_spotlight)} new valid spotlight from {try_url}")
                            
                    except Exception as e:
                        print(f"Failed to extract from {try_url}: {e}")
                        continue
            
            # Final validation - remove any invalid entries
            all_stories = [s for s in all_stories if self.is_valid_content_entry(s)]
            all_spotlight = [s for s in all_spotlight if self.is_valid_content_entry(s)]
            
            print(f"Total valid extraction result: {len(all_stories)} stories, {len(all_spotlight)} spotlight")
            
            return {
                'username': username,
                'profile_url': username_or_url if self.is_snapchat_url(username_or_url) else f"https://www.snapchat.com/add/{username}",
                'avatar': f"https://ui-avatars.com/api/?name={username}&background=FFFC00&color=000",
                'stories': all_stories,
                'spotlight': all_spotlight,
                'total_count': len(all_stories),
                'spotlight_count': len(all_spotlight),
                'message': 'No content found. This could be because the user has no public stories/spotlight, or the content is private.' if (len(all_stories) + len(all_spotlight) == 0) else None
            }
            
        except Exception as e:
            print(f"Error in extract_user_stories: {e}")
            raise Exception(f"Failed to extract stories: {str(e)}")
    
    def is_valid_content_entry(self, entry):
        """Validate if a content entry is real and downloadable"""
        if not entry:
            return False
        
        # Check if best_quality URL is valid
        best_quality = entry.get('best_quality', {})
        if not best_quality or not self.is_valid_video_url(best_quality.get('url', '')):
            # More lenient check - if we have formats, it might still be valid
            formats = entry.get('formats', [])
            valid_formats = [f for f in formats if f.get('url') and ('http' in f.get('url', '') or 'cf-st' in f.get('url', ''))]
            if not valid_formats:
                print(f"Invalid entry - no valid video URLs: {entry.get('title', 'No title')}")
                return False
        
        # Check for minimum metadata requirements (more lenient)
        if not entry.get('title') and not entry.get('thumbnail') and entry.get('duration', 0) == 0:
            print(f"Invalid entry - insufficient metadata: {entry.get('id', 'No ID')}")
            return False
        
        print(f"Valid entry found: {entry.get('title', 'No title')}")
        return True
    
    def extract_from_url(self, url, username):
        """Extract data from a specific URL using yt-dlp - IMPROVED VERSION with better validation"""
        # Enhanced yt-dlp options for better Snapchat extraction
        ydl_opts = {
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'socket_timeout': 300,  # Increased timeout
            'headers': self.headers,
            'ignoreerrors': True,
            'no_color': True,
            'writeinfojson': False,
            'writethumbnail': False,
            # Try to get the best formats
            'format': 'best[ext=mp4]/best',
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            # Add more extractors and options
            'extractor_args': {
                'snapchat': {
                    'include_stories': True,
                    'include_spotlight': True
                }
            }
        }
        
        stories = []
        spotlight = []
        
        try:
            print(f"yt-dlp extracting from: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    print("No info extracted")
                    return {'stories': stories, 'spotlight': spotlight}
                
                print(f"Extracted info type: {type(info)}")
                print(f"Info keys: {list(info.keys()) if isinstance(info, dict) else 'Not a dict'}")
                
                # Handle playlist/multiple entries
                if 'entries' in info and info['entries']:
                    print(f"Processing {len(info['entries'])} entries")
                    for i, entry in enumerate(info['entries']):
                        if entry:
                            print(f"Processing entry {i+1}: {entry.get('title', 'No title')}")
                            processed = self.process_story_entry(entry, username)
                            if processed and self.is_valid_content_entry(processed):
                                existing_ids = [s['id'] for s in stories + spotlight]
                                if processed['id'] not in existing_ids:
                                    if self.is_spotlight_content(entry):
                                        processed['type'] = 'spotlight'
                                        processed['snapchat_url'] = self.generate_snapchat_url(entry, username)
                                        spotlight.append(processed)
                                        print(f"Added valid spotlight: {processed['title']}")
                                    else:
                                        processed['type'] = 'story'
                                        processed['snapchat_url'] = self.generate_snapchat_url(entry, username)
                                        stories.append(processed)
                                        print(f"Added valid story: {processed['title']}")
                            else:
                                print(f"Skipped invalid entry: {entry.get('title', 'No title')}")
                else:
                    # Single entry
                    print("Processing single entry")
                    processed = self.process_story_entry(info, username)
                    if processed and self.is_valid_content_entry(processed):
                        if self.is_spotlight_content(info):
                            processed['type'] = 'spotlight'
                            processed['snapchat_url'] = self.generate_snapchat_url(info, username)
                            spotlight.append(processed)
                            print(f"Single valid spotlight added: {processed['title']}")
                        else:
                            processed['type'] = 'story'
                            processed['snapchat_url'] = self.generate_snapchat_url(info, username)
                            stories.append(processed)
                            print(f"Single valid story added: {processed['title']}")
                    else:
                        print(f"Skipped invalid single entry: {info.get('title', 'No title')}")
                        
        except Exception as e:
            print(f"yt-dlp extraction error for {url}: {e}")
        
        print(f"Final valid extraction result from {url}: {len(stories)} stories, {len(spotlight)} spotlight")
        return {'stories': stories, 'spotlight': spotlight}
    
    def is_spotlight_content(self, entry):
        """Determine if content is spotlight based on metadata"""
        title = entry.get('title', '').lower()
        description = entry.get('description', '').lower()
        duration = entry.get('duration', 0)
        url = entry.get('url', '').lower()
        webpage_url = entry.get('webpage_url', '').lower()
        
        # Spotlight indicators
        spotlight_indicators = [
            'spotlight', 'discover', 'featured', 'trending', 'popular',
            'viral', 'public', 'share', 'explore'
        ]
        
        # Check URL patterns that indicate spotlight
        spotlight_url_patterns = [
            'spotlight',
            'discover',
            'public'
        ]
        
        # Check if it's likely spotlight content
        is_spotlight = (
            duration > 15 or  # Spotlight videos are usually longer than stories
            any(indicator in title for indicator in spotlight_indicators) or
            any(indicator in description for indicator in spotlight_indicators) or
            any(pattern in url for pattern in spotlight_url_patterns) or
            any(pattern in webpage_url for pattern in spotlight_url_patterns) or
            entry.get('view_count', 0) > 1000  # Higher view count suggests public content
        )
        
        return is_spotlight
    
    def generate_snapchat_url(self, entry, username):
        """Generate Snapchat URL for the content"""
        story_id = entry.get('id', '')
        webpage_url = entry.get('webpage_url', '')
        
        # If we have a webpage URL, use it
        if webpage_url and 'snapchat.com' in webpage_url:
            return webpage_url
        
        # Generate URL based on story ID
        if story_id and not story_id.startswith('snapchat_'):
            return f"https://www.snapchat.com/t/{story_id}"
        else:
            # Fallback to user profile
            return f"https://www.snapchat.com/add/{username}"
    
    def process_story_entry(self, entry, username):
        """Process a single story entry - ONLY REAL CONTENT with validation"""
        try:
            if not entry:
                return None
                
            print(f"Processing entry: {entry.get('title', 'No title')}")
            
            formats = []
            if 'formats' in entry and entry['formats']:
                for fmt in entry['formats']:
                    # Include valid video formats with real URLs (more lenient)
                    if (fmt.get('url') and 
                        (fmt.get('protocol') in ['http', 'https', 'm3u8', 'dash', 'rtmp'] or 
                         'cf-st' in fmt.get('url', '') or
                         'snap' in fmt.get('url', '')) and 
                        fmt.get('vcodec') != 'none'):
                        
                        ext = self.determine_file_extension(fmt)
                        
                        formats.append({
                            'url': fmt['url'],
                            'width': fmt.get('width', 0),
                            'height': fmt.get('height', 0),
                            'ext': ext,
                            'filesize': fmt.get('filesize', 0),
                            'quality': f"{fmt.get('height', 0)}p" if fmt.get('height') else 'Unknown',
                            'acodec': fmt.get('acodec', ''),
                            'vcodec': fmt.get('vcodec', ''),
                            'protocol': fmt.get('protocol', 'http')
                        })
            elif entry.get('url'):
                # Single format - more lenient validation
                formats.append({
                    'url': entry['url'],
                    'width': entry.get('width', 0),
                    'height': entry.get('height', 0),
                    'ext': entry.get('ext', 'mp4'),
                    'filesize': entry.get('filesize', 0),
                    'quality': f"{entry.get('height', 0)}p" if entry.get('height') else 'Unknown',
                    'acodec': entry.get('acodec', ''),
                    'vcodec': entry.get('vcodec', ''),
                    'protocol': 'http'
                })
            
            if not formats:
                print("No valid video formats found for entry - skipping")
                return None
            
            # Sort by quality (highest first)
            formats.sort(key=lambda x: x['height'] or 0, reverse=True)
            
            # Get best quality format
            best_quality = formats[0] if formats else None
            
            # Additional validation - ensure we have real content (more lenient)
            duration = entry.get('duration', 0)
            thumbnail = entry.get('thumbnail', '')
            title = entry.get('title', f"{username}'s Content")
            
            result = {
                'id': entry.get('id', f"snapchat_{int(time.time())}_{username}_{uuid.uuid4().hex[:8]}"),
                'title': title,
                'thumbnail': thumbnail,
                'duration': duration,
                'upload_date': entry.get('upload_date', datetime.now().strftime('%Y%m%d')),
                'view_count': entry.get('view_count', 0),
                'formats': formats,
                'best_quality': best_quality
            }
            
            print(f"Processed entry: {result['title']} with {len(formats)} formats, duration: {duration}s")
            return result
            
        except Exception as e:
            print(f"Error processing story entry: {e}")
            return None
    
    def determine_file_extension(self, fmt):
        """Determine the best file extension based on format info"""
        # Check if format has a known extension
        ext = fmt.get('ext', '')
        if ext in ['mp4', 'mkv', 'webm', 'mov', 'm4v']:
            return ext
        
        # Check codecs to determine best format
        vcodec = fmt.get('vcodec', '').lower()
        
        if 'h264' in vcodec or 'avc' in vcodec:
            return 'mp4'
        elif 'vp9' in vcodec or 'av1' in vcodec:
            return 'webm'
        elif 'h265' in vcodec or 'hevc' in vcodec:
            return 'mkv'
        
        # Default to mp4 if unsure
        return 'mp4'
