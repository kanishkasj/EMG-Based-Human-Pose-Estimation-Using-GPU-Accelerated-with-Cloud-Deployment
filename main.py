from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import pickle
import os
import tempfile
import h5py
import logging
from pathlib import Path
from collections import Counter
import traceback

# CUDA imports - Fixed to handle missing CUDA gracefully
try:
    import cupy as cp
    from numba import cuda, float32
    CUDA_AVAILABLE = True
    print("CUDA available for FastAPI")
except ImportError:
    CUDA_AVAILABLE = False
    cp = None
    cuda = None
    print("Warning: CUDA not available, using CPU fallback")

# Initialize FastAPI app
app = FastAPI(
    title="EMG Pose Classifier API", 
    version="1.0.0",
    description="CUDA-accelerated EMG pose classification API"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths - Updated to match your project structure
MODEL_PATH = Path("models/emg_classifier.pkl")  # Your trained model
EXCEL_PATH = Path("data/label_image.xlsx")      # Optional: pose image mapping
STATIC_PATH = Path("static")                    # Optional: pose images

# Mount static files if they exist
if STATIC_PATH.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")

# Global variables
model_package = None
label_mapping = None

# CUDA Kernels - Only define if CUDA is available
if CUDA_AVAILABLE:
    @cuda.jit
    def optimized_sliding_window_kernel(input_data, output_windows, window_size, step_size, n_channels, n_samples):
        thread_id = cuda.threadIdx.x + cuda.blockIdx.x * cuda.blockDim.x
        n_windows = (n_samples - window_size) // step_size + 1
        total_operations = n_windows * n_channels
        
        if thread_id >= total_operations:
            return
        
        window_idx = thread_id // n_channels
        channel_idx = thread_id % n_channels
        start_pos = window_idx * step_size
        
        for sample_idx in range(window_size):
            input_idx = start_pos + sample_idx
            if input_idx < n_samples:
                output_windows[window_idx, channel_idx, sample_idx] = input_data[input_idx, channel_idx]

    @cuda.jit
    def advanced_feature_extraction_kernel(window_data, feature_output, n_windows, n_channels, window_size):
        thread_id = cuda.threadIdx.x + cuda.blockIdx.x * cuda.blockDim.x
        total_operations = n_windows * n_channels
        if thread_id >= total_operations:
            return
        
        window_idx = thread_id // n_channels
        channel_idx = thread_id % n_channels
        
        sum_val = 0.0
        sum_squares = 0.0
        sum_abs = 0.0
        min_val = float('inf')
        max_val = float('-inf')
        
        for i in range(window_size):
            val = window_data[window_idx, channel_idx, i]
            sum_val += val
            sum_squares += val * val
            sum_abs += abs(val) if val >= 0 else -val
            if val < min_val:
                min_val = val
            if val > max_val:
                max_val = val
        
        mean_val = sum_val / window_size
        variance = (sum_squares / window_size) - (mean_val * mean_val)
        rms_val = (sum_squares / window_size) ** 0.5 if sum_squares > 0.0 else 0.0
        std_val = variance ** 0.5 if variance > 0.0 else 0.0
        mav_val = sum_abs / window_size
        
        zero_crossings = 0.0
        slope_changes = 0.0
        
        for i in range(1, window_size):
            current_val = window_data[window_idx, channel_idx, i]
            prev_val = window_data[window_idx, channel_idx, i-1]
            
            if (current_val >= 0 and prev_val < 0) or (current_val < 0 and prev_val >= 0):
                zero_crossings += 1.0
            
            if i > 1:
                prev_prev_val = window_data[window_idx, channel_idx, i-2]
                current_slope = current_val - prev_val
                prev_slope = prev_val - prev_prev_val
                if (current_slope > 0 and prev_slope <= 0) or (current_slope <= 0 and prev_slope > 0):
                    slope_changes += 1.0
        
        waveform_length = 0.0
        for i in range(1, window_size):
            waveform_length += abs(window_data[window_idx, channel_idx, i] - 
                                window_data[window_idx, channel_idx, i-1])
        
        n_features_per_channel = 8
        feature_base_idx = (window_idx * n_channels + channel_idx) * n_features_per_channel
        
        feature_output[feature_base_idx + 0] = mean_val
        feature_output[feature_base_idx + 1] = rms_val
        feature_output[feature_base_idx + 2] = std_val
        feature_output[feature_base_idx + 3] = mav_val
        feature_output[feature_base_idx + 4] = max_val - min_val
        feature_output[feature_base_idx + 5] = zero_crossings
        feature_output[feature_base_idx + 6] = slope_changes
        feature_output[feature_base_idx + 7] = waveform_length

def process_data_cpu_exact_match(data, window_size, step_size):
    """CPU fallback - exact same processing as training"""
    n_samples, n_channels = data.shape
    n_windows = max(1, (n_samples - window_size) // step_size + 1)
    
    if n_samples < window_size:
        # Single window processing
        features = []
        for ch in range(n_channels):
            channel_data = data[:, ch]
            features.extend([
                np.mean(channel_data),                           # mean
                np.sqrt(np.mean(channel_data**2)),              # rms
                np.std(channel_data),                           # std
                np.mean(np.abs(channel_data)),                  # mav
                np.max(channel_data) - np.min(channel_data),    # range
                0.0,                                            # zero_crossings
                0.0,                                            # slope_changes
                np.sum(np.abs(np.diff(channel_data)))          # waveform_length
            ])
        return np.array(features).reshape(1, -1)
    
    # Multi-window processing
    all_features = []
    for window_idx in range(n_windows):
        start_idx = window_idx * step_size
        end_idx = min(start_idx + window_size, n_samples)
        
        window_features = []
        for ch in range(n_channels):
            window_data = data[start_idx:end_idx, ch]
            
            # Exact same 8 features as CUDA version
            mean_val = np.mean(window_data)
            rms_val = np.sqrt(np.mean(window_data**2))
            std_val = np.std(window_data)
            mav_val = np.mean(np.abs(window_data))
            range_val = np.max(window_data) - np.min(window_data)
            
            # Zero crossings
            zero_crossings = sum(1 for i in range(1, len(window_data)) 
                               if (window_data[i] >= 0) != (window_data[i-1] >= 0))
            
            # Slope changes
            slope_changes = 0
            if len(window_data) > 2:
                slope_changes = sum(1 for i in range(2, len(window_data))
                                  if ((window_data[i] - window_data[i-1]) > 0) != 
                                     ((window_data[i-1] - window_data[i-2]) > 0))
            
            # Waveform length
            waveform_length = np.sum(np.abs(np.diff(window_data)))
            
            window_features.extend([
                mean_val, rms_val, std_val, mav_val, 
                range_val, zero_crossings, slope_changes, waveform_length
            ])
        
        all_features.append(window_features)
    
    return np.array(all_features)

def process_data_cuda_exact_match(data, window_size, step_size):
    """Process data using CUDA - exact same as training"""
    if not CUDA_AVAILABLE:
        return process_data_cpu_exact_match(data, window_size, step_size)
    
    n_samples, n_channels = data.shape
    n_windows = (n_samples - window_size) // step_size + 1
    
    if n_windows <= 0:
        return process_data_cpu_exact_match(data, window_size, step_size)
    
    try:
        # GPU processing
        data_gpu = cp.asarray(data, dtype=cp.float32)
        windows_gpu = cp.zeros((n_windows, n_channels, window_size), dtype=cp.float32)
        
        # CUDA configuration
        total_threads = n_windows * n_channels
        threads_per_block = min(total_threads, 1024)
        blocks_per_grid = (total_threads + threads_per_block - 1) // threads_per_block
        
        # Extract windows
        optimized_sliding_window_kernel[blocks_per_grid, threads_per_block](
            data_gpu, windows_gpu, window_size, step_size, n_channels, n_samples
        )
        cuda.synchronize()
        
        # Extract features
        n_features_per_channel = 8
        total_features = n_windows * n_channels * n_features_per_channel
        features_gpu = cp.zeros(total_features, dtype=cp.float32)
        
        advanced_feature_extraction_kernel[blocks_per_grid, threads_per_block](
            windows_gpu, features_gpu, n_windows, n_channels, window_size
        )
        cuda.synchronize()
        
        # Return to CPU
        features = features_gpu.reshape(n_windows, n_channels * n_features_per_channel)
        result = cp.asnumpy(features)
        
        # Cleanup GPU memory
        cp._default_memory_pool.free_all_blocks()
        
        return result
        
    except Exception as e:
        logger.warning(f"CUDA processing failed: {e}, falling back to CPU")
        return process_data_cpu_exact_match(data, window_size, step_size)

def load_model_and_mapping():
    """Load model and optional label mapping on startup"""
    global model_package, label_mapping
    
    try:
        # Load model
        if MODEL_PATH.exists():
            logger.info(f"Loading model from: {MODEL_PATH}")
            with open(MODEL_PATH, 'rb') as f:
                model_package = pickle.load(f)
            logger.info(f"Model loaded successfully")
            logger.info(f"Classes: {model_package.get('class_names', 'Unknown')}")
            
            # Log model components
            components = ['model', 'scaler', 'label_encoder', 'emg_columns', 'angle_columns']
            for comp in components:
                status = "✓" if comp in model_package else "✗"
                logger.info(f"  {comp}: {status}")
                
            # Check for feature selector
            if 'feature_selector' in model_package:
                logger.info("  feature_selector: ✓")
            else:
                logger.warning("  feature_selector: ✗ (this might cause issues)")
        else:
            raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
        
        # Load optional label mapping for pose images
        if EXCEL_PATH.exists():
            try:
                label_mapping = pd.read_excel(EXCEL_PATH)
                logger.info(f"Label mapping loaded: {len(label_mapping)} entries")
            except Exception as e:
                logger.warning(f"Could not load label mapping: {e}")
                label_mapping = None
        else:
            logger.info("No label mapping file found (optional)")
            label_mapping = None
            
    except Exception as e:
        logger.error(f"Critical error loading model: {e}")
        traceback.print_exc()
        model_package = None
        label_mapping = None

def predict_pose(emg_data, angle_data):
    """Main prediction function"""
    if model_package is None:
        raise ValueError("Model not loaded")
    
    logger.info(f"Input EMG data: {emg_data.shape}")
    logger.info(f"Input Angle data: {angle_data.shape}")
    
    # Get processing parameters
    params = model_package['preprocessing_params']
    window_size = int(params['window_size_ms'] * params['sampling_rate'] / 1000)
    step_size = int(params['step_size_ms'] * params['sampling_rate'] / 1000)
    
    logger.info(f"Processing params: window={window_size}, step={step_size}")
    
    # Process EMG data
    emg_features = process_data_cuda_exact_match(emg_data.astype(np.float32), window_size, step_size)
    logger.info(f"EMG features extracted: {emg_features.shape}")
    
    # Process Angle data
    angle_features = process_data_cuda_exact_match(angle_data.astype(np.float32), window_size, step_size)
    logger.info(f"Angle features extracted: {angle_features.shape}")
    
    # Check expected feature counts from model
    expected_total_features = model_package['scaler'].n_features_in_
    expected_emg_features = len(model_package['emg_columns']) * 8  # 8 features per channel
    expected_angle_features = expected_total_features - expected_emg_features
    
    logger.info(f"Expected features: EMG={expected_emg_features}, Angle={expected_angle_features}, Total={expected_total_features}")
    logger.info(f"Actual features: EMG={emg_features.shape[1]}, Angle={angle_features.shape[1]}, Total={emg_features.shape[1] + angle_features.shape[1]}")
    
    # Trim features to match training if needed
    if emg_features.shape[1] != expected_emg_features:
        logger.warning(f"EMG feature mismatch! Trimming from {emg_features.shape[1]} to {expected_emg_features}")
        emg_features = emg_features[:, :expected_emg_features]
    
    if angle_features.shape[1] != expected_angle_features:
        logger.warning(f"Angle feature mismatch! Trimming from {angle_features.shape[1]} to {expected_angle_features}")
        angle_features = angle_features[:, :expected_angle_features]
    
    # Combine features
    min_windows = min(emg_features.shape[0], angle_features.shape[0])
    emg_features = emg_features[:min_windows]
    angle_features = angle_features[:min_windows]
    
    combined_features = np.concatenate([emg_features, angle_features], axis=1)
    logger.info(f"Final combined features: {combined_features.shape}")
    
    # Final check
    if combined_features.shape[1] != expected_total_features:
        raise ValueError(f"Feature count mismatch: got {combined_features.shape[1]}, expected {expected_total_features}")
    
    # Apply scaling
    scaler = model_package['scaler']
    features_scaled = scaler.transform(combined_features)
    logger.info(f"Scaled features: {features_scaled.shape}")
    
    # Apply feature selection (CRITICAL!)
    feature_selector = model_package.get('feature_selector')
    if feature_selector is not None:
        features_final = feature_selector.transform(features_scaled)
        logger.info(f"Features after selection: {features_final.shape}")
    else:
        features_final = features_scaled
        logger.warning("No feature selector found - this might cause prediction issues!")
    
    # Make predictions
    model = model_package['model']
    label_encoder = model_package['label_encoder']
    
    predictions_encoded = model.predict(features_final)
    predictions = label_encoder.inverse_transform(predictions_encoded)
    predictions_proba = model.predict_proba(features_final)
    
    confidence_scores = np.max(predictions_proba, axis=1)
    
    # Calculate statistics
    pred_counts = Counter(predictions)
    most_common = pred_counts.most_common(1)[0][0]
    max_conf_idx = np.argmax(confidence_scores)
    most_confident = predictions[max_conf_idx]
    
    logger.info(f"Generated {len(predictions)} predictions")
    logger.info(f"Most common: {most_common}")
    logger.info(f"Most confident: {most_confident} ({confidence_scores[max_conf_idx]:.3f})")
    
    return {
        'all_predictions': predictions.tolist(),
        'all_confidences': confidence_scores.tolist(),
        'prediction_counts': dict(pred_counts),
        'most_common_prediction': most_common,
        'most_confident_prediction': most_confident,
        'max_confidence': float(confidence_scores[max_conf_idx]),
        'mean_confidence': float(confidence_scores.mean()),
        'total_windows': len(predictions)
    }

# Load model on startup
load_model_and_mapping()

@app.get("/")
async def root():
    """Root endpoint"""
    model_status = "loaded" if model_package is not None else "not loaded"
    mapping_status = "loaded" if label_mapping is not None else "not available"
    
    return {
        "status": "EMG Pose Classifier API is running",
        "model": model_status,
        "label_mapping": mapping_status,
        "cuda": "available" if CUDA_AVAILABLE else "cpu fallback",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for AWS ALB - always returns 200"""
    return {
        "status": "healthy",
        "model_loaded": model_package is not None,
        "cuda": "available" if CUDA_AVAILABLE else "cpu_fallback"
    }

@app.get("/model-info")
async def model_info():
    """Get detailed model information"""
    if model_package is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    info = {
        "n_classes": model_package.get('n_classes'),
        "class_names": model_package.get('class_names'),
        "trained_at": model_package.get('trained_at'),
        "preprocessing_params": model_package.get('preprocessing_params'),
        "emg_columns": len(model_package.get('emg_columns', [])),
        "angle_columns": len(model_package.get('angle_columns', [])),
        "has_feature_selector": 'feature_selector' in model_package
    }
    
    return info

@app.post("/predict")
async def predict_endpoint(file: UploadFile = File(...)):
    """Main prediction endpoint - upload EMG+Angle data file"""
    try:
        if model_package is None:
            raise HTTPException(status_code=500, detail="Model not loaded")
        
        logger.info(f"Received file: {file.filename}")
        
        # Read uploaded file
        content = await file.read()
        
        # Save temporarily and read based on file type
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            if file.filename.endswith(('.hdf5', '.h5')):
                # HDF5 file
                with h5py.File(temp_file_path, "r") as f:
                    dataset_keys = list(f.keys())
                    logger.info(f"HDF5 datasets: {dataset_keys}")
                    
                    if not dataset_keys:
                        raise ValueError("No datasets found in HDF5 file")
                    
                    # Try common dataset names
                    dataset_name = next(
                        (key for key in ['data', 'dataset', 'emg_data', 'measurements'] 
                         if key in dataset_keys), 
                        dataset_keys[0]
                    )
                    logger.info(f"Using dataset: {dataset_name}")
                    
                    data = pd.DataFrame(f[dataset_name][:])
                    
            elif file.filename.endswith('.csv'):
                # CSV file
                data = pd.read_csv(temp_file_path)
                
            else:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported file format: {Path(file.filename).suffix}. Use CSV or HDF5."
                )
                
        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        logger.info(f"Data loaded: {data.shape}")
        logger.info(f"Columns: {list(data.columns)}")
        
        # Extract required columns
        emg_cols = model_package['emg_columns']
        angle_cols = model_package['angle_columns']
        
        logger.info(f"Required EMG columns: {emg_cols}")
        logger.info(f"Required Angle columns: {angle_cols}")
        
        # Check for missing columns
        missing_emg = [col for col in emg_cols if col not in data.columns]
        missing_angle = [col for col in angle_cols if col not in data.columns]
        
        if missing_emg:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing EMG columns: {missing_emg}"
            )
        
        if missing_angle:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing Angle columns: {missing_angle}"
            )
        
        # Extract data in correct order
        emg_data = data[emg_cols].values
        angle_data = data[angle_cols].values
        
        logger.info(f"Extracted EMG data: {emg_data.shape}")
        logger.info(f"Extracted Angle data: {angle_data.shape}")
        
        # Make prediction
        result = predict_pose(emg_data, angle_data)
        
        # Get pose image if available
        pose_image = None
        if label_mapping is not None:
            try:
                pose_row = label_mapping[
                    label_mapping['Class'] == result['most_confident_prediction']
                ]
                if not pose_row.empty and 'Image Path' in pose_row.columns:
                    pose_image = f"/static/poses/{pose_row['Image Path'].values[0]}"
            except Exception as e:
                logger.warning(f"Error looking up pose image: {e}")
        
        # Format response
        response = {
            "success": True,
            "predicted_class": result['most_confident_prediction'],
            "confidence": result['max_confidence'],
            "mean_confidence": result['mean_confidence'],
            "total_windows": result['total_windows'],
            "prediction_distribution": result['prediction_counts'],
            "pose_image": pose_image,
            "processing_info": {
                "input_samples": len(data),
                "emg_channels": len(emg_cols),
                "angle_channels": len(angle_cols),
                "windows_generated": result['total_windows'],
                "cuda_used": CUDA_AVAILABLE
            }
        }
        
        logger.info(f"Prediction successful: {result['most_confident_prediction']} ({result['max_confidence']:.3f})")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail=f"Prediction failed: {str(e)}"
        )

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {
        "message": "EMG Pose Classifier API is working!",
        "model_loaded": model_package is not None,
        "cuda_available": CUDA_AVAILABLE,
        "classes": model_package.get('class_names', []) if model_package else []
    }

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("EMG POSE CLASSIFIER API")
    print("=" * 60)
    print(f"Model: {'✓' if model_package else '✗'}")
    print(f"CUDA: {'✓' if CUDA_AVAILABLE else '✗'}")
    print(f"Label mapping: {'✓' if label_mapping else '✗'}")
    print("=" * 60)
    
    if model_package:
        print("Ready to serve predictions!")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    else:
        print("ERROR: Model not loaded! Check file paths.")
        print(f"Looking for: {MODEL_PATH.absolute()}")