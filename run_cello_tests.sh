#!/bin/bash

# Change to the project directory
cd "$(dirname "$0")"

# Source bash_profile to get the correct PATH that includes Yosys
source ~/.bash_profile

# Activate the virtual environment
source venv/bin/activate

# Export the PATH to ensure Yosys is visible
export PATH="/opt/homebrew/bin:$PATH"

# Run the tests
echo "Running Cello integration tests with proper environment..."
python -m unittest src.tests.test_cello_integration

# Deactivate the virtual environment
deactivate 