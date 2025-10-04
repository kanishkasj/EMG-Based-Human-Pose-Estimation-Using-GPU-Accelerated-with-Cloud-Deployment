import React, { useState } from 'react';

function EMGPoseClassifier() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  // API URL configuration - uses environment variable or defaults to localhost
  const API_BASE_URL = process.env.REACT_APP_API_URL;
  // Custom SVG Icons
  const CloudUploadIcon = () => (
    <svg className="h-16 w-16 text-gray-400 hover:text-blue-500 transition-colors duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
    </svg>
  );

  const SparklesIcon = () => (
    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3l3.057 3.943L16 7l-3.943 3.057L12 19l-3.057-3.943L1 15l3.943-3.057L5 3z"/>
    </svg>
  );

  const ChartBarIcon = () => (
    <svg className="h-8 w-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
    </svg>
  );

  const CpuIcon = () => (
    <svg className="h-12 w-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/>
    </svg>
  );

  const BeakerIcon = () => (
    <svg className="h-5 w-5 text-teal-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547A1.934 1.934 0 004 17.5c0 .775.37 1.465.974 1.908l6.652 4.877a2 2 0 002.348 0l6.652-4.877A1.934 1.934 0 0021 17.5c0-.775-.37-1.465-.974-1.908zM11 5h2v7h-2V5zM7 5h2v2H7V5zm8 0h2v2h-2V5z"/>
    </svg>
  );

  const CheckCircleIcon = () => (
    <svg className="h-10 w-10 text-green-600" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
    </svg>
  );

  const WarningIcon = () => (
    <svg className="h-6 w-6 text-red-500 flex-shrink-0 animate-bounce" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
    </svg>
  );

  const StatsIcon = () => (
    <svg className="h-5 w-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
    </svg>
  );

  const ProcessingIcon = () => (
    <svg className="h-5 w-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z"/>
    </svg>
  );

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError(null);
    }
  };

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    setFile(selectedFile);
    setError(null);
    setResult(null);
  };

  const handleSubmit = async () => {
    if (!file) {
      setError('Please select a file first!');
      return;
    }

    setLoading(true);
    setError(null);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 20, 90));
      }, 200);

      const response = await fetch(`${API_BASE_URL}/predict`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      let data;
      try {
        const text = await response.text();
        console.log('Raw response:', text); // Debug log
        data = JSON.parse(text);
      } catch (jsonError) {
        console.error('Failed to parse JSON:', jsonError);
        throw new Error('Server returned invalid response. Backend may be misconfigured.');
      }

      if (!response.ok) {
        throw new Error(data.detail || data.error || 'Prediction failed');
      }
            
      setResult(data);
    } catch (error) {
      console.error('Error:', error);
      setError(error.message || 'Error processing file. Please try again.');
    } finally {
      setLoading(false);
      setTimeout(() => setUploadProgress(0), 1000);
    }
  };

  const resetForm = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setUploadProgress(0);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-teal-50">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-200 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse"></div>
        <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse delay-1000"></div>
        <div className="absolute bottom-1/4 left-1/3 w-96 h-96 bg-teal-200 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse delay-2000"></div>
      </div>

      <div className="relative z-10 container mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-6">
            <div className="bg-gradient-to-r from-blue-500 to-purple-600 p-4 rounded-2xl shadow-lg transform hover:scale-110 transition-transform duration-300">
              <CpuIcon />
            </div>
          </div>
          <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-teal-600 bg-clip-text text-transparent mb-4 animate-fade-in">
            EMG Pose Classifier
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed">
            Upload your EMG signal data and let our AI predict the corresponding pose with 
            <span className="text-purple-600 font-semibold"> advanced machine learning</span>
          </p>
          <div className="flex items-center justify-center mt-6 space-x-6 text-sm text-gray-500">
            <div className="flex items-center space-x-2 hover:text-teal-600 transition-colors duration-300">
              <BeakerIcon />
              <span>CUDA Accelerated</span>
            </div>
            <div className="flex items-center space-x-2 hover:text-purple-600 transition-colors duration-300">
              <ProcessingIcon />
              <span>XGBoost ML</span>
            </div>
            <div className="flex items-center space-x-2 hover:text-blue-600 transition-colors duration-300">
              <StatsIcon />
              <span>Real-time Processing</span>
            </div>
          </div>
        </div>

        {/* Main Card */}
        <div className="max-w-4xl mx-auto">
          <div className="bg-white/80 backdrop-blur-lg rounded-3xl shadow-2xl border border-white/20 p-8 transition-all duration-300 hover:shadow-3xl hover:scale-[1.02]">
            
            {!result ? (
              <div className="space-y-8">
                {/* File Upload Area */}
                <div 
                  className={`relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 cursor-pointer ${
                    dragActive 
                      ? 'border-purple-400 bg-purple-50/50 scale-105 shadow-lg' 
                      : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50/30'
                  }`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => document.getElementById('file-upload').click()}
                >
                  <input
                    type="file"
                    onChange={handleFileChange}
                    className="hidden"
                    id="file-upload"
                    accept=".csv,.hdf5,.h5"
                  />
                  
                  <div className="mb-6">
                    {dragActive ? (
                      <div className="mx-auto h-16 w-16 text-purple-500 scale-110 animate-bounce">
                        <CloudUploadIcon />
                      </div>
                    ) : (
                      <div className="mx-auto h-16 w-16">
                        <CloudUploadIcon />
                      </div>
                    )}
                  </div>
                  <div className="space-y-3">
                    <p className="text-xl font-semibold text-gray-700">
                      {file ? (
                        <span className="text-green-600 flex items-center justify-center space-x-2">
                          <svg className="h-6 w-6 text-green-600 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                          </svg>
                          <span>{file.name}</span>
                        </span>
                      ) : (
                        'Drop your EMG data file here'
                      )}
                    </p>
                    <p className="text-gray-500">
                      or <span className="text-blue-600 font-medium hover:text-purple-600 transition-colors duration-300">click to browse</span>
                    </p>
                    <div className="flex items-center justify-center space-x-4 text-sm text-gray-400 mt-4">
                      <span className="px-3 py-1 bg-gradient-to-r from-blue-100 to-purple-100 text-blue-600 rounded-full transition-all duration-300 hover:scale-110">CSV</span>
                      <span className="px-3 py-1 bg-gradient-to-r from-purple-100 to-teal-100 text-purple-600 rounded-full transition-all duration-300 hover:scale-110">HDF5</span>
                      <span className="px-3 py-1 bg-gradient-to-r from-teal-100 to-blue-100 text-teal-600 rounded-full transition-all duration-300 hover:scale-110">H5</span>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  {loading && uploadProgress > 0 && (
                    <div className="absolute bottom-4 left-4 right-4">
                      <div className="bg-gray-200 rounded-full h-2 overflow-hidden">
                        <div 
                          className="bg-gradient-to-r from-blue-500 via-purple-500 to-teal-500 h-2 rounded-full transition-all duration-500 animate-pulse"
                          style={{ width: `${uploadProgress}%` }}
                        ></div>
                      </div>
                      <p className="text-sm text-purple-600 mt-2 font-medium animate-pulse">Processing... {uploadProgress}%</p>
                    </div>
                  )}
                </div>

                {/* Error Display */}
                {error && (
                  <div className="rounded-xl bg-red-50 border border-red-200 p-4 transform animate-shake">
                    <div className="flex items-center space-x-3">
                      <WarningIcon />
                      <p className="text-red-800 font-medium">{error}</p>
                    </div>
                  </div>
                )}

                {/* Submit Button */}
                <button
                  onClick={handleSubmit}
                  disabled={!file || loading}
                  className={`w-full py-4 px-8 rounded-2xl font-semibold text-lg transition-all duration-300 transform ${
                    !file || loading
                      ? 'bg-gray-200 text-gray-400 cursor-not-allowed opacity-50'
                      : 'bg-gradient-to-r from-blue-500 via-purple-500 to-teal-500 text-white shadow-lg hover:shadow-xl hover:scale-105 active:scale-95 hover:from-blue-600 hover:via-purple-600 hover:to-teal-600'
                  }`}
                >
                  {loading ? (
                    <div className="flex items-center justify-center space-x-3">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
                      <span>Analyzing EMG Signals...</span>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center space-x-3">
                      <SparklesIcon />
                      <span>Predict Pose</span>
                    </div>
                  )}
                </button>
              </div>
            ) : (
              /* Results Display */
              <div className="space-y-8 animate-fade-in">
                <div className="text-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-2xl mb-4 animate-bounce">
                    <CheckCircleIcon />
                  </div>
                  <h2 className="text-3xl font-bold text-gray-900 mb-2">Prediction Complete!</h2>
                  <p className="text-gray-600">Your EMG data has been successfully analyzed</p>
                </div>

                <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-2xl p-8 border border-blue-100 shadow-inner">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
                    <div className="space-y-6">
                      <div className="flex items-center space-x-4">
                        <div className="bg-gradient-to-r from-purple-500 to-blue-500 p-3 rounded-xl">
                          <ChartBarIcon />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">Predicted Class</p>
                          <p className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                            {result.predicted_class}
                          </p>
                        </div>
                      </div>
                      
                      <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-100">
                        <h3 className="text-lg font-semibold text-gray-700 mb-4 flex items-center space-x-2">
                          <BeakerIcon />
                          <span>Analysis Details</span>
                        </h3>
                        <div className="space-y-3 text-sm text-gray-600">
                          <div className="flex justify-between items-center">
                            <span>Confidence:</span>
                            <span className="font-medium text-green-600">{(result.confidence * 100).toFixed(1)}%</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span>Windows Analyzed:</span>
                            <span className="font-medium text-purple-600">{result.total_windows}</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span>Processing Mode:</span>
                            <span className="font-medium text-blue-600">
                              {result.processing_info?.cuda_used ? 'CUDA GPU' : 'CPU'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {result.pose_image && (
                      <div className="text-center">
                        <p className="text-sm font-medium text-gray-500 mb-4 uppercase tracking-wide">Pose Visualization</p>
                        <div className="relative group">
                          <img 
                            src={`${API_BASE_URL}${result.pose_image}`}
                            alt="Predicted Pose"
                            className="w-full max-w-sm mx-auto rounded-2xl shadow-lg border-4 border-white transition-transform duration-300 group-hover:scale-105"
                          />
                          <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex justify-center space-x-4">
                  <button
                    onClick={resetForm}
                    className="px-8 py-3 bg-gradient-to-r from-gray-500 to-gray-600 text-white rounded-xl font-semibold transition-all duration-300 hover:shadow-lg hover:scale-105 active:scale-95"
                  >
                    Analyze Another File
                  </button>
                  <button
                    onClick={() => window.location.reload()}
                    className="px-8 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl font-semibold transition-all duration-300 hover:shadow-lg hover:scale-105 active:scale-95"
                  >
                    Start Over
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer Info */}
        <div className="text-center mt-12 text-gray-500 text-sm">
          <p className="hover:text-gray-700 transition-colors duration-300">
            Powered by advanced machine learning algorithms and CUDA acceleration
          </p>
          <p className="text-xs mt-2 text-gray-400">
            Connected to: {API_BASE_URL}
          </p>
        </div>
      </div>

      <style jsx>{`
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          10%, 30%, 50%, 70%, 90% { transform: translateX(-2px); }
          20%, 40%, 60%, 80% { transform: translateX(2px); }
        }
        
        .animate-fade-in {
          animation: fade-in 0.6s ease-out forwards;
        }
        
        .animate-shake {
          animation: shake 0.5s ease-in-out;
        }
      `}</style>
    </div>
  );
}

export default EMGPoseClassifier;