# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-18

### Added
- Initial release of the VM Management API.
- Support for creating Ubuntu KasmVNC VMs using Docker.
- Inactive session auto-deletion (idle CPU monitoring).
- Hard 60-minute session cap.
- Password-protected `/api/list` and `/api/delete` endpoints.
- Support for dynamic hostnames in VM creation URL.

### Fixed
- Improved API stability by offloading Docker calls to background threads.
- Added health check endpoint for reverse proxy monitoring.
- Enhanced Caddyfile with retry logic to prevent 502 errors.
- Robust port allocation to avoid race conditions.
