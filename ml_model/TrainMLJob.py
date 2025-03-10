import psycopg2
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import StandardScaler
import joblib
import os
import torch.nn.functional as F
import json
from datetime import datetime
import traceback
import pickle
import fire

def get_training_job_data(job_id):
    conn = psycopg2.connect(
        host="localhost",
        database="sensordb",  # Replace with your database name
        user="XXXXX",          # Replace with your username
        password="XXXXX"           # Replace with your password
    )
    
    cursor = conn.cursor()

    gesture_sensor_query = f"""
    SELECT 
        ugt.gestureid, 
        ugt.sensor_a0_used, 
        ugt.sensor_a1_used, 
        ugt.sensor_a2_used, 
        ugt.sensor_a3_used, 
        ugt.sensor_a4_used
    FROM 
        user_gestures ugt
    WHERE 
        ugt.gestureid IN (
            SELECT DISTINCT gestureid
            FROM user_gesture_trainingmetadata ugtm
            JOIN job_training_metadata jtm ON ugtm.training_metadata_id = jtm.training_metadata_id
            WHERE jtm.job_id = {job_id}
        );
    """

    cursor.execute(gesture_sensor_query)
    gesture_sensors = cursor.fetchall()

    sensors_used = {
        'sensor_a0': any(row[1] for row in gesture_sensors),
        'sensor_a1': any(row[2] for row in gesture_sensors),
        'sensor_a2': any(row[3] for row in gesture_sensors),
        'sensor_a3': any(row[4] for row in gesture_sensors),
        'sensor_a4': any(row[5] for row in gesture_sensors)
    }

    columns = ['timestamp']
    selected_sensors = []
    for sensor, used in sensors_used.items():
        if used:
            selected_sensors.append(sensor)
            columns.append(sensor.replace('sensor_', 'Sensor '))
    columns.append('gesture_id')

    data_query = f"""
    WITH training_metadata AS (
        SELECT 
            start_time, 
            end_time, 
            sample_number,
            CASE 
                WHEN status = 'REST PERIOD' THEN 'REST PERIOD' 
                ELSE (select gesture_description from user_gestures u where u.gestureid = ugt.gestureid ) 
            END AS gesture_id
        FROM 
            user_gesture_trainingmetadata ugt  
        WHERE 
            ugt.training_metadata_id IN (
                SELECT training_metadata_id 
                FROM job_training_metadata
                WHERE job_id = {job_id}
            )
    )
    SELECT 
        us.ts AS timestamp, 
        {', '.join(selected_sensors)},
        tmd.gesture_id  
    FROM 
        user_sensor us, 
        training_metadata tmd
    WHERE 
        us.userid = (SELECT userid FROM training_job_schedule WHERE job_id = {job_id}) 
        AND us.ts BETWEEN tmd.start_time AND tmd.end_time
    ORDER BY 
        us.ts;
    """

    cursor.execute(data_query)
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)

    cursor.close()
    conn.close()

    return df, sensors_used


# Preprocessing the data (scaling and encoding)
def preprocess_data(df, sensor_columns):
    scaler = StandardScaler()
    scaler.fit(df[sensor_columns].values)
    df[sensor_columns] = scaler.transform(df[sensor_columns].values)
    
    df['gesture_id'] = df['gesture_id'].astype('category')
    class_mapping = dict(enumerate(df['gesture_id'].cat.categories))
    df['gesture_id'] = df['gesture_id'].cat.codes
    
    return df, class_mapping, scaler



# Preparing the data for training
class EMGDataset(torch.utils.data.Dataset):
    def __init__(self, df, sequence_length=32):
        num_sensors = df.shape[1] - 2  # Exclude timestamp and target columns
        self.sequences, self.labels = self.process_df(df, sequence_length, num_sensors)
        
        # Convert to PyTorch tensors
        try:
            self.sequences = torch.tensor(self.sequences, dtype=torch.float32)
            self.labels = torch.tensor(self.labels, dtype=torch.long)
        except Exception as e:
            print(f"Error converting to tensor: {e}")
            print("Sequences type:", self.sequences.dtype)
            print("Labels type:", self.labels.dtype)
            print("First few sequences:", self.sequences[:5])
            print("First few labels:", self.labels[:5])
            raise e

    def process_df(self, rdf, sequence_length, num_sensors):
        sequences = []
        labels = []
        for row in range(sequence_length, rdf.shape[0]):
            sequence = rdf.iloc[row-sequence_length:row, 1:1+num_sensors].values.T.flatten()  # Exclude timestamp
            target = rdf.iloc[row, -1]  # Target column (gesture_id)
            sequences.append(sequence)
            labels.append(target)
        return np.array(sequences), np.array(labels)

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.labels[idx]


# Defining the CNN model
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
            x = torch.zeros(1, 1, 128)  # Adjust the size according to your data
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



# Function to store artifacts in the database
def store_artifacts_in_db(job_id, userid, model, class_mapping, scaler, sensors_used, conn):
    # Serialize the model and scaler
    model_blob = pickle.dumps(model.state_dict())
    scaler_blob = pickle.dumps(scaler)
    
    # Convert sensors used and class mapping to JSON
    sensors_used_json = json.dumps(sensors_used)
    class_mapping_json = json.dumps(class_mapping)
    
    # Insert or update the artifacts in the database
    cursor = conn.cursor()
    query = """
    INSERT INTO public.training_job_artifacts (job_id, userid, model, class_mapping, scaler, sensors_used)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (job_id)
    DO UPDATE SET
        model = EXCLUDED.model,
        class_mapping = EXCLUDED.class_mapping,
        scaler = EXCLUDED.scaler,
        sensors_used = EXCLUDED.sensors_used,
        userid = EXCLUDED.userid;
    """
    cursor.execute(query, (job_id, userid, model_blob, class_mapping_json, scaler_blob, sensors_used_json))
    conn.commit()
    cursor.close()


def update_job_status(job_id, status=None, log_message=None, error_message=None, conn=None):
    """Update the status, log messages, or error messages for the job."""
    update_fields = []
    update_values = []

    if status:
        update_fields.append("job_status = %s")
        update_values.append(status)

    if log_message:
        update_fields.append("log_messages = COALESCE(log_messages, '') || %s || '\n'")
        update_values.append(log_message)

    if error_message:
        update_fields.append("error_message = %s")
        update_values.append(error_message)

    if status == 'in-progress' and 'actual_start_time' not in update_fields:
        update_fields.append("actual_start_time = %s")
        update_values.append(datetime.now())

    if status in ('completed', 'failed', 'canceled'):
        update_fields.append("actual_end_time = %s")
        update_values.append(datetime.now())

    if update_fields:
        query = f"UPDATE training_job_schedule SET {', '.join(update_fields)} WHERE job_id = %s"
        update_values.append(job_id)

        cursor = conn.cursor()
        cursor.execute(query, update_values)
        conn.commit()
        cursor.close()

def train_model(job_id, num_epochs=50, sequence_length=32, batch_size=32):
    # Initialize database connection
    conn = psycopg2.connect(
        host="localhost",
        database="sensordb",  # Replace with your database name
        user="kaavya",          # Replace with your username
        password="sEMG1234"           # Replace with your password
    )

    try:
        # Set job status to in-progress
        update_job_status(job_id, status='in-progress', log_message='Training started.', conn=conn)
        df, sensors_used = get_training_job_data(job_id)
        
        # Preprocess data and get class mapping
        sensor_columns = df.columns[1:-1]  # All columns except the last one (assumed to be the target)
        df, class_mapping, scaler = preprocess_data(df, sensor_columns)
        
        # Create dataset
        dataset = EMGDataset(df, sequence_length=sequence_length)
        
        # Split the dataset into training and validation sets
        train_size = int(0.8 * len(dataset))
        val_size = len(dataset) - train_size
        train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
        
        train_dataloader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_dataloader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        # Model instantiation
        num_classes = df['gesture_id'].nunique()
        model = EnhancedAudioCNN(num_classes=num_classes)
        
        # Move the model to GPU if available
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        
        # Loss and optimizer
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=3e-4)
        
        # Compile the model for better performance
        model = torch.compile(model)
        
        for epoch in range(num_epochs):
            model.train()
            running_loss = 0.0
            correct_predictions = 0
            total_predictions = 0
            for batch_idx, (inputs, labels) in enumerate(train_dataloader):
                inputs, labels = inputs.to(device), labels.to(device)
                inputs = inputs.unsqueeze(1)  # Add a channel dimension
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                
                loss.backward()
                optimizer.step()
                
                running_loss += loss.item()
                _, predicted = torch.max(outputs, 1)
                correct_predictions += (predicted == labels).sum().item()
                total_predictions += labels.size(0)

                # Log progress every 10 batches
                if (batch_idx + 1) % 10 == 0:
                    log_msg = (f'Epoch [{epoch+1}/{num_epochs}], Step [{batch_idx+1}/{len(train_dataloader)}], '
                               f'Loss: {running_loss/(batch_idx+1):.4f}, '
                               f'Accuracy: {correct_predictions/total_predictions:.4f}')
                    update_job_status(job_id, log_message=log_msg, conn=conn)
            
            # Validation phase
            model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, labels in val_dataloader:
                    inputs, labels = inputs.to(device), labels.to(device)
                    inputs = inputs.unsqueeze(1)  # Add a channel dimension
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
                    val_loss += loss.item()
                    _, predicted = torch.max(outputs, 1)
                    val_correct += (predicted == labels).sum().item()
                    val_total += labels.size(0)
            
            print(f'Epoch [{epoch+1}/{num_epochs}], Training Loss: {running_loss/len(train_dataloader):.4f}, '
                  f'Validation Loss: {val_loss/len(val_dataloader):.4f}, '
                  f'Validation Accuracy: {val_correct/val_total:.4f}')
        
        # Get the userid for the job from the training_job_schedule table
        cursor = conn.cursor()
        cursor.execute("SELECT userid FROM training_job_schedule WHERE job_id = %s", (job_id,))
        userid = cursor.fetchone()[0]
        cursor.close()

        # Save artifacts to the database
        store_artifacts_in_db(job_id, userid, model, class_mapping, scaler, sensors_used, conn)

        # Update job status to completed
        update_job_status(job_id, status='completed', log_message='Training completed successfully.', conn=conn)
        print(f'Training complete and artifacts saved to the database.')
    
    except Exception as e:
        error_message = str(e)
        stack_trace = traceback.format_exc()  # Get the full stack trace
        full_error_message = f"{error_message}\n\nStack Trace:\n{stack_trace}"
        
        update_job_status(job_id, status='failed', log_message='Training failed.', error_message=full_error_message, conn=conn)
        print(f'Error occurred: {full_error_message}')
    
    finally:
        conn.close()

# Example usage
if __name__ == '__main__':
  fire.Fire(train_model)

