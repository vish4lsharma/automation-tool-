import React from 'react';
import './FileList.css';

const FileList = ({ files, onFileSelect, selectedFile }) => {
  // Function to determine file icon based on file type
  const getFileIcon = (fileType) => {
    switch (fileType.toLowerCase()) {
      case 'pdf':
        return '📄';
      case 'xlsx':
      case 'xls':
      case 'csv':
        return '📊';
      case 'jpg':
      case 'jpeg':
      case 'png':
        return '🖼️';
      default:
        return '📁';
    }
  };

  if (files.length === 0) {
    return (
      <div className="empty-file-list">
        <p>No files uploaded yet. Upload a file to get started.</p>
      </div>
    );
  }

  return (
    <ul className="file-list">
      {files.map((file) => (
        <li 
          key={file.id} 
          className={`file-item ${selectedFile && selectedFile.id === file.id ? 'selected' : ''}`}
          onClick={() => onFileSelect(file)}
        >
          <span className="file-icon">{getFileIcon(file.type)}</span>
          <div className="file-details">
            <span className="file-name">{file.filename}</span>
            <span className="file-type">{file.type.toUpperCase()}</span>
          </div>
        </li>
      ))}
    </ul>
  );
};

export default FileList;