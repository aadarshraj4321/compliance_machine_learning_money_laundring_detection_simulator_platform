import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense

from pathlib import Path # Add this import

# Correct, direct imports since the working directory is /code/src
from app.database import SessionLocal
from app.models import Transaction, User

# --- THIS IS THE FIX ---
# Define the absolute path to the 'models' directory relative to this file.
# This file is in /code/src, so we go up one parent to /code, then down into 'models'.
MODELS_DIR = Path(__file__).resolve().parents[1] / 'models'


def train_and_save_models():
    print("Starting model training process...")
    db = SessionLocal()

    # --- 1. Data Preparation ---
    print("Fetching training data for normal users...")
    normal_users_query = db.query(User).filter(
        User.full_name != "Walter White",
        User.full_name != "Danny Ocean"
    )
    normal_user_ids = [user.id for user in normal_users_query.all()]

    if not normal_user_ids:
        print("No normal users found for training. Aborting.")
        db.close()
        return

    query = db.query(Transaction).filter(Transaction.user_id.in_(normal_user_ids))
    df = pd.read_sql(query.statement, query.session.bind)

    if df.empty:
        print("No transaction data available for training. Aborting.")
        db.close()
        return

    print(f"Loaded {len(df)} transactions for training.")

    # --- 2. Feature Engineering ---
    features = df[['amount']]
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)
    
    # --- 3. Train and Save Isolation Forest ---
    print("Training Isolation Forest model...")
    iso_forest = IsolationForest(contamination='auto', random_state=42)
    iso_forest.fit(scaled_features)
    
    # Save the model and the scaler to the absolute path
    joblib.dump(iso_forest, MODELS_DIR / 'isolation_forest.joblib')
    joblib.dump(scaler, MODELS_DIR / 'scaler.joblib')
    print(f"Isolation Forest model and scaler saved to {MODELS_DIR}")

    # --- 4. Train and Save TensorFlow Autoencoder ---
    print("Training Autoencoder model...")
    input_dim = scaled_features.shape[1]
    encoding_dim = int(input_dim / 2) if input_dim > 1 else 1

    input_layer = Input(shape=(input_dim,))
    encoder = Dense(encoding_dim, activation="relu")(input_layer)
    decoder = Dense(input_dim, activation='sigmoid')(encoder)
    autoencoder = Model(inputs=input_layer, outputs=decoder)

    autoencoder.compile(optimizer='adam', loss='mean_squared_error')
    autoencoder.fit(scaled_features, scaled_features,
                    epochs=20,
                    batch_size=32,
                    shuffle=True,
                    validation_split=0.1,
                    verbose=0)

    # Save the autoencoder model to the absolute path
    autoencoder.save(MODELS_DIR / 'autoencoder.keras')
    print(f"Autoencoder model saved to {MODELS_DIR}")
    
    db.close()
    print("Model training complete.")

if __name__ == "__main__":
    # Create the directory using the absolute path
    print(f"Ensuring models directory exists at: {MODELS_DIR}")
    MODELS_DIR.mkdir(exist_ok=True)
    train_and_save_models()