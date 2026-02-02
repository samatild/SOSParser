#!/bin/bash
# SOSParser Docker Build Script

set -e

echo "🐳 Building SOSParser Docker Image..."
echo ""

# Build the image (no cache to ensure latest changes are included)
docker build --no-cache -t sosparser:latest .

echo ""
echo "✅ Build complete!"
echo ""
echo "Image: sosparser:latest"
docker images | grep sosparser

# Check for run arguments
if [[ "$1" == "--run" ]]; then
    echo ""
    echo "🚀 Parameter -run detected. Restarting container..."
    
    echo "Stopping sosparser..."
    docker stop sosparser 2>/dev/null || true

    echo "Removing sosparser..."
    docker rm sosparser 2>/dev/null || true

    echo "Starting new container..."
    docker run -d -p 8000:8000 --name sosparser -e WEBAPP_DEBUG=1 
    sosparser:latest
    
    echo ""
    echo "✅ Container is running!"
elif [[ "$1" == "--run-public" ]]; then
    echo ""
    echo "🚀 Parameter --run-public detected. Restarting container in PUBLIC MODE..."
    
    echo "Stopping sosparser..."
    docker stop sosparser 2>/dev/null || true

    echo "Removing sosparser..."
    docker rm sosparser 2>/dev/null || true

    echo "Starting new container with PUBLIC_MODE=true..."
    docker run -d -p 8000:8000 --name sosparser -e PUBLIC_MODE=true sosparser:latest
    
    echo ""
    echo "✅ Container is running in PUBLIC MODE!"
    echo "   - No report storage"
    echo "   - Saved Reports browser disabled"
    echo "   - Reports deleted after viewing"
else
    echo ""
    echo "To run manually:"
    echo "  docker run -d -p 8000:8000 --name sosparser sosparser:latest"
    echo ""
    echo "To run in public mode (no data retention):"
    echo "  docker run -d -p 8000:8000 --name sosparser -e PUBLIC_MODE=true sosparser:latest"
    echo ""
    echo "To run with persistent storage:"
    echo "  docker run -d -p 8000:8000 --name sosparser -v sosparser_uploads:/app/webapp/uploads -v sosparser_outputs:/app/webapp/outputs samuelmatildes/sosparser:latest"
    echo ""
    echo "Or use docker-compose:"
    echo "  docker-compose up -d"
fi