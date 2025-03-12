import React, { useState } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { dracula } from 'react-syntax-highlighter/dist/esm/styles/prism';

const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

const App = () => {
  const [file, setFile] = useState(null);
  const [manuscriptId, setManuscriptId] = useState(null);
  const [review, setReview] = useState('');
  const [loading, setLoading] = useState(false);

  const handleFileUpload = (e) => {
    setFile(e.target.files[0]);
  };

  const uploadManuscript = async () => {
    if (!file) {
      alert('Please select a PDF file.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      setLoading(true);
      const response = await axios.post(`${API_URL}/upload/`, formData);
      setManuscriptId(response.data.id);
      alert('Manuscript uploaded successfully!');
    } catch (error) {
      console.error('Error uploading manuscript:', error);
      alert('Failed to upload manuscript.');
    } finally {
      setLoading(false);
    }
  };

  const generateReview = async () => {
    if (!manuscriptId) {
      alert('Please upload a manuscript first.');
      return;
    }

    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/full-review/${manuscriptId}/?include_math=true`);
      setReview(response.data.full_review);
    } catch (error) {
      console.error('Error generating review:', error);
      alert('Failed to generate review.');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(review);
    alert('Review copied to clipboard!');
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.header}>Manuscript Review</h1>

      {!manuscriptId && (
        <div style={styles.uploadContainer}>
          <input type="file" accept="application/pdf" onChange={handleFileUpload} />
          <button onClick={uploadManuscript} style={styles.button}>
            {loading ? 'Uploading...' : 'Upload Manuscript'}
          </button>
        </div>
      )}

      {manuscriptId && !review && (
        <button onClick={generateReview} style={styles.button}>
          {loading ? 'Generating Review...' : 'Generate Review'}
        </button>
      )}

      {review && (
        <div style={styles.reviewContainer}>
          <h2>Generated Review</h2>
          <ReactMarkdown
            children={review}
            components={{
              code({ node, inline, className, children, ...props }) {
                return !inline ? (
                  <SyntaxHighlighter style={dracula} language="markdown" PreTag="div" {...props}>
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code {...props}>{children}</code>
                );
              },
            }}
          />
          <button onClick={copyToClipboard} style={styles.copyButton}>
            Copy to Clipboard
          </button>
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    fontFamily: 'Arial, sans-serif',
    padding: '20px',
    maxWidth: '800px',
    margin: 'auto',
    textAlign: 'center',
  },
  header: {
    fontSize: '2em',
    marginBottom: '20px',
    color: '#333',
  },
  uploadContainer: {
    margin: '20px 0',
  },
  button: {
    padding: '10px 20px',
    fontSize: '16px',
    backgroundColor: '#007BFF',
    color: '#FFF',
    border: 'none',
    borderRadius: '5px',
    cursor: 'pointer',
    marginTop: '10px',
  },
  buttonDisabled: {
    backgroundColor: '#CCC',
    cursor: 'not-allowed',
  },
  reviewContainer: {
    textAlign: 'left',
    marginTop: '20px',
    backgroundColor: '#F9F9F9',
    padding: '15px',
    borderRadius: '5px',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
  },
  copyButton: {
    padding: '10px 20px',
    fontSize: '16px',
    backgroundColor: '#28A745',
    color: '#FFF',
    border: 'none',
    borderRadius: '5px',
    cursor: 'pointer',
    marginTop: '10px',
  },
};

export default App;
