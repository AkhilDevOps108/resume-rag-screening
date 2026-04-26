import React, { useRef, useState } from 'react';
import './DocumentUpload.css';

function DocumentUpload({ onDocumentsUploaded }) {
  const fileInputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

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
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
  };

  const handleBrowseClick = () => {
    if (!uploading) {
      fileInputRef.current?.click();
    }
  };

  const handleDropZoneKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleBrowseClick();
    }
  };

  const handleFiles = (fileList) => {
    const newFiles = Array.from(fileList).filter(file => {
      const ext = file.name.split('.').pop().toLowerCase();
      return ['pdf', 'txt', 'md', 'markdown'].includes(ext);
    });
    setFiles(prev => [...prev, ...newFiles]);
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setProgress(0);

    try {
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });

      const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        await response.json();
        setProgress(100);
        setTimeout(() => {
          onDocumentsUploaded();
        }, 500);
      } else {
        let errorMessage = 'Upload failed. Please try again.';

        try {
          const errorData = await response.json();
          if (errorData?.detail) {
            errorMessage = `Upload failed: ${errorData.detail}`;
          }
        } catch {
          // Keep generic message if server response is not JSON.
        }

        alert(errorMessage);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Error uploading documents');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-container">
      <div className="upload-content">
        <h2>📤 Upload Documents</h2>
        <p>Add PDF, TXT, or Markdown files to build your knowledge base</p>

        <div
          className={`drop-zone ${dragActive ? 'active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={handleBrowseClick}
          onKeyDown={handleDropZoneKeyDown}
          role="button"
          tabIndex={0}
        >
          <div className="drop-icon">📁</div>
          <h3>Drag and drop files here</h3>
          <p>or click to select files</p>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleChange}
            accept=".pdf,.txt,.md,.markdown"
            className="file-input"
          />
        </div>

        {files.length > 0 && (
          <div className="files-list">
            <h3>Selected Files ({files.length})</h3>
            <ul>
              {files.map((file, index) => (
                <li key={index}>
                  <span className="file-name">📄 {file.name}</span>
                  <span className="file-size">({(file.size / 1024).toFixed(2)} KB)</span>
                  <button
                    className="remove-btn"
                    onClick={() => removeFile(index)}
                    disabled={uploading}
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {uploading && (
          <div className="progress-bar-container">
            <div className="progress-bar" style={{ width: `${progress}%` }}></div>
            <p className="progress-text">Uploading and processing documents...</p>
          </div>
        )}

        {!uploading && files.length > 0 && (
          <button
            className="upload-btn"
            onClick={handleUpload}
          >
            Upload & Process
          </button>
        )}

        {!uploading && files.length === 0 && (
          <div className="info-box">
            <h4>💡 Supported Formats</h4>
            <ul>
              <li>PDF (.pdf)</li>
              <li>Text (.txt)</li>
              <li>Markdown (.md, .markdown)</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default DocumentUpload;
