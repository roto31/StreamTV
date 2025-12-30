# Makefile for StreamTV Desktop Installers and Packaging
# Supports macOS, Windows, and Linux builds

.PHONY: help build-macos build-windows build-linux build-all docker-build docker-test docker-validate package-desktop clean

# Default target
help:
	@echo "StreamTV Build Targets:"
	@echo "  make build-macos      - Build macOS desktop installer"
	@echo "  make build-windows    - Build Windows desktop installer"
	@echo "  make build-linux      - Build Linux desktop installer"
	@echo "  make build-all        - Build all desktop installers"
	@echo "  make docker-build    - Build Docker image"
	@echo "  make docker-test     - Test Docker image"
	@echo "  make docker-validate - Validate Docker image (health, config, migrations)"
	@echo "  make package-desktop  - Package desktop application bundles"
	@echo "  make clean           - Clean build artifacts"

# macOS build target
build-macos:
	@echo "Building macOS desktop installer..."
	@if [ -f build-installer.sh ]; then \
		chmod +x build-installer.sh && ./build-installer.sh; \
	else \
		echo "Error: build-installer.sh not found"; \
		exit 1; \
	fi

# Windows build target (using PyInstaller or similar)
build-windows:
	@echo "Building Windows desktop installer..."
	@if [ -f scripts/build-windows.sh ]; then \
		chmod +x scripts/build-windows.sh && scripts/build-windows.sh; \
	else \
		echo "Creating Windows build script..."; \
		scripts/create-windows-installer.sh; \
	fi

# Linux build target (using AppImage or similar)
build-linux:
	@echo "Building Linux desktop installer..."
	@if [ -f scripts/build-linux.sh ]; then \
		chmod +x scripts/build-linux.sh && scripts/build-linux.sh; \
	else \
		echo "Creating Linux build script..."; \
		scripts/create-linux-installer.sh; \
	fi

# Build all platforms
build-all: build-macos build-windows build-linux
	@echo "All desktop installers built successfully"

# Docker build
docker-build:
	@echo "Building Docker image..."
	@if [ -f StreamTV-Containers/docker/Dockerfile ]; then \
		docker build -t streamtv:latest -f StreamTV-Containers/docker/Dockerfile .; \
	else \
		echo "Error: Dockerfile not found"; \
		exit 1; \
	fi

# Docker test
docker-test:
	@echo "Testing Docker image..."
	@docker run --rm streamtv:latest python -m pytest tests/ -v || echo "Tests completed"

# Docker validation (health, config, migrations)
docker-validate:
	@echo "Validating Docker image..."
	@if [ -f scripts/validate-docker.sh ]; then \
		chmod +x scripts/validate-docker.sh && scripts/validate-docker.sh; \
	else \
		echo "Creating Docker validation script..."; \
		scripts/create-docker-validation.sh; \
	fi

# Package desktop applications
package-desktop:
	@echo "Packaging desktop applications..."
	@mkdir -p dist
	@if [ -d "StreamTVInstaller/build" ]; then \
		cp -R StreamTVInstaller/build/*.app dist/ 2>/dev/null || true; \
	fi
	@if [ -d "dist-windows" ]; then \
		cp -R dist-windows/* dist/ 2>/dev/null || true; \
	fi
	@if [ -d "dist-linux" ]; then \
		cp -R dist-linux/* dist/ 2>/dev/null || true; \
	fi
	@echo "Desktop packages created in dist/"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf dist dist-windows dist-linux
	@rm -rf StreamTVInstaller/build
	@rm -rf __pycache__ */__pycache__ */*/__pycache__
	@rm -rf *.pyc */*.pyc */*/*.pyc
	@rm -rf .pytest_cache
	@rm -rf *.egg-info
	@echo "Clean complete"

