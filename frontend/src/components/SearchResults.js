import React from 'react';
import './SearchResults.css';

const SearchResults = ({ results, isLoading }) => {
  if (isLoading) {
    return (
      <div className="search-loading">
        <p>Searching documents...</p>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="no-results">
        <p>No search results to display. Try searching for something.</p>
      </div>
    );
  }

  // Group results by file
  const resultsByFile = results.reduce((acc, result) => {
    if (!acc[result.filename]) {
      acc[result.filename] = [];
    }
    acc[result.filename].push(result);
    return acc;
  }, {});

  return (
    <div className="search-results">
      <div className="results-count">
        <span>{results.length} {results.length === 1 ? 'result' : 'results'} found</span>
      </div>

      {Object.keys(resultsByFile).map((filename) => (
        <div key={filename} className="result-file-group">
          <div className="result-file-header">
            <span className="result-file-icon">
              {getFileIcon(resultsByFile[filename][0].type)}
            </span>
            <span className="result-file-name">{filename}</span>
            <span className="result-count">
              {resultsByFile[filename].length} {resultsByFile[filename].length === 1 ? 'match' : 'matches'}
            </span>
          </div>
          
          <ul className="result-matches">
            {resultsByFile[filename].map((result, index) => (
              <li key={`${result.file_id}-${index}`} className="result-match-item">
                <div className="result-match-preview">{result.preview}</div>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};

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

export default SearchResults;