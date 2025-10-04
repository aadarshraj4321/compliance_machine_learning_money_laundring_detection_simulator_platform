import joblib
import numpy as np
from tensorflow.keras.models import load_model
from pathlib import Path

# --- THIS IS THE CORRECT PATH LOGIC ---
# This file is located at /code/src/app/ml_inference.py
# The models are located in /code/models/
# So, we go up two parent directories (from app to src, from src to code)
# and then go down into the 'models' directory.
MODELS_DIR = Path(__file__).resolve().parents[2] / 'models'

# Global variables to hold the loaded models to prevent reloading on every call
SCALER = None
ISO_FOREST = None
AUTOENCODER = None
MODELS_LOADED = False

def load_models_lazily():
    """
    Loads all ML models into global variables if they haven't been loaded yet.
    Uses absolute paths to avoid any ambiguity about the working directory.
    This function is called by `score_transaction`.
    """
    global SCALER, ISO_FOREST, AUTOENCODER, MODELS_LOADED
    
    # If models are already loaded in this worker process, do nothing.
    if MODELS_LOADED:
        return True

    print(f"Attempting to lazy-load ML models from: {MODELS_DIR}")
    
    scaler_path = MODELS_DIR / 'scaler.joblib'
    iso_forest_path = MODELS_DIR / 'isolation_forest.joblib'
    autoencoder_path = MODELS_DIR / 'autoencoder.keras'
    
    # Check if all necessary model files exist before trying to load them.
    if not all([scaler_path.exists(), iso_forest_path.exists(), autoencoder_path.exists()]):
        print(f"CRITICAL WARNING: One or more model files not found in {MODELS_DIR}. Inference will be disabled for this worker process.")
        return False

    try:
        # Load the models from disk
        SCALER = joblib.load(scaler_path)
        ISO_FOREST = joblib.load(iso_forest_path)
        AUTOENCODER = load_model(autoencoder_path)
        
        # Set the flag to True so we don't try to load them again
        MODELS_LOADED = True
        print("ML models loaded successfully.")
        return True
    except Exception as e:
        print(f"CRITICAL ERROR loading models: {e}")
        return False


def score_transaction(amount: float) -> dict:
    """
    Scores a single transaction amount for its anomalousness.
    """
    # First, ensure the models are loaded. This will only run the loading logic once.
    if not load_models_lazily():
        # If models failed to load for any reason, return a non-anomalous result.
        return {"anomaly": False, "iso_forest_score": 0, "autoencoder_error": 0}

    # Prepare the feature vector for prediction
    # It must be a 2D array, so we wrap the single amount in two sets of square brackets.
    features = np.array([[amount]])
    scaled_features = SCALER.transform(features)

    # 1. Get score from the Isolation Forest model
    # It returns a score where negative values are more anomalous.
    iso_score = ISO_FOREST.decision_function(scaled_features)[0]
    
    # 2. Get reconstruction error from the Autoencoder model
    reconstruction = AUTOENCODER.predict(scaled_features, verbose=0)
    reconstruction_error = np.mean(np.square(scaled_features - reconstruction))

    # 3. Apply business logic to determine if it's an anomaly
    # These thresholds are a key part of "tuning" the model.
    is_anomaly = iso_score < -0.05 or reconstruction_error > 0.2

    return {
        "anomaly": is_anomaly,
        "iso_forest_score": float(iso_score),
        "autoencoder_error": float(reconstruction_error)
    }