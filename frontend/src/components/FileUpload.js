import React, { useState } from 'react';
import './FileUpload.css';

const FileUpload = ({ onFileUpload, isLoading }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (selectedFile) {
      onFileUpload(selectedFile);
      setSelectedFile(null);
      // Reset file input
      e.target.reset();
    }
  };

  return (
    <div className="file-upload-container">
      <h2>Upload Files</h2>
      <form 
        onSubmit={handleSubmit}
        onDragEnter={handleDrag}
        className="file-upload-form"
      >
        <div 
          className={`drag-drop-area ${dragActive ? 'active' : ''} ${selectedFile ? 'has-file' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input 
            type="file" 
            id="file-upload" 
            onChange={handleFileChange} 
            accept=".pdf,.jpg,.jpeg,.png,.xlsx,.xls,.csv"
            className="file-input"
          />
          <label htmlFor="file-upload" className="file-label">
            {selectedFile ? (
              <span className="file-name">{selectedFile.name}</span>
            ) : (
              <>
                <img 
                  src="/api/placeholder/64/64" 
                  alt="upload" 
                  className="upload-icon" 
                />
                <span>Drag & drop files here or click to browse</span>
                <span className="file-types">Supported formats: PDF, JPG, PNG, Excel, CSV</span>
              </>
            )}
          </label>
        </div>
        
        <button 
          type="submit" 
          className="upload-button" 
          disabled={!selectedFile || isLoading}
        >
          {isLoading ? 'Uploading...' : 'Upload'}
        </button>
      </form>
    </div>
  );
};

export default FileUpload;