from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import joblib
import psycopg2
import json
import pickle
import os
import asyncio

app = FastAPI()

# Define input data schema
class InputData(BaseModel):
    userid: int
    data: list

# Define your model architecture
class EnhancedAudioCNN(nn.Module):
    def __init__(self, num_classes):
        super(EnhancedAudioCNN, self).__init__()
        self.conv1 = nn.Conv1d(1, 32, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=3, stride=1, padding=1)
        self.pool = nn.MaxPool1d(kernel_size=2, stride=2, padding=0)
        self.residual_conv = nn.Conv1d(1, 64, kernel_size=1, stride=4, padding=0)
        self.fc_input_size = self._initialize_fc_input_size()
        self.fc1 = nn.Linear(self.fc_input_size, 128)
        self.dropout = nn.Dropout(0.5)
        self.fc2 = nn.Linear(128, num_classes)

    def _initialize_fc_input_size(self):
        with torch.no_grad():
            x = torch.zeros(1, 1, 128)
            x = self.pool(F.relu(self.conv1(x)))
            x = self.pool(F.relu(self.conv2(x)))
            return x.numel()

    def forward(self, x):
        residual = self.residual_conv(x)
        x = F.relu(self.conv1(x))
        x = self.pool(x)
        x = F.relu(self.conv2(x))
        x = self.pool(x)
        if residual.size(2) != x.size(2):
            residual = F.adaptive_avg_pool1d(residual, x.size(2))
        x += residual
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

# Dictionary to hold the models, scalers, sensor configurations, and class mappings for all users
user_artifacts = {}

# Load the most recent model, scaler, and sensor configurations for each user
def load_latest_user_artifacts():
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT DISTINCT ON (userid) userid, model, class_mapping, scaler, sensors_used
    FROM public.training_job_artifacts
    ORDER BY userid, job_id DESC;
    """
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()

    if not results:
        print("Warning: No models found in the database.")
        return

    for userid, model_blob, class_mapping_json, scaler_blob, sensors_used_json in results:
        # Deserialize the model state_dict
        state_dict = pickle.loads(model_blob)
        
        # Remove '_orig_mod.' prefix from keys if present
        new_state_dict = {}
        for key, value in state_dict.items():
            new_key = key.replace("_orig_mod.", "")
            new_state_dict[new_key] = value

        num_classes = len(class_mapping_json)  # Since class_mapping_json is already a dict
        model = EnhancedAudioCNN(num_classes=num_classes)
        model.load_state_dict(new_state_dict)  # Load the adjusted state_dict
        model.eval()

        # Load the scaler
        scaler = pickle.loads(scaler_blob)

        # Load sensors used (assuming this is a JSON string)
        sensors_used = json.loads(sensors_used_json) if isinstance(sensors_used_json, str) else sensors_used_json

        # Load class mapping
        class_mapping = json.loads(class_mapping_json) if isinstance(class_mapping_json, str) else class_mapping_json

        # Store artifacts in the dictionary
        user_artifacts[userid] = {
            "model": model,
            "scaler": scaler,
            "sensors_used": sensors_used,
            "class_mapping": class_mapping
        }
    print("Loaded models for users:", list(user_artifacts.keys()))

# Periodically poll for new models
async def poll_new_models():
    while True:
        try:
            load_latest_user_artifacts()
            print("Polled for new models; current artifacts:", list(user_artifacts.keys()))
        except Exception as e:
            print("Error during polling for new models:", e)
        await asyncio.sleep(60)  # Poll every 60 seconds

# Preprocessing function
def preprocess(data, scaler, sensors_used):
    try:
        # Determine which sensors to use
        columns_to_use = [col for col, used in sensors_used.items() if used]
        
        # Create DataFrame and preprocess the data
        df = pd.DataFrame(data)
        df = df.loc[:, 0:len(columns_to_use) - 1]  # Adjust the range to match the length of columns_to_use
        df.columns = columns_to_use
        df = scaler.transform(df.values)
        
        sequences = []
        for row in range(32, df.shape[0]):
            sequence = df[row-32:row].T.flatten()
            sequences.append(sequence)

        sequences = np.array(sequences)
        return torch.tensor(sequences, dtype=torch.float32)
    
    except ValueError as ve:
        print(f"ValueError occurred: {ve}")
        raise ve
    except IndexError as ie:
        print(f"IndexError occurred: {ie}")
        raise ie
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise e

# Prediction endpoint
@app.post("/predict")
async def predict(input_data: InputData):
    try:
        # Retrieve the model, scaler, and sensors used for the given user ID
        if input_data.userid not in user_artifacts:
            raise HTTPException(status_code=404, detail="No model found for the given user.")

        model_info = user_artifacts[input_data.userid]
        model = model_info["model"]
        scaler = model_info["scaler"]
        sensors_used = model_info["sensors_used"]
        class_mapping = model_info["class_mapping"]
        
        # Preprocess the input data
        data = input_data.data
        inputs = preprocess(data, scaler, sensors_used)
        inputs = inputs.unsqueeze(1)
        
        # Make predictions
        with torch.no_grad():
            outputs = model(inputs)
            _, predicted = torch.max(outputs, 1)
            # Convert predicted indices to gesture descriptions
            predicted_gestures = [class_mapping[str(idx)] for idx in predicted.tolist()]
            return {"predictions": predicted_gestures}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# On startup, try loading models and start polling for new models
@app.on_event("startup")
async def startup_event():
    try:
        load_latest_user_artifacts()
    except Exception as e:
        print("Startup warning: No models loaded initially. Polling will continue. Error:", e)
    # Start background task to poll for new models
    asyncio.create_task(poll_new_models())

def get_db_connection():
    return psycopg2.connect(
        host=os.environ['POSTGRES_HOST'],
        database=os.environ['POSTGRES_DB'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD']
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
