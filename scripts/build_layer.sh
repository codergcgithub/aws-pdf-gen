#!/bin/bash

# Exit on error
set -e

# Define the layer name
LAYER_NAME="unoconv-layer"

# Create a directory for the layer
rm -rf layer
mkdir -p layer/bin layer/lib

# Install unoconv and its dependencies
cp /usr/bin/unoconv layer/bin/
cp -r /usr/lib/libreoffice layer/lib/

# Create the layer zip file
mkdir -p dist
zip -r dist/unoconv-layer.zip layer

# Clean up
rm -rf layer
