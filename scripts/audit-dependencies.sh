#!/bin/bash
#
# Dependency Security Audit Script for StreamTV
# Scans dependencies for known security vulnerabilities
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REQUIREMENTS_FILES=(
    "${PROJECT_ROOT}/requirements.txt"
    "${PROJECT_ROOT}/requirements-secure.txt"
    "${PROJECT_ROOT}/requirements-mcp-archive-org.txt"
    "${PROJECT_ROOT}/requirements-mcp-ersatztv.txt"
    "${PROJECT_ROOT}/requirements-mcp-streamtv.txt"
)
OUTPUT_DIR="${PROJECT_ROOT}/security-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Function to print colored messages
print_header() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check Python version
check_python_version() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    local version=$(python3 --version 2>&1 | awk '{print $2}')
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)
    
    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 10 ]); then
        print_error "Python 3.10+ is required. Found: $version"
        exit 1
    fi
    
    print_success "Python $version found"
}

# Check if pip-audit is installed
check_pip_audit() {
    # Check if pip-audit is available as a command or module
    if ! command -v pip-audit &> /dev/null && ! python3 -m pip show pip-audit &> /dev/null; then
        print_warning "pip-audit not found. Installing..."
        python3 -m pip install --user pip-audit>=2.10.0 --quiet
        
        # Add user bin directory to PATH if pip-audit was installed there
        local user_bin="$HOME/Library/Python/$(python3 --version | cut -d' ' -f2 | cut -d. -f1,2)/bin"
        if [ -d "$user_bin" ] && [[ ":$PATH:" != *":$user_bin:"* ]]; then
            export PATH="$user_bin:$PATH"
            print_info "Added $user_bin to PATH for this session"
        fi
    fi
    
    # Verify pip-audit is accessible
    if command -v pip-audit &> /dev/null || python3 -m pip_audit --help &> /dev/null; then
        print_success "pip-audit is available"
    else
        print_error "pip-audit installation failed or not accessible"
        print_info "Try: python3 -m pip install --user pip-audit>=2.10.0"
        exit 1
    fi
}

# Run pip-audit on a single requirements file
run_pip_audit_file() {
    local req_file="$1"
    local file_name=$(basename "$req_file")
    local output_file="${OUTPUT_DIR}/pip-audit-${file_name}-${TIMESTAMP}.json"
    local sbom_file="${OUTPUT_DIR}/sbom-${file_name}-${TIMESTAMP}.json"
    
    # Try pip-audit as command first, then as module
    local pip_audit_cmd=""
    if command -v pip-audit &> /dev/null; then
        pip_audit_cmd="pip-audit"
    elif python3 -m pip_audit --help &> /dev/null; then
        pip_audit_cmd="python3 -m pip_audit"
    else
        print_error "pip-audit not found. Please install it first."
        return 1
    fi
    
    print_info "Scanning ${req_file}..."
    
    # Run security scan
    local scan_result=0
    if $pip_audit_cmd -r "$req_file" --format json --output "$output_file" 2>&1; then
        print_success "Security scan completed for ${file_name}"
        print_info "Results saved to: $output_file"
    else
        print_warning "Security scan found vulnerabilities in ${file_name}"
        scan_result=1
    fi
    
    # Generate SBOM in CycloneDX format
    if $pip_audit_cmd -r "$req_file" --format cyclonedx-json --output "$sbom_file" 2>&1; then
        print_success "SBOM generated for ${file_name}"
        print_info "SBOM saved to: $sbom_file"
    else
        print_warning "SBOM generation failed for ${file_name}, trying alternative format..."
        # Fallback to JSON format if CycloneDX not available
        if $pip_audit_cmd -r "$req_file" --format json --output "$sbom_file" 2>&1; then
            print_info "SBOM (JSON format) saved to: $sbom_file"
        fi
    fi
    
    # Print summary to console
    echo ""
    print_info "Summary for ${file_name}:"
    $pip_audit_cmd -r "$req_file" 2>&1 | head -30 || true
    echo ""
    
    return $scan_result
}

# Run pip-audit on all requirements files
run_pip_audit() {
    print_header "Running pip-audit Security Scan on All Requirements Files"
    
    mkdir -p "$OUTPUT_DIR"
    
    local total_vulns=0
    local files_scanned=0
    
    for req_file in "${REQUIREMENTS_FILES[@]}"; do
        if [ ! -f "$req_file" ]; then
            print_warning "Requirements file not found: $req_file (skipping)"
            continue
        fi
        
        if run_pip_audit_file "$req_file"; then
            files_scanned=$((files_scanned + 1))
        else
            total_vulns=$((total_vulns + 1))
            files_scanned=$((files_scanned + 1))
        fi
    done
    
    echo ""
    print_header "Overall Security Scan Summary"
    print_info "Files scanned: $files_scanned"
    if [ $total_vulns -eq 0 ]; then
        print_success "No vulnerabilities found in scanned files"
    else
        print_warning "$total_vulns file(s) contain vulnerabilities"
    fi
}

# Generate dependency tree for a single requirements file
generate_dependency_tree_file() {
    local req_file="$1"
    local file_name=$(basename "$req_file")
    local output_file="${OUTPUT_DIR}/dependency-tree-${file_name}-${TIMESTAMP}.txt"
    
    # Check if pipdeptree is installed, if not install it
    if ! python3 -m pip show pipdeptree &> /dev/null; then
        print_info "pipdeptree not found. Installing..."
        python3 -m pip install --user pipdeptree>=2.0.0 --quiet
    fi
    
    if python3 -m pip show pipdeptree &> /dev/null; then
        print_info "Generating dependency tree for ${file_name}..."
        python3 -m pipdeptree -r -p "$req_file" > "$output_file" 2>&1 || true
        print_success "Dependency tree saved to: $output_file"
    else
        print_warning "pipdeptree installation failed. Skipping dependency tree generation for ${file_name}."
    fi
}

# Generate dependency trees for all requirements files
generate_dependency_tree() {
    print_header "Generating Dependency Trees"
    
    for req_file in "${REQUIREMENTS_FILES[@]}"; do
        if [ -f "$req_file" ]; then
            generate_dependency_tree_file "$req_file"
        fi
    done
    
    echo ""
    print_info "Dependency trees generated for all requirements files"
}

# Main function
main() {
    print_header "StreamTV Dependency Security Audit"
    
    # Check prerequisites
    check_python_version
    check_pip_audit
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Run audits
    local audit_result=0
    if run_pip_audit; then
        print_success "Security scan completed"
    else
        print_warning "Vulnerabilities detected. Review the reports for details."
        audit_result=1
    fi
    
    # Generate dependency tree
    generate_dependency_tree
    
    # Generate severity-based summary report
    generate_severity_report
    
    # Summary
    echo ""
    print_header "Audit Complete"
    print_info "Reports saved to: $OUTPUT_DIR"
    print_info "SBOM files saved to: $OUTPUT_DIR"
    print_info "Review the reports and update dependencies as needed"
    echo ""
    
    return $audit_result
    
    return $audit_result
}

# Generate severity-based summary report
generate_severity_report() {
    print_header "Generating Severity-Based Summary Report"
    
    local summary_file="${OUTPUT_DIR}/security-summary-${TIMESTAMP}.txt"
    
    {
        echo "StreamTV Security Audit Summary"
        echo "Generated: $(date)"
        echo ""
        echo "=== Files Scanned ==="
        for req_file in "${REQUIREMENTS_FILES[@]}"; do
            if [ -f "$req_file" ]; then
                echo "- $(basename "$req_file")"
            fi
        done
        echo ""
        echo "=== Vulnerability Summary ==="
        echo "Review individual JSON reports for detailed vulnerability information."
        echo ""
        echo "=== Recommendations ==="
        echo "1. Review all JSON reports in: $OUTPUT_DIR"
        echo "2. Update packages with critical/high severity vulnerabilities immediately"
        echo "3. Plan updates for moderate severity vulnerabilities"
        echo "4. Use SBOM files for supply chain security tracking"
        echo "5. Run this audit regularly (recommended: weekly)"
    } > "$summary_file"
    
    print_success "Summary report saved to: $summary_file"
}

# Run main function
main "$@"

