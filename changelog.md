# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-04-05

### Added

- Queue system: Automatically queues VM creation requests when capacity is reached
- Premium codes (Xcloud+): Create VMs that never auto-delete with valid premium codes
- Developer whitelist: Restrict VM creation to specific developer IDs
- Admin panel: Web-based management interface at `/admin`
- Rate limiting: Built-in rate limits to prevent abuse
- Resource monitoring: Real-time CPU stats for all containers via `/api/admin/containers`
- Separate VM limits: Different caps for free vs premium VMs (`MAX_FREE_VMS`, `MAX_PREMIUM_VMS`)
- High usage protection: Auto-delete non-premium VMs when server CPU/RAM exceeds 90%
- Per-premium-code limits: Limit VMs per premium code (`MAX_PREMIUM_VMS_PER_CODE`)
- Queue status API: Track queued requests with `/api/queue_status`
- Queue cancel API: Cancel queued requests with `/api/queue_cancel`

### Changed

- Improved queue processing efficiency
- Enhanced resource allocation logic
- Updated documentation with new API endpoints

### Fixed

- Fixed rate limit handler type compatibility
- Improved Docker client error handling

## [1.0.0] - 2026-03-22

### Added

- Initial release of the VM Management API.
- Support for creating Ubuntu KasmVNC VMs using Docker.
- Inactive session auto-deletion (idle CPU monitoring).
- Hard 60-minute session cap.
- Password-protected `/api/list` and `/api/delete` endpoints.
- Support for dynamic hostnames in VM creation URL.
- Added more documentation, examples, and tooling.

### Fixed

- Improved API stability by offloading Docker calls to background threads.
- Added health check endpoint for reverse proxy monitoring.
- Enhanced Caddyfile with retry logic to prevent 502 errors.
- Robust port allocation to avoid race conditions.
