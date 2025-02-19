#!/bin/bash
# This script pushes all submodules and then pushes the parent repository.

set -e

echo "Pushing all submodules..."
git submodule foreach --recursive 'echo "Pushing submodule $name at $path" && git push'

echo "Pushing parent repository..."
git push

echo "All pushes completed."