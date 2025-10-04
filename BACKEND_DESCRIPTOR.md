# Backend of Real-Time EMG Pose Estimation API

Efficient real-time pose estimation from EMG data requires fast processing, accurate inference, and reliable access via the cloud. The backend delivers this by managing all API logic, data handling, and model inference through a GPU-accelerated service.

---

## Overview

- Provides a FastAPI-based REST API for health checks, file uploads, and prediction.
- Handles preprocessing of EMG and joint angle data with optimized filtering, normalization, and segmentation.
- Loads and serves predictions from trained models, using both CPU and CUDA acceleration.
- Containerized using Docker for seamless deployment on GPU-enabled cloud infrastructure.

---

## Objectives

- Receive, validate, and preprocess incoming data files.
- Apply feature extraction and custom CUDA routines for efficient computation.
- Expose the trained model as a `/predict` endpoint for fast, accurate pose estimation.
- Monitor and manage service health and status as a production-ready cloud microservice.

---

## System Workflow

1. **API Request Handling**
    - Accepts data from clients, securely storing and validating all inputs.

2. **Feature Extraction & Preprocessing**
    - EMG signals are filtered, normalized, segmented, and transformed for inference.

3. **Prediction Pipeline**
    - Runs rapid, GPU-powered inference using preloaded models, returning results via API.

4. **Service Management**
    - Offers endpoints for health and model info, enabling robust monitoring and maintenance.

---

## File Descriptions

- `main.py` &mdash; FastAPI application implementing the core backend logic, API endpoints, and inference routines.
- `requirements.txt` &mdash; Lists all Python dependencies needed to run the backend service.
- `dockerfile` &mdash; Instructions for building the Docker image to containerize and deploy the backend.
- `deploy.sh` &mdash; Shell script automating deployment tasks for the backend.
- `file.dockerignore` &mdash; Specifies files and folders to exclude from the Docker build context.
- `emg_classifier.pkl` &mdash; Pre-trained machine learning model (saved with pickle) used for EMG pose prediction inference.
---
