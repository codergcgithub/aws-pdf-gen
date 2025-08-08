#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Define directories
LAMBDA_DIR="./lambda_app"
DIST_DIR="./dist"
PACKAGE_DIR="${DIST_DIR}/package"
ZIP_FILE="${DIST_DIR}/convert_to_pdf.zip"

# Clean up previous build artifacts
echo "Cleaning up previous build artifacts..."
rm -rf "${DIST_DIR}"
mkdir -p "${PACKAGE_DIR}"

# Build the unoconv layer
echo "Building unoconv layer..."
chmod +x ./scripts/build_layer.sh
./scripts/build_layer.sh

# Install Python dependencies
echo "Installing Lambda dependencies..."
python3 -m pip install -r "${LAMBDA_DIR}/requirements.txt" -t "${PACKAGE_DIR}"

# Copy Lambda function code
echo "Copying Lambda function code..."
cp "${LAMBDA_DIR}/convert_to_pdf.py" "${PACKAGE_DIR}/"

# Create the zip file for deployment
echo "Creating deployment package..."
(cd "${PACKAGE_DIR}" && zip -r9 "../convert_to_pdf.zip" .)

# Clean up the package directory
rm -rf "${PACKAGE_DIR}"

echo "Lambda package created successfully at ${ZIP_FILE}"
