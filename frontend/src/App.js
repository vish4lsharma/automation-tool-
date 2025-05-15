import React, { useState, useEffect } from 'react';
import './App.css';
import FileUpload from './components/FileUpload';
import FileList from './components/FileList';
import SearchBar from './components/SearchBar';
import SearchResults from './components/SearchResults';

function App() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Fetch existing files when component mounts
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/files');
      if (!response.ok) {
        throw new Error('Failed to fetch files');
      }
      const data = await response.json();
      setFiles(data);
    } catch (err) {
      setError('Error fetching files: ' + err.message);
    }
  };

  const handleFileUpload = async (file) => {
    setIsLoading(true);
    setError('');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('http://localhost:5000/api/upload', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Upload failed');
      }
      
      const data = await response.json();
      setFiles([...files, data]);
      setIsLoading(false);
    } catch (err) {
      setError('Error uploading file: ' + err.message);
      setIsLoading(false);
    }
  };

  const handleSearch = async (query) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    
    setIsLoading(true);
    setError('');
    
    try {
      let url = `http://localhost:5000/api/search?query=${encodeURIComponent(query)}`;
      
      if (selectedFile) {
        url += `&file_id=${selectedFile.id}`;
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Search failed');
      }
      
      const data = await response.json();
      setSearchResults(data.results);
      setIsLoading(false);
    } catch (err) {
      setError('Error searching: ' + err.message);
      setIsLoading(false);
    }
  };

  const handleFileSelect = (file) => {
    setSelectedFile(file === selectedFile ? null : file);
    setSearchResults([]);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Document Search System</h1>
      </header>
      <main className="App-main">
        <div className="container">
          <FileUpload onFileUpload={handleFileUpload} isLoading={isLoading} />
          
          <div className="search-container">
            <SearchBar onSearch={handleSearch} isLoading={isLoading} />
            {selectedFile && (
              <div className="selected-file">
                Searching in: {selectedFile.filename}
                <button onClick={() => setSelectedFile(null)}>Clear Selection</button>
              </div>
            )}
          </div>
          
          {error && <div className="error-message">{error}</div>}
          
          <div className="content-container">
            <div className="file-list-container">
              <h2>Uploaded Files</h2>
              <FileList 
                files={files} 
                onFileSelect={handleFileSelect} 
                selectedFile={selectedFile} 
              />
            </div>
            
            <div className="search-results-container">
              <h2>Search Results</h2>
              <SearchResults results={searchResults} isLoading={isLoading} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;