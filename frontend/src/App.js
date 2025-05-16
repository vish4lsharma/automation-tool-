import React, { useState, useEffect } from 'react';
import './App.css';
import FileUpload from './components/FileUpload';
import FileList from './components/FileList';
import SearchBar from './components/SearchBar';
import SearchResults from './components/SearchResults';
import FileViewer from './components/FileViewer';

function App() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('files'); // 'files' or 'search'
  
  // API URL - change this to match your backend
  const API_URL = 'http://localhost:5000/api';

  // Fetch files on component mount
  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/files`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch files: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // Map response to our file format
      const mappedFiles = data.map(file => ({
        id: file.id,
        name: file.filename,
        type: file.type
      }));
      
      setFiles(mappedFiles);
    } catch (err) {
      console.error('Error fetching files:', err);
      setError(`Failed to fetch files: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file) => {
    setLoading(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to upload file');
      }
      
      const data = await response.json();
      
      // Add the new file to our list
      setFiles(prevFiles => [
        ...prevFiles, 
        { 
          id: data.id, 
          name: data.filename, 
          type: data.type 
        }
      ]);
      
      // Show success message
      alert('File uploaded successfully!');
    } catch (err) {
      console.error('Error uploading file:', err);
      setError(`Failed to upload file: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    // When a file is selected, switch to the file view tab
    setActiveTab('files');
  };

  const handleSearch = async (query, fileId = null) => {
    if (!query) return;
    
    setLoading(true);
    setError(null);
    setSearchResults([]);
    
    try {
      let searchUrl = `${API_URL}/search?query=${encodeURIComponent(query)}`;
      
      if (fileId) {
        searchUrl += `&file_id=${fileId}`;
      }
      
      const response = await fetch(searchUrl);
      
      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }
      
      const data = await response.json();
      setSearchResults(data.results);
      
      // Switch to search results tab
      setActiveTab('search');
    } catch (err) {
      console.error('Error searching:', err);
      setError(`Search failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchInFile = (file) => {
    const searchQuery = prompt('Enter search term:');
    if (searchQuery) {
      handleSearch(searchQuery, file.id);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Document Search System</h1>
        <p>Upload, view, and search through various document types</p>
      </header>
      
      <main className="app-main">
        <div className="sidebar">
          <FileUpload onFileUpload={handleFileUpload} />
          <FileList 
            files={files} 
            onFileSelect={handleFileSelect} 
            onSearchInFile={handleSearchInFile}
            selectedFile={selectedFile}
          />
        </div>
        
        <div className="content">
          <div className="search-controls">
            <SearchBar onSearch={handleSearch} />
            <div className="tabs">
              <button 
                className={`tab-btn ${activeTab === 'files' ? 'active' : ''}`}
                onClick={() => setActiveTab('files')}
              >
                File View
              </button>
              <button 
                className={`tab-btn ${activeTab === 'search' ? 'active' : ''}`}
                onClick={() => setActiveTab('search')}
              >
                Search Results
              </button>
            </div>
          </div>
          
          {loading && <div className="loading">Loading...</div>}
          
          {error && <div className="error-message">{error}</div>}
          
          <div className={`tab-content ${activeTab === 'files' ? 'active' : ''}`}>
            <FileViewer 
              selectedFile={selectedFile} 
              apiUrl={API_URL} 
            />
          </div>
          
          <div className={`tab-content ${activeTab === 'search' ? 'active' : ''}`}>
            <SearchResults 
              results={searchResults}
              onFileSelect={(fileId) => {
                const file = files.find(f => f.id === fileId);
                if (file) {
                  handleFileSelect(file);
                }
              }}
            />
          </div>
        </div>
      </main>
      
      <footer className="app-footer">
        <p>Document Search System &copy; 2025</p>
      </footer>
    </div>
  );
}

export default App;