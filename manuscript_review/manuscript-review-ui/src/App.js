import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min.js';
import './App.css';
import { toast, Toaster } from 'react-hot-toast';
import remarkGfm from 'remark-gfm';

const App = () => {
  const [file, setFile] = useState(null);
  const [manuscriptId, setManuscriptId] = useState(null);
  const [review, setReview] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [reviewStage, setReviewStage] = useState('');
  const controllerRef = useRef(null);
  const [estimatedProgress, setEstimatedProgress] = useState(0);
  const [actualProgress, setActualProgress] = useState(0);
  const progressInterval = useRef(null);
  const startTime = useRef(null);
  const [comparisonReview, setComparisonReview] = useState(null);
  const [isComparing, setIsComparing] = useState(false);
  

  const getBackendURL = () => {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://127.0.0.1:8000';
    } else {
      return `${protocol}//${hostname}`;
    }
  };

/* const getBackendURL = () => {
  // Determine backend URL based on the hostname
  if (window.location.hostname === 'localhost') {
	return 'http://127.0.0.1:8000'; // Local Django backend
  } else {
	return 'http://paper-reviewer.com'; // Production backend
  }
}; */

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
    setUploadProgress(0);
    const backendURL = getBackendURL();
    const response = await axios.post(`${backendURL}/upload/`, formData, {
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploadProgress(percentCompleted);
      },
    });

    // Check if upload was successful
    if (response.data.status === 'success') {
      setManuscriptId(response.data.id);
      alert('Manuscript uploaded successfully!');
    } else {
      throw new Error(response.data.message || 'Upload failed');
    }
  } catch (error) {
    console.error('Error uploading manuscript:', error);
    alert('Failed to upload manuscript.');
  } finally {
    setLoading(false);
    setUploadProgress(0);
  }
};

const reviewStages = {
  'Extracting text and images': 10,
  'Running primary analysis': 30,
  'Processing claims and issues': 60,
  'Generating final review': 80,
  'Complete': 100
};

const startProgressEstimation = () => {
  startTime.current = Date.now();
  const totalDuration = 5 * 60 * 1000; // 5 minutes
  
  progressInterval.current = setInterval(() => {
    const elapsed = Date.now() - startTime.current;
    const estimated = Math.min((elapsed / totalDuration) * 99, 99); // Cap at 99%
    
    setEstimatedProgress(estimated);
  }, 1000);
};

const startComparisonProgress = () => {
  startTime.current = Date.now();
  const totalDuration = 40 * 1000; // 40 seconds
  
  progressInterval.current = setInterval(() => {
    const elapsed = Date.now() - startTime.current;
    const estimated = Math.min((elapsed / totalDuration) * 99, 99); // Cap at 99%
    setActualProgress(estimated);
  }, 1000);
};

const updateActualProgress = async () => {
  try {
    const backendURL = getBackendURL();
    const progressResponse = await axios.get(`${backendURL}/review-progress/${manuscriptId}/`);
    
    // Only update if progress has increased
    if (progressResponse.data.progress > actualProgress) {
      setReviewStage(progressResponse.data.stage);
      setActualProgress(progressResponse.data.progress);
      
      // Update estimated progress to match actual if it's behind
      if (progressResponse.data.progress > estimatedProgress) {
        setEstimatedProgress(progressResponse.data.progress);
      }
    }
    
    if (progressResponse.data.progress >= 100) {
      clearInterval(progressInterval.current);
    }
  } catch (error) {
    console.error('Error fetching progress:', error);
  }
};

const generateReview = async () => {
  if (!manuscriptId) {
    alert('Please upload a manuscript first.');
    return;
  }

  try {
    setLoading(true);
    setReviewStage('Extracting text and images');
    
    const backendURL = getBackendURL();
    startProgressEstimation();
    const response = await axios.get(`${backendURL}/full-review/${manuscriptId}/?include_math=true`);
    
    if (response.data.status === 'success') {
      // Quickly complete progress bar if review finished early
      const elapsed = Date.now() - startTime.current;
      if (elapsed < 5 * 60 * 1000) {
        setEstimatedProgress(100);
      }
      setReview(response.data.full_review);
    } else {
      throw new Error(response.data.error || 'Review generation failed');
    }
  } catch (error) {
    console.error('Error generating review:', error);
    alert(error.message || 'Failed to generate review.');
  } finally {
    clearInterval(progressInterval.current);
    setLoading(false);
  }
};

useEffect(() => {
  const handleKeyPress = (event) => {
    if (event.ctrlKey && event.key === 'c') {
      cancelReviewGeneration();
    }
  };

  document.addEventListener('keydown', handleKeyPress);

  return () => {
    document.removeEventListener('keydown', handleKeyPress);
    if (controllerRef.current) {
      controllerRef.current.abort();
    }
  };
}, []);

const cancelReviewGeneration = () => {
  if (controllerRef.current) {
    controllerRef.current.abort();
    controllerRef.current = null;
    setLoading(false);
    setReviewStage('');
  }
};

const handleNewFileUpload = async () => {
  try {
    setLoading(false);
    setReview('');
    setManuscriptId(null);
    setFile(null);
    setUploadProgress(0);
    setReviewStage('');
    setEstimatedProgress(0);
    setActualProgress(0);
    
    if (progressInterval.current) {
      clearInterval(progressInterval.current);
    }
    
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) fileInput.value = '';
    
    // Call cleanup endpoint
    const backendURL = getBackendURL();
    await axios.post(`${backendURL}/cleanup/`);
  } catch (error) {
    console.error('Error cleaning up:', error);
  }
};

const handleFeedbackSubmit = async (e) => {
  e.preventDefault();
  const email = e.target.email.value;
  const feedback = e.target.feedback.value;
  
  try {
    const backendURL = getBackendURL();
    await axios.post(`${backendURL}/save-feedback/`, {
      email,
      feedback,
      timestamp: new Date().toISOString()
    });
    alert('Thank you for your feedback!');
    e.target.reset();
  } catch (error) {
    console.error('Error saving feedback:', error);
    alert('Failed to save feedback. Please try again.');
  }
};

useEffect(() => {
  const cleanup = async () => {
    try {
      const backendURL = getBackendURL();
      await axios.post(`${backendURL}/cleanup/`);
    } catch (error) {
      console.error('Cleanup failed:', error);
    }
  };

  const handleBeforeUnload = () => {
    if (controllerRef.current) {
      controllerRef.current.abort();
    }
    // Use sendBeacon for cleanup on page unload
    const backendURL = getBackendURL();
    navigator.sendBeacon(`${backendURL}/cleanup/`);
  };

  window.addEventListener('beforeunload', handleBeforeUnload);

  return () => {
    window.removeEventListener('beforeunload', handleBeforeUnload);
    cleanup();
    if (controllerRef.current) {
      controllerRef.current.abort();
    }
  };
}, []);

const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    toast.success('Review copied to clipboard!');
  } catch (err) {
    toast.error('Failed to copy to clipboard');
  }
};

const downloadReview = (text, filename) => {
  try {
    const element = document.createElement('a');
    const file = new Blob([text], { type: 'text/markdown;charset=utf-8' });
    element.href = URL.createObjectURL(file);
    element.download = filename;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
    URL.revokeObjectURL(element.href);
  } catch (err) {
    toast.error('Failed to download review');
  }
};

// Update the progress display
const getProgressStage = (progress) => {
  for (const [stage, threshold] of Object.entries(reviewStages)) {
    if (progress <= threshold) {
      return stage;
    }
  }
  return 'Complete';
};

const generateComparison = async () => {
  try {
    setIsComparing(true);
    setReviewStage('Running GPT-4o comparison');
    setActualProgress(0);
    
    const backendURL = getBackendURL();
    startComparisonProgress();
    const response = await axios.get(`${backendURL}/compare-review/${manuscriptId}/`);
    
    if (response.data.status === 'success') {
      setActualProgress(100);
      setComparisonReview(response.data.comparison_review);
    } else {
      throw new Error(response.data.error || 'Comparison generation failed');
    }
  } catch (error) {
    console.error('Error generating comparison:', error);
    alert(error.message || 'Failed to generate comparison.');
  } finally {
    clearInterval(progressInterval.current);
    setIsComparing(false);
    setReviewStage('Complete');
  }
};

  return (
    <div className="container mt-5">
      <Toaster position="top-right" />
      <h1 className="text-center mb-4">Paper Reviewer AI</h1>
  
      {!manuscriptId ? (
        <div className="upload-container">
          <div className="drag-drop-zone"
            onClick={() => document.getElementById('fileInput').click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const droppedFile = e.dataTransfer.files[0];
              if (droppedFile?.type === 'application/pdf') {
                setFile(droppedFile);
              }
            }}
          >
            <i className="fas fa-cloud-upload-alt upload-icon"></i>
            <p>Click or drag PDF file here to upload</p>
            <input
              id="fileInput"
              type="file"
              accept="application/pdf"
              onChange={handleFileUpload}
              className="file-input"
            />
            {file && <div className="file-name">{file.name}</div>}
          </div>
          
          <div className="progress-container">
            <div className="progress-bar-container">
              <div 
                className="progress-fill"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <div className="progress-text">Uploading: {uploadProgress}%</div>
          </div>
  
          <div className="text-center">
            <button
              className="button"
              onClick={uploadManuscript}
              disabled={!file || loading}
            >
              {loading ? 'Uploading...' : 'Upload Manuscript'}
            </button>
          </div>

          <div className="alert alert-info mt-4">
            <h5>Instructions:</h5>
            <ol>
              <li>Select a PDF file using the file picker above</li>
              <li>Click "Upload PDF" to submit your manuscript</li>
              <li>Wait for the upload to complete</li>
              <li>Once uploaded, click "Generate Review" to analyze your paper</li>
              <li>The AI will provide a detailed review of your manuscript</li>
              <li>The review may take up to 10 minutes to generate for long papers. Please be patient</li>
              <li>After the review is generated, scroll down to the bottom of the page to compare my agentic framework with a single prompt to GPT-4o</li>
            </ol>
            <p className="mb-0"><strong>Note:</strong> Only PDF files are accepted. Maximum paper length is around 100 pages. Maximum file size is 100MB.</p>
          </div>

          <div className="alert alert-warning mt-4">
            <h5>Beta Version Notice</h5>
            <p>Paper Reviewer AI is currently in early beta stage. I would greatly appreciate your feedback to help improve the application.</p>
          </div>

          <div className="card mt-4">
            <div className="card-body">
              <h5 className="card-title">Send Feedback</h5>
              <form onSubmit={handleFeedbackSubmit}>
                <div className="mb-3">
                  <label htmlFor="email" className="form-label">Your Email</label>
                  <input type="email" className="form-control" id="email" />
                </div>
                <div className="mb-3">
                  <label htmlFor="feedback" className="form-label">Your Feedback</label>
                  <textarea className="form-control" id="feedback" rows="3"></textarea>
                </div>
                <button type="submit" className="button">Send Feedback</button>
              </form>
            </div>
          </div>
        </div>
      ) : (
        <div className="review-page">
          <div className="control-buttons mb-4">
            <button
              onClick={generateReview}
              disabled={loading}
              className="button"
            >
              {loading ? (
                <span>
                  Generating
                  <span className="dots-animation">...</span>
                </span>
              ) : (
                'Generate Review'
              )}
            </button>
            
            <button
              onClick={handleNewFileUpload}
              className="button"
            >
              Upload Different File
            </button>
          </div>

          <div className="progress-section">
            {loading && (
              <>
                <div className="progress-container">
                  <div className="progress-label">
                    {reviewStage === 'Extracting text and images' && 'Extracting text and images from manuscript...'}
                    {reviewStage === 'Running primary analysis' && 'Running primary analysis of manuscript content...'}
                    {reviewStage === 'Processing claims and issues' && 'Analyzing claims and potential issues...'}
                    {reviewStage === 'Generating final review' && 'Generating comprehensive review...'}
                    {reviewStage === 'Complete' && 'Review complete!'}
                  </div>
                  <div className="progress">
                    <div 
                      className="progress-bar progress-bar-striped progress-bar-animated"
                      style={{ width: `${isComparing ? actualProgress : estimatedProgress}%` }}
                    ></div>
                  </div>
                  <div className="progress-percentage">
                    {Math.round(isComparing ? actualProgress : estimatedProgress)}%
                  </div>
                </div>

                <button 
                  onClick={cancelReviewGeneration} 
                  className="button button-danger"
                >
                  Cancel Generation
                </button>
              </>
            )}
          </div>

          {/* Display the review if we have one */}
          {review && (
            <div className="card">
              <h3 className="text-center mb-4">Generated Review</h3>
              <div className="review-content markdown-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{review}</ReactMarkdown>
              </div>
              <div className="button-group">
                <button className="button" onClick={(e) => { e.preventDefault(); copyToClipboard(review); }}>
                  <i className="fas fa-copy me-2"></i>Copy to Clipboard
                </button>
                <button className="button" onClick={(e) => { e.preventDefault(); downloadReview(review, 'agentic_review.txt'); }}>
                  <i className="fas fa-download me-2"></i>Download Review
                </button>
              </div>
            </div>
          )}

          {/* Add comparison button and progress bar */}
          {review && !comparisonReview && (
            <div className="comparison-progress-container">
              {isComparing && (
                <div className="progress-section">
                  <div className="progress-bar-container">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${actualProgress}%` }}
                    />
                  </div>
                  <div className="progress-text">
                    {reviewStage} ({Math.round(actualProgress)}%)
                  </div>
                </div>
              )}
              <button
                className="btn btn-primary"
                onClick={generateComparison}
                disabled={isComparing}
              >
                {isComparing ? 'Generating Comparison...' : 'Compare with GPT-4o'}
              </button>
            </div>
          )}

          {/* Add side-by-side display */}
          {review && comparisonReview && (
            <div className="review-comparison">
              <div className="review-column">
                <h3>Agentic Framework</h3>
                <div className="review-content agentic-border markdown-body">
                  <div className="button-container">
                    <button onClick={(e) => { e.preventDefault(); copyToClipboard(review); }}>Copy</button>
                    <button onClick={(e) => { e.preventDefault(); downloadReview(review, 'agentic_review.txt'); }}>Download</button>
                  </div>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{review}</ReactMarkdown>
                </div>
              </div>
              <div className="review-column">
                <h3>GPT-4o Straight Shot</h3>
                <div className="review-content gpt4-border markdown-body">
                  <div className="button-container">
                    <button onClick={(e) => { e.preventDefault(); copyToClipboard(comparisonReview); }}>Copy</button>
                    <button onClick={(e) => { e.preventDefault(); downloadReview(comparisonReview, 'gpt4o_review.txt'); }}>Download</button>
                  </div>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{comparisonReview}</ReactMarkdown>
                </div>
              </div>
            </div>
          )}

        </div>
      )}
  
      <footer className="footer">
        <p>Marc Berghouse, 2025</p>
      </footer>
    </div>
  );
};

export default App;
