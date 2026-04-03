# Contributing to Xcloud

Thank you for your interest in contributing! This project provides an API for managing lightweight Ubuntu VMs based on KasmVNC.

## How to Contribute

1.  **Report Bugs**: Use GitHub Issues to report bugs or unexpected behavior.
2.  **Suggest Enhancements**: We welcome ideas for new features or improvements.
3.  **Submit Pull Requests**:
    - Fork the repository.
    - Create a new branch for your feature or bug fix.
    - Ensure your code follows existing patterns (e.g., using `asyncio.to_thread` for blocking Docker calls).
    - Provide clear descriptions of your changes in the PR.

## Development Setup

1.  Ensure Docker is installed and running.
2.  Run `tools/setup.sh` (Linux) or `tools/setup.bat` (Windows) to initialize the environment.
3.  The API runs by default on port 8000.
4.  Docker containers for VMs use the `xcloud` image.

**Local development:** Prefer creating a Python virtual environment (`python -m venv venv`) and installing `requirements.txt` rather than committing a `venv/` directory to the repo. Add `venv/` to `.gitignore` and, if accidentally committed, remove it with `git rm -r --cached venv`.

## Code Standards

- Use `FastAPI` for API endpoints.
- Ensure all Docker SDK interactions are non-blocking.
- Keep security in mind (administrative actions require a password).
