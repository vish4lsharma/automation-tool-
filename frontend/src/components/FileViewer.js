import React, { useState, useEffect } from 'react';
import './FileViewer.css';

const FileViewer = ({ selectedFile, apiUrl }) => {
  const [fileContent, setFileContent] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [debugInfo, setDebugInfo] = useState(null);

  // Fetch debug info when component mounts
  useEffect(() => {
    const fetchDebugInfo = async () => {
      try {
        const response = await fetch(`${apiUrl}/debug/files`);
        if (response.ok) {
          const data = await response.json();
          setDebugInfo(data);
          console.log('Debug info:', data);
        }
      } catch (err) {
        console.error('Error fetching debug info:', err);
      }
    };

    fetchDebugInfo();
  }, [apiUrl]);

  useEffect(() => {
    if (!selectedFile) {
      setFileContent(null);
      return;
    }

    const fetchFileContent = async () => {
      setLoading(true);
      setError(null);
      
      try {
        console.log(`Fetching content for file ID: ${selectedFile.id}`);
        console.log(`Full selected file info:`, selectedFile);

        // ✅ CHANGED TO USE THE SEARCH-STYLE URL
        const response = await fetch(`${apiUrl}/file-content?file_id=${selectedFile.id}`);
        
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Failed to fetch file content: ${response.statusText} (${response.status}). Server message: ${errorText}`);
        }

        const data = await response.json();
        console.log('Received file content:', data);
        setFileContent(data);
      } catch (err) {
        console.error('Error fetching file content:', err);
        setError(`Failed to load file content: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    fetchFileContent();
  }, [selectedFile, apiUrl]);

  const renderFileContent = () => {
    if (!fileContent) return null;

    switch (selectedFile.type.toLowerCase()) {
      case 'pdf':
        return (
          <div className="pdf-content">
            <h3>PDF Text Content:</h3>
            <div className="text-content">{fileContent.content}</div>
          </div>
        );
      
      case 'image':
      case 'png':
      case 'jpg':
      case 'jpeg':
        return (
          <div className="image-content">
            <h3>Image OCR Text:</h3>
            <div className="image-container">
              <img 
                src={`${apiUrl}/files/${selectedFile.id}/raw`} 
                alt="Uploaded content" 
                className="preview-image" 
              />
            </div>
            <div className="text-content">{fileContent.content}</div>
          </div>
        );
      
      case 'excel':
      case 'xlsx':
      case 'xls':
      case 'csv':
        return (
          <div className="table-content">
            <h3>Spreadsheet Data:</h3>
            {fileContent.sheets && Object.keys(fileContent.sheets).map(sheetName => (
              <div key={sheetName} className="sheet-container">
                <h4>Sheet: {sheetName}</h4>
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead>
                      {fileContent.sheets[sheetName].columns && (
                        <tr>
                          {fileContent.sheets[sheetName].columns.map((col, idx) => (
                            <th key={idx}>{col}</th>
                          ))}
                        </tr>
                      )}
                    </thead>
                    <tbody>
                      {fileContent.sheets[sheetName].data && 
                        fileContent.sheets[sheetName].data.map((row, rowIdx) => (
                          <tr key={rowIdx}>
                            {row.map((cell, cellIdx) => (
                              <td key={cellIdx}>{cell !== null ? cell.toString() : ''}</td>
                            ))}
                          </tr>
                        ))
                      }
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        );
      
      default:
        return <div>No preview available for this file type: {selectedFile.type}</div>;
    }
  };

  return (
    <div className="file-viewer">
      {selectedFile && (
        <div className="file-content-container">
          <h2>File Content: {selectedFile.name}</h2>
          <div className="file-info">
            <p><strong>File ID:</strong> {selectedFile.id}</p>
            <p><strong>File Type:</strong> {selectedFile.type}</p>
          </div>
          
          {loading && <div className="loading">Loading file content...</div>}
          
          {error && (
            <div className="error-message">
              <p>{error}</p>
              <p>Please ensure the backend server is running and the file is properly uploaded.</p>
              <div className="debug-actions">
                <button 
                  onClick={() => window.location.reload()} 
                  className="debug-button"
                >
                  Reload Page
                </button>
              </div>
            </div>
          )}
          
          {!loading && !error && renderFileContent()}
        </div>
      )}
      
      {!selectedFile && (
        <div className="no-file-selected">
          <p>Select a file from the list to view its content</p>
        </div>
      )}

      {debugInfo && (
        <div className="debug-info" style={{ marginTop: '20px', padding: '10px', backgroundColor: '#f5f5f5', border: '1px solid #ddd' }}>
          <h3>Debug Information</h3>
          <p>Files in storage: {debugInfo.file_count}</p>
          <ul>
            {Object.entries(debugInfo.files || {}).map(([id, info]) => (
              <li key={id}>
                ID: {id.substring(0, 8)}... - {info.filename} ({info.exists ? '✅' : '❌'})
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default FileViewer;
