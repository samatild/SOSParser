#!/bin/bash
# 
# Audit Log Helper Script for SOSParser
# Provides convenient commands for viewing and analyzing audit logs
#
# Usage: ./view-audit-logs.sh [command] [options]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
SERVICE_NAME="${SERVICE_NAME:-sosparser}"
USE_DOCKER_DIRECT="${USE_DOCKER_DIRECT:-auto}"  # auto, true, or false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if docker-compose is available
check_docker_compose() {
    if ! command -v docker &> /dev/null; then
        print_error "docker not found. Please install Docker."
        exit 1
    fi
}

# Determine which docker command to use
detect_container_mode() {
    # If explicitly set, use that
    if [ "$USE_DOCKER_DIRECT" = "true" ]; then
        return 0  # Use direct docker
    elif [ "$USE_DOCKER_DIRECT" = "false" ]; then
        return 1  # Use docker compose
    fi
    
    # Auto-detect: check if container exists as standalone
    if sudo docker ps -a --filter "name=^${SERVICE_NAME}$" --format "{{.Names}}" | grep -q "^${SERVICE_NAME}$"; then
        return 0  # Use direct docker
    fi
    
    # Check if docker compose service exists
    if command -v docker compose &> /dev/null; then
        if docker compose -f "$COMPOSE_FILE" ps "$SERVICE_NAME" &> /dev/null; then
            return 1  # Use docker compose
        fi
    fi
    
    # Default to direct docker
    return 0
}

# Show usage
show_usage() {
    cat << EOF
Audit Log Helper Script for SOSParser

Works with both docker-compose and direct docker run containers.

Usage: $0 [command] [options]

Commands:
    live            View audit logs in real-time
    export FILE     Export audit logs to a file
    stats           Show audit log statistics
    by-ip IP        Filter logs by IP address
    by-event TYPE   Filter logs by event type
    failed          Show failed report generations
    security        Show security events
    last N          Show last N audit events (default: 20)
    help            Show this help message

Options:
    -f FILE         Use specific docker-compose file (default: docker-compose.yml)
    -s SERVICE      Use specific service name (default: sosparser)

Environment Variables:
    COMPOSE_FILE      Docker compose file to use
    SERVICE_NAME      Service/container name (default: sosparser)
    USE_DOCKER_DIRECT Set to 'true' to force direct docker, 'false' for compose (default: auto)

Examples:
    # View live audit logs (auto-detects container mode)
    $0 live

    # Export logs to file
    $0 export audit-$(date +%Y%m%d).log

    # Show statistics
    $0 stats

    # Filter by IP address
    $0 by-ip 192.168.1.100

    # Show failed report generations
    $0 failed

    # Show last 50 events
    $0 last 50

    # Force direct docker mode
    USE_DOCKER_DIRECT=true $0 live

    # Use public mode compose file
    COMPOSE_FILE=docker-compose.public.yml $0 live

EOF
}

# Get audit logs
get_audit_logs() {
    if detect_container_mode; then
        # Direct docker
        if ! sudo docker ps -a --filter "name=^${SERVICE_NAME}$" --format "{{.Names}}" | grep -q "^${SERVICE_NAME}$"; then
            print_error "Container '$SERVICE_NAME' not found"
            print_info "Run 'sudo docker ps -a' to see available containers"
            exit 1
        fi
        sudo docker logs "$SERVICE_NAME" 2>/dev/null | grep "AUDIT" || true
    else
        # Docker compose
        docker compose -f "$COMPOSE_FILE" logs "$SERVICE_NAME" 2>/dev/null | grep "AUDIT" || true
    fi
}

# Get live audit logs
get_live_audit_logs() {
    if detect_container_mode; then
        # Direct docker
        if ! sudo docker ps -a --filter "name=^${SERVICE_NAME}$" --format "{{.Names}}" | grep -q "^${SERVICE_NAME}$"; then
            print_error "Container '$SERVICE_NAME' not found"
            print_info "Start the container first with: sudo bash docker-build.sh --run-public"
            exit 1
        fi
        sudo docker logs -f "$SERVICE_NAME" 2>&1 | grep --line-buffered "AUDIT"
    else
        # Docker compose
        docker compose -f "$COMPOSE_FILE" logs -f "$SERVICE_NAME" 2>&1 | grep --line-buffered "AUDIT"
    fi
}

# Command: live
cmd_live() {
    if detect_container_mode; then
        print_info "Using direct docker mode (container: $SERVICE_NAME)"
    else
        print_info "Using docker compose mode (service: $SERVICE_NAME)"
    fi
    print_info "Viewing live audit logs... (Press Ctrl+C to stop)"
    echo ""
    get_live_audit_logs
}

# Command: export
cmd_export() {
    local output_file="$1"
    if [ -z "$output_file" ]; then
        print_error "Please specify an output file"
        echo "Usage: $0 export <filename>"
        exit 1
    fi
    
    print_info "Exporting audit logs to: $output_file"
    get_audit_logs > "$output_file"
    local count=$(wc -l < "$output_file")
    print_success "Exported $count audit log entries"
}

# Command: stats
cmd_stats() {
    if ! command -v python3 &> /dev/null; then
        print_warning "python3 not found. Showing basic statistics instead."
        echo ""
        echo "Total audit events: $(get_audit_logs | wc -l)"
        echo ""
        echo "Events by type:"
        get_audit_logs | grep -oP '"event_type": "\K[^"]+' | sort | uniq -c | sort -rn
        return
    fi
    
    local script_path="$SCRIPT_DIR/examples/analyze_audit_logs.py"
    if [ ! -f "$script_path" ]; then
        print_error "Analysis script not found: $script_path"
        exit 1
    fi
    
    print_info "Analyzing audit logs..."
    echo ""
    get_audit_logs | python3 "$script_path"
}

# Command: by-ip
cmd_by_ip() {
    local ip="$1"
    if [ -z "$ip" ]; then
        print_error "Please specify an IP address"
        echo "Usage: $0 by-ip <ip-address>"
        exit 1
    fi
    
    print_info "Filtering logs by IP: $ip"
    echo ""
    get_audit_logs | grep "\"ip_address\": \"$ip\""
}

# Command: by-event
cmd_by_event() {
    local event_type="$1"
    if [ -z "$event_type" ]; then
        print_error "Please specify an event type"
        echo "Usage: $0 by-event <event-type>"
        echo ""
        echo "Available event types:"
        echo "  - page_access"
        echo "  - report_generation_started"
        echo "  - report_generation_completed"
        echo "  - chunked_upload_initiated"
        echo "  - report_viewed"
        echo "  - security_event"
        exit 1
    fi
    
    print_info "Filtering logs by event type: $event_type"
    echo ""
    get_audit_logs | grep "\"event_type\": \"$event_type\""
}

# Command: failed
cmd_failed() {
    print_info "Showing failed report generations"
    echo ""
    get_audit_logs | grep "report_generation_completed" | grep "\"success\": false"
}

# Command: security
cmd_security() {
    print_info "Showing security events"
    echo ""
    get_audit_logs | grep "\"event_type\": \"security_event\""
}

# Command: last
cmd_last() {
    local count="${1:-20}"
    print_info "Showing last $count audit events"
    echo ""
    get_audit_logs | tail -n "$count"
}

# Main
main() {
    check_docker_compose
    
    local command="${1:-help}"
    shift || true
    
    case "$command" in
        live)
            cmd_live "$@"
            ;;
        export)
            cmd_export "$@"
            ;;
        stats)
            cmd_stats "$@"
            ;;
        by-ip)
            cmd_by_ip "$@"
            ;;
        by-event)
            cmd_by_event "$@"
            ;;
        failed)
            cmd_failed "$@"
            ;;
        security)
            cmd_security "$@"
            ;;
        last)
            cmd_last "$@"
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
