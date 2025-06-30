import requests
import os
import time
import unittest
import sys
from pathlib import Path

class VideoChatAPITester:
    def __init__(self, base_url="https://0220f5b6-83f5-48b4-8561-29449d7220c9.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.video_id = None
        self.session_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        if data and not files:
            headers['Content-Type'] = 'application/json'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files)
                else:
                    response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json().get('detail', 'No detail provided')
                    print(f"Error detail: {error_detail}")
                except:
                    print("Could not parse error response")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test the health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        if success:
            print(f"Health check response: {response}")
        return success

    def test_get_videos(self):
        """Test getting the list of videos"""
        success, response = self.run_test(
            "Get Videos",
            "GET",
            "api/videos",
            200
        )
        if success:
            videos = response.get('videos', [])
            print(f"Found {len(videos)} videos")
        return success

    def test_upload_video(self, video_path):
        """Test uploading a video file"""
        if not Path(video_path).exists():
            print(f"❌ Video file not found: {video_path}")
            return False
        
        print(f"Uploading video: {video_path}")
        with open(video_path, 'rb') as video_file:
            files = {'file': (Path(video_path).name, video_file, 'video/mp4')}
            success, response = self.run_test(
                "Upload Video",
                "POST",
                "api/upload-video",
                200,
                files=files
            )
        
        if success and 'video_id' in response:
            self.video_id = response['video_id']
            print(f"Video uploaded with ID: {self.video_id}")
        return success

    def test_analyze_video(self):
        """Test analyzing a video"""
        if not self.video_id:
            print("❌ No video ID available for analysis")
            return False
        
        success, response = self.run_test(
            "Analyze Video",
            "POST",
            f"api/analyze-video/{self.video_id}",
            200
        )
        
        if success:
            print(f"Video analysis status: {response.get('status', 'unknown')}")
            # Print a snippet of the analysis
            analysis = response.get('analysis', '')
            if analysis:
                print(f"Analysis snippet: {analysis[:100]}...")
        return success

    def test_chat_with_video(self, message="What is this video about?"):
        """Test chatting about a video"""
        if not self.video_id:
            print("❌ No video ID available for chat")
            return False
        
        data = {
            "video_id": self.video_id,
            "message": message,
            "session_id": self.session_id
        }
        
        success, response = self.run_test(
            "Chat with Video",
            "POST",
            "api/chat",
            200,
            data=data
        )
        
        if success:
            self.session_id = response.get('session_id')
            print(f"Chat response: {response.get('response', '')[:100]}...")
        return success

    def test_get_chat_history(self):
        """Test getting chat history for a video"""
        if not self.video_id:
            print("❌ No video ID available for getting chat history")
            return False
        
        success, response = self.run_test(
            "Get Chat History",
            "GET",
            f"api/chats/{self.video_id}",
            200
        )
        
        if success:
            chats = response.get('chats', [])
            print(f"Found {len(chats)} chat messages")
        return success

    def create_test_video(self, output_path="/tmp/test_video.mp4"):
        """Create a simple test video file using Python"""
        try:
            # Create a very simple binary file that mimics a video file structure
            with open(output_path, 'wb') as f:
                # Write a simple MP4 file header and some dummy data
                # This is not a valid video but should pass basic MIME type checks
                f.write(b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41\x00\x00\x00\x00')
                f.write(b'\x00\x00\x00\x08free\x00\x00\x00\x00')
                f.write(b'\x00\x00\x00\x08mdat')
                # Add some dummy video data (1MB)
                f.write(b'\x00' * 1024 * 1024)
            
            print(f"✅ Created test video: {output_path}")
            return output_path
        except Exception as e:
            print(f"❌ Failed to create test video: {str(e)}")
            return None

def main():
    # Setup
    tester = VideoChatAPITester()
    
    # Test health check
    if not tester.test_health_check():
        print("❌ Health check failed, stopping tests")
        return 1
    
    # Test getting videos
    tester.test_get_videos()
    
    # Create or find a test video
    test_video_path = "/tmp/test_video.mp4"
    if not Path(test_video_path).exists():
        test_video_path = tester.create_test_video()
    
    if not test_video_path or not Path(test_video_path).exists():
        print("❌ No test video available, stopping upload test")
        print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
        return 1
    
    # Test uploading a video
    if not tester.test_upload_video(test_video_path):
        print("❌ Video upload failed, stopping tests")
        print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
        return 1
    
    # Test analyzing the video
    if not tester.test_analyze_video():
        print("❌ Video analysis failed, stopping tests")
        print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
        return 1
    
    # Test chatting about the video
    if not tester.test_chat_with_video():
        print("❌ Chat with video failed, stopping tests")
        print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
        return 1
    
    # Test getting chat history
    tester.test_get_chat_history()
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())