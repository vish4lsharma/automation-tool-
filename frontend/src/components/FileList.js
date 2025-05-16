import React from 'react';
import './FileList.css';

const FileList = ({ files, onFileSelect, onSearchInFile, selectedFile }) => {
  // Helper function to get appropriate icon for file type
  const getFileIcon = (fileType) => {
    switch (fileType) {
      case 'pdf':
        return '📄';
      case 'xlsx':
      case 'xls':
        return '📊';
      case 'csv':
        return '📋';
      case 'jpg':
      case 'jpeg':
      case 'png':
        return '🖼️';
      default:
        return '📁';
    }
  };

  // Helper function to get a more readable file type label
  const getFileTypeLabel = (fileType) => {
    switch (fileType) {
      case 'pdf':
        return 'PDF Document';
      case 'xlsx':
      case 'xls':
        return 'Excel Spreadsheet';
      case 'csv':
        return 'CSV Data';
      case 'jpg':
      case 'jpeg':
      case 'png':
        return 'Image';
      default:
        return fileType.toUpperCase();
    }
  };

  return (
    <div className="file-list">
      <h2>Uploaded Files</h2>
      
      {files.length === 0 ? (
        <div className="no-files">
          <p>No files uploaded yet</p>
          <small>Upload files using the panel above</small>
        </div>
      ) : (
        <ul className="files">
          {files.map(file => (
            <li 
              key={file.id} 
              className={`file-item ${selectedFile && selectedFile.id === file.id ? 'selected' : ''}`}
            >
              <div 
                className="file-info"
                onClick={() => onFileSelect(file)}
              >
                <span className="file-icon">{getFileIcon(file.type)}</span>
                <div className="file-details">
                  <span className="file-name">{file.name}</span>
                  <span className="file-type">{getFileTypeLabel(file.type)}</span>
                </div>
              </div>
              
              <div className="file-actions">
                <button 
                  onClick={() => onFileSelect(file)}
                  className="action-btn view-btn"
                  title="View file content"
                >
                  View
                </button>
                <button 
                  onClick={() => onSearchInFile(file)}
                  className="action-btn search-btn"
                  title="Search in this file"
                >
                  Search
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default FileList;