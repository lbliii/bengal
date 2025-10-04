# Changelog

All notable changes to Bengal SSG will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Comprehensive resource cleanup system** - Dev server now properly cleans up resources in ALL termination scenarios
  - New `ResourceManager` class for centralized lifecycle management with signal handlers, atexit, and context manager support
  - New `PIDManager` class for process tracking and stale process detection
  - New `bengal cleanup` CLI command for manually cleaning up stale server processes
  - Automatic stale process detection on server startup with user-friendly recovery prompts
  - Proper cleanup on SIGTERM, SIGHUP, parent process death, and terminal crashes
  - PID file tracking (`.bengal.pid`) to identify and recover from zombie processes
  - Idempotent cleanup (safe to call multiple times)
  - LIFO resource cleanup order (like context managers)
  - Timeout protection to prevent hanging on cleanup

### Changed
- **Refactored `DevServer` class** to use ResourceManager pattern
  - Separated server creation from starting for better resource management
  - Added proactive stale process checking before server start
  - Improved error messages and user guidance for port conflicts
  - Better separation of concerns (observer creation, server creation, startup messages)

### Fixed
- **Eliminated zombie processes** - Dev server no longer leaves orphaned processes holding ports
- **Port conflicts on restart** - Automatic detection and recovery from stale processes
- **Resource leaks** - All resources (TCP sockets, file system observers, PID files) now properly cleaned up

### Dependencies
- Added `psutil>=5.9.0` for better process management and validation (optional, graceful fallback)

## [0.1.0] - Previous Release

### Added
- Initial release of Bengal SSG
- Core static site generation
- Development server with hot reload
- Parallel build processing
- Template system with Jinja2
- Asset pipeline
- And much more...

[Unreleased]: https://github.com/bengal-ssg/bengal/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/bengal-ssg/bengal/releases/tag/v0.1.0
