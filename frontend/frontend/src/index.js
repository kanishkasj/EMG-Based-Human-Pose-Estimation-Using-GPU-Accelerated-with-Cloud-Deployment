
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';  // This imports Tailwind CSS
import EMGPoseClassifier from './components/EMGPoseClassifier';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <EMGPoseClassifier />
  </React.StrictMode>
);