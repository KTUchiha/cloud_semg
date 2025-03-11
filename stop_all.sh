#!/bin/bash
PROJECT_DIR=/app
LOGS=$PROJECT_DIR/logs

echo "Stopping NatServer"
natserver_pid=$(ps aux | grep '[n]ats-server' | awk '{print $2}')
if [ ! -z "$natserver_pid" ]; then
  kill $natserver_pid
  echo "NatServer stopped."
else
  echo "NatServer not running."
fi

echo "Stopping Streamlit App"
streamlit_pid=$(ps aux | grep '[s]treamlit' | awk '{print $2}')
if [ ! -z "$streamlit_pid" ]; then
  echo "killing $streamlit_pid"
	kill $streamlit_pid
  echo "Streamlit App stopped."
else
  echo "Streamlit App not running."
fi

echo "Stopping UDP Server"
udpserver_pid=$(ps aux | grep '[u]dpserver.py' | awk '{print $2}')
if [ ! -z "$udpserver_pid" ]; then
  kill $udpserver_pid
  echo "UDP Server stopped."
else
  echo "UDP Server not running."
fi

echo "Stopping ML Model Server"
ml_model_pid=$(ps aux | grep '[u]vicorn' | awk '{print $2}')
if [ ! -z "$ml_model_pid" ]; then
  kill $ml_model_pid
  echo "ML Model Server stopped."
else
  echo "ML Model Server not running."
fi

nat_inference_pid=$(ps aux | grep '[n]at_inference.py' | awk '{print $2}')
if [ ! -z "$nat_inference_pid" ]; then
  kill $nat_inference_pid
  echo "NAT Inference stopped."
else
  echo "NAT Inference not running."
fi

echo "All processes stopped."
