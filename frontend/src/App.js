import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [videos, setVideos] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [uploadFile, setUploadFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Load videos on component mount
  useEffect(() => {
    loadVideos();
  }, []);

  // Load chat history when video is selected
  useEffect(() => {
    if (selectedVideo) {
      loadChatHistory(selectedVideo.video_id);
    }
  }, [selectedVideo]);

  const loadVideos = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/videos`);
      const data = await response.json();
      setVideos(data.videos || []);
    } catch (error) {
      console.error('Error loading videos:', error);
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file && file.type.startsWith('video/')) {
      setUploadFile(file);
    } else {
      alert('Please select a valid video file');
    }
  };

  const uploadVideo = async () => {
    if (!uploadFile) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', uploadFile);

    try {
      const response = await fetch(`${API_BASE_URL}/api/upload-video`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        alert('Video uploaded successfully!');
        setUploadFile(null);
        loadVideos(); // Refresh video list
        
        // Auto-analyze the uploaded video
        analyzeVideo(result.video_id);
      } else {
        const error = await response.json();
        alert(`Upload failed: ${error.detail}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert(`Upload failed: ${error.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const analyzeVideo = async (videoId) => {
    setIsAnalyzing(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze-video/${videoId}`, {
        method: 'POST',
      });

      if (response.ok) {
        const result = await response.json();
        alert('Video analyzed successfully!');
        loadVideos(); // Refresh video list to show updated status
        
        // If this is the currently selected video, refresh its data
        if (selectedVideo && selectedVideo.video_id === videoId) {
          setSelectedVideo({...selectedVideo, status: 'analyzed', analysis: result.analysis});
        }
      } else {
        const error = await response.json();
        alert(`Analysis failed: ${error.detail}`);
      }
    } catch (error) {
      console.error('Analysis error:', error);
      alert(`Analysis failed: ${error.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const selectVideo = async (video) => {
    setSelectedVideo(video);
    setChatHistory([]);
    setCurrentSessionId(null);
  };

  const loadChatHistory = async (videoId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chats/${videoId}`);
      const data = await response.json();
      setChatHistory(data.chats || []);
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const sendChatMessage = async () => {
    if (!chatMessage.trim() || !selectedVideo) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_id: selectedVideo.video_id,
          message: chatMessage,
          session_id: currentSessionId,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        
        // Add message to chat history
        const newMessage = {
          user_message: chatMessage,
          ai_response: result.response,
          timestamp: new Date().toISOString(),
        };
        
        setChatHistory(prev => [...prev, newMessage]);
        setCurrentSessionId(result.session_id);
        setChatMessage('');
      } else {
        const error = await response.json();
        alert(`Chat failed: ${error.detail}`);
      }
    } catch (error) {
      console.error('Chat error:', error);
      alert(`Chat failed: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendChatMessage();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">
            🎥 Video Chat AI
          </h1>
          <p className="text-xl text-gray-600">
            Upload videos and have intelligent conversations about their content
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">Upload Video</h2>
          <div className="flex flex-col space-y-4">
            <div className="flex items-center space-x-4">
              <input
                type="file"
                accept="video/*"
                onChange={handleFileSelect}
                className="flex-1 p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={uploadVideo}
                disabled={!uploadFile || isUploading}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-lg font-medium transition-colors duration-200"
              >
                {isUploading ? 'Uploading...' : 'Upload'}
              </button>
            </div>
            {uploadFile && (
              <p className="text-sm text-gray-600">
                Selected: {uploadFile.name} ({(uploadFile.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Video List */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Your Videos</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {videos.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No videos uploaded yet</p>
              ) : (
                videos.map((video) => (
                  <div
                    key={video.video_id}
                    onClick={() => selectVideo(video)}
                    className={`p-4 border rounded-lg cursor-pointer transition-all duration-200 ${
                      selectedVideo?.video_id === video.video_id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="font-medium text-gray-800 truncate">
                          {video.filename}
                        </h3>
                        <div className="flex items-center space-x-2 mt-1">
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            video.status === 'analyzed' 
                              ? 'bg-green-100 text-green-800' 
                              : video.status === 'uploaded'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {video.status}
                          </span>
                          <span className="text-xs text-gray-500">
                            {(video.size / 1024 / 1024).toFixed(2)} MB
                          </span>
                        </div>
                      </div>
                      {video.status === 'uploaded' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            analyzeVideo(video.video_id);
                          }}
                          disabled={isAnalyzing}
                          className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white px-3 py-1 rounded text-sm font-medium transition-colors duration-200"
                        >
                          {isAnalyzing ? 'Analyzing...' : 'Analyze'}
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Chat Interface */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">
              {selectedVideo ? `Chat about: ${selectedVideo.filename}` : 'Select a video to chat'}
            </h2>
            
            {!selectedVideo ? (
              <div className="text-center py-12 text-gray-500">
                <div className="text-6xl mb-4">💬</div>
                <p>Select a video from the list to start chatting about its content</p>
              </div>
            ) : selectedVideo.status !== 'analyzed' ? (
              <div className="text-center py-12 text-gray-500">
                <div className="text-6xl mb-4">⏳</div>
                <p>Video needs to be analyzed before you can chat about it</p>
                {selectedVideo.status === 'uploaded' && (
                  <button
                    onClick={() => analyzeVideo(selectedVideo.video_id)}
                    disabled={isAnalyzing}
                    className="mt-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-lg font-medium transition-colors duration-200"
                  >
                    {isAnalyzing ? 'Analyzing...' : 'Analyze Video'}
                  </button>
                )}
              </div>
            ) : (
              <div className="flex flex-col h-96">
                {/* Chat History */}
                <div className="flex-1 overflow-y-auto border border-gray-200 rounded-lg p-4 mb-4 space-y-4">
                  {chatHistory.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                      <p>Start a conversation about your video!</p>
                      <p className="text-sm mt-2">Try asking: "What is this video about?" or "Summarize the main points"</p>
                    </div>
                  ) : (
                    chatHistory.map((chat, index) => (
                      <div key={index} className="space-y-2">
                        <div className="bg-blue-100 p-3 rounded-lg ml-8">
                          <p className="text-gray-800">{chat.user_message}</p>
                        </div>
                        <div className="bg-gray-100 p-3 rounded-lg mr-8">
                          <p className="text-gray-800 whitespace-pre-wrap">{chat.ai_response}</p>
                        </div>
                      </div>
                    ))
                  )}
                  {isLoading && (
                    <div className="text-center text-gray-500">
                      <div className="animate-pulse">AI is thinking...</div>
                    </div>
                  )}
                </div>

                {/* Chat Input */}
                <div className="flex space-x-2">
                  <textarea
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask a question about the video..."
                    className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                    rows="2"
                  />
                  <button
                    onClick={sendChatMessage}
                    disabled={!chatMessage.trim() || isLoading}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-lg font-medium transition-colors duration-200 self-end"
                  >
                    Send
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;