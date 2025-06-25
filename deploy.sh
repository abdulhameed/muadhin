#!/bin/bash

# Change to the project directory
cd /muadhin

# Create the file_cache directory if it doesn't exist
mkdir -p file_cache

# Grant write permissions to the Django process user/group
chown -R django:django file_cache
chmod -R 775 file_cache