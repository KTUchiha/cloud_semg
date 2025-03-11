#!/bin/bash
PROJECT_DIR=/app
LOGS=$PROJECT_DIR/logs
mkdir -p $LOGS
echo "Starting NatServer"
cd ${PROJECT_DIR}/natserver
nohup ${PROJECT_DIR}/natserver/nats-server -c nats-server.conf 2>&1> $LOGS/natserver.log   & 
echo "Starting Streamlit App"
cd ${PROJECT_DIR}/streamlit_apps
nohup streamlit run Main.py 2>&1> $LOGS/streamlit.log & 
echo "Starting UDP Server"
cd ${PROJECT_DIR}/udpserver
nohup python3 udpserver.py 2>&1> $LOGS/udpserver.log & 
echo "Starting ML Model Server"
cd $PROJECT_DIR/ml_model
nohup uvicorn api:app --reload --host='0.0.0.0' --port=8000 2>&1> $LOGS/api.logs & 
nohup python3 nat_inference.py 2>&1> $LOGS/nat_inference.logs & 
exec sleep infinity

