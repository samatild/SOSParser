## [0.2.18] - 2026-02-02

### Fixed
- **Memory Efficiency for Large Log Files**: Prevents OOM crashes in Kubernetes pods
  - Log file tailing now uses reverse-reading algorithm for files > 1MB
  - Only reads the last N lines from disk instead of loading entire file into memory
  - Gzip log files now stream through with `deque(maxlen=N)` to cap memory usage
  - Supportconfig parser uses same memory-efficient tail algorithm
  - Chunk reassembly uses streaming copy (`shutil.copyfileobj`) with 64KB buffer
  - Fixes OOM issues when processing sosreports with large journal/message logs

---