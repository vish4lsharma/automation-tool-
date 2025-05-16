import React from 'react';
import './SearchResults.css';

const SearchResults = ({ results, onFileSelect }) => {
  // Helper function to group results by file
  const groupResultsByFile = () => {
    const groupedResults = {};
    
    results.forEach(result => {
      const fileId = result.file_id;
      
      if (!groupedResults[fileId]) {
        groupedResults[fileId] = {
          id: fileId,
          filename: result.filename,
          type: result.type,
          matches: []
        };
      }
      
      groupedResults[fileId].matches.push(result);
    });
    
    return Object.values(groupedResults);
  };

  // Get file type icon
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

  const groupedResults = groupResultsByFile();

  if (results.length === 0) {
    return (
      <div className="search-results empty">
        <div className="no-results">
          <p>No search results to display</p>
          <small>Try searching for something in your uploaded files</small>
        </div>
      </div>
    );
  }

  return (
    <div className="search-results">
      <h2>Search Results ({results.length} matches found)</h2>
      
      {groupedResults.map(fileGroup => (
        <div key={fileGroup.id} className="result-group">
          <div className="file-header">
            <div className="file-info">
              <span className="file-icon">{getFileIcon(fileGroup.type)}</span>
              <span className="file-name">{fileGroup.filename}</span>
            </div>
            <button 
              className="view-file-btn"
              onClick={() => onFileSelect(fileGroup.id)}
            >
              View Full File
            </button>
          </div>
          
          <div className="matches">
            {fileGroup.matches.map((match, index) => (
              <div key={index} className="match-item">
                <div className="match-preview">
                  <p>{match.preview}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default SearchResults;