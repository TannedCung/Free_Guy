#!/bin/bash
set -e

echo "==> Installing frontend_server Python dependencies..."
pip install --upgrade pip
pip install -r /workspaces/Free_Guy/frontend_server/requirements.txt

echo "==> Installing backend_server Python dependencies..."
pip install -r /workspaces/Free_Guy/backend_server/requirements.txt

echo "==> Installing frontend Node dependencies..."
cd /workspaces/Free_Guy/frontend && npm install

echo "==> Post-create setup complete."
