#!/bin/bash

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run Flask app
echo "Starting OutSystems ODC Exam Simulator..."
echo "Open your browser and navigate to: http://localhost:5000"
python app.py
