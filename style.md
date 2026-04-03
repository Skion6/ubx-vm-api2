# Code Style Guide

This document outlines the coding conventions used in the Xcloud VM API project.

## General Principles

- Write clean, readable code
- Keep functions focused and small
- Use meaningful variable and function names
- Comment complex logic

## Python

### Indentation

- Use 4 spaces per indentation level
- No tabs

```python
def example_function(param1,param2):
    result=param1+param2
    return result
```

### Naming

- Variables and functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`

```python
MAX_VMS_PER_DEV=100
class VMManager:
    def create_vm(self,name):
        pass
```

### Imports

- Standard library first, then third-party, then local

```python
import os
import socket
import docker
from fastapi import FastAPI
```

### Functions

- Always include docstrings
- Use type hints

```python
def verify_password(password_query:str=None,password_header:str=None):
    """Verify admin password from query or header."""
    if password_query==ADMIN_PASSWORD or password_header==ADMIN_PASSWORD:
        return True
    raise HTTPException(status_code=401,detail="Unauthorized")
```

## Shell Scripts

### Shebang and Error Handling

- Always use `#!/bin/bash`
- Always use `set -e`

```bash
#!/bin/bash
set -e
```

### Indentation

- Use 2 spaces

```bash
if [ -d "/path" ]; then
  echo "exists"
fi
```

### Logging

- Use `echo` with `**** message ****` format

```bash
echo "**** install wine ****"
```

### Package Management

- Use `-y` flag for apt-get
- Set `DEBIAN_FRONTEND=noninteractive`

```bash
DEBIAN_FRONTEND=noninteractive apt-get install -y wine
```

## Dockerfile

### Structure

- Labels for metadata
- Comments with `#`
- Multi-line commands with `\`

```dockerfile
FROM ghcr.io/linuxserver/baseimage-kasmvnc:ubuntunoble
LABEL maintainer="mollomm1"
ENV DEBIAN_FRONTEND=noninteractive

RUN \
  echo "**** install packages ****" && \
  apt-get update -y && \
  apt-get install -y wget
```

### Best Practices

- Use `--no-install-recommends` to minimize image size
- Clean up in same layer
- Use specific tags, not `latest`

```dockerfile
RUN apt-get install --no-install-recommends -y wget jq && \
    apt-get autoclean && \
    rm -rf /var/lib/apt/lists/*
```

## JavaScript

### Indentation

- Use 2 spaces

```javascript
function example() {
  const x = 1;
  return x;
}
```

### Naming

- Variables and functions: `camelCase`
- Constants: `UPPER_SNAKE_CASE`

```javascript
const MAX_CONNECTIONS = 10;
let currentCount = 0;
function handleRequest() {}
```

## File Organization

- Python: `main.py`, `setup.py`, `tools/verify_auth.py`
- Shell scripts: `root/installable-apps/*.sh`
- Docker: `Dockerfile`, `Dockerfile.aarch64`
- Wiki: `wiki/*.md`

## Minification

All code in this project follows minified patterns:

- No unnecessary whitespace
- Concise variable names where appropriate
- Single-line statements where readable
