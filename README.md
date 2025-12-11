# SOSParser

A web application for automated analysis of Linux sosreport/supportconfig diagnostic files.

[![Docker Hub](https://img.shields.io/docker/pulls/samuelmatildes/sosparser)](https://hub.docker.com/r/samuelmatildes/sosparser)
[![Docker Image Size](https://img.shields.io/docker/image-size/samuelmatildes/sosparser/latest)](https://hub.docker.com/r/samuelmatildes/sosparser)


## How to run

### Docker (Recommended)

The easiest way to run SOSParser is using Docker:

```bash
docker pull samuelmatildes/sosparser:latest
docker run -d -p 8000:8000 --name sosparser samuelmatildes/sosparser:latest
```

Then open http://localhost:8000 in your browser.



## Usage

### Web Interface

1. Open `http://localhost:8000` in your browser
2. Select a sosreport tarball file (supports .tar.xz, .tar.gz, .tar.bz2, .tar)
3. Click "Analyze Report"
4. View the generated interactive analysis report.


## Supported Formats

### SOSReport (Red Hat/CentOS/Ubuntu/Fedora)
- `.tar.xz` (recommended)
- `.tar.gz`
- `.tar.bz2`
- `.tgz`
- `.tar`

### Supportconfig (SUSE SLES/openSUSE)
- `.txz` (tar.xz format)
- `.tar.xz`


### Build Docker Image Locally

```bash
git clone <your-repo-url>
cd sosparser
docker build -t sosparser:local .
docker run -d -p 8000:8000 sosparser:local
```

### Or use the build script

```bash
./docker-build.sh
```

## Docker Hub

Official Docker image: [samuelmatildes/sosparser](https://hub.docker.com/r/samuelmatildes/sosparser)

Available tags:
- `latest` - Latest stable release from main branch
- `v*.*.*` - Specific version releases
- Multi-platform support: `linux/amd64`, `linux/arm64`

## Contributing

We welcome contributions to `sosparser`! To help us maintain a high-quality codebase, please review and follow these guidelines:

### How to Contribute

1. **Fork the repository**  
   Click "Fork" at the top right of this page and clone your fork locally.

2. **Create a new branch**  
   Branch names should be descriptive, e.g. `feature/add-parsing-support` or `fix/crash-on-upload`.

3. **Make your changes**  
   Please keep your changes focused and avoid unrelated formatting edits.

4. **Write clear commit messages**  
   Describe what your change does and why it’s needed.

5. **Test your changes**  
   Ensure that existing tests pass and write new tests for your features or bugfixes if possible.

6. **Submit a Pull Request**  
   Push your branch and open a Pull Request (PR) to the `main` branch. Include:
   - A summary of your changes
   - Any relevant issue numbers (e.g. `Closes #12`)
   - Screenshots or logs if relevant

7. **Code Review**  
   Be responsive to feedback and please update your PR as requested.


---

## Reporting Issues

If you encounter bugs, have questions, or want to suggest an enhancement:

1. **Search first**  
   Check [existing issues](https://github.com/samatild/sosparser/issues) to avoid duplicates.

2. **Open a new issue**  
   Use the [Issue Tracker](https://github.com/samatild/sosparser/issues/new/choose). Include:
   - A clear and descriptive title
   - Steps to reproduce the problem (if applicable)
   - Expected and actual behavior
   - Environment details (OS, browser, Docker tag, etc.)
   - Screenshots or logs if helpful

3. **Feature Requests**  
   Clearly describe the use case and the benefit for others.

Thank you for helping improve `sosparser`!
