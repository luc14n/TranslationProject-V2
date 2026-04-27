#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Change to the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Initialize Conda for this script session
# This is required to use 'conda activate' inside a bash script
if [ -n "$CONDA_EXE" ]; then
    eval "$("$CONDA_EXE" shell.bash hook)"
else
    echo "Error: Conda is not found in your system. Please make sure Anaconda or Miniconda is installed."
    exit 1
fi

ENV_NAME="translation-env"

# Check if the Conda environment already exists
if conda info --envs | grep -q "^$ENV_NAME "; then
    echo "🟢 Found existing Conda environment '$ENV_NAME'. Activating..."
    conda activate $ENV_NAME
else
    echo "🟡 Conda environment '$ENV_NAME' not found. Creating it now with Python 3.12..."
    conda create -n $ENV_NAME python=3.12 -y

    echo "🟢 Activating environment..."
    conda activate $ENV_NAME

    echo "📦 Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
fi

echo "🚀 Starting the Translation Project application..."
python app/main.py
