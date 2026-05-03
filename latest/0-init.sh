#!/bin/bash


set -e

VENV_DIR=".venv";

echo "Creating virtual environment in $VENV_DIR ...";

python3 -m venv "$VENV_DIR";

# Activate it
source "$VENV_DIR/bin/activate";

echo "Upgrading pip ..."
pip install --upgrade pip;

echo "Installing dependencies ...";
pip install openai;
pip install python-dotenv;
pip install requests;
pip install hypothesis;
pip install pytest;
pip install pandas;

echo "";
echo "Setup complete";
echo "To activate the environment, run:";
echo "source $VENV_DIR/bin/activate";
