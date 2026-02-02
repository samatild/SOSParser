## [0.2.19] - 2026-02-02

### Fixed
- **Critical Memory Optimization for Supportconfig**: Reduces peak memory from ~3.2GB to ~150MB
  - `boot.txt` streaming: New `find_sections_streaming()` method reads large files line-by-line
  - `BootConfigAnalyzer` now streams through boot.txt finding only needed sections (was loading entire file)
  - `ProviderDetector` fixed to read only first N bytes instead of loading entire file then truncating
  - `get_kernel_info()` uses streaming to find "running kernel" section without loading boot.txt
  - Peak memory during supportconfig analysis reduced from 946MB to ~150MB

### Added
- **Memory Profiling Tools** (debug mode only):
  - `Logger.memory(phase)` - logs RSS and Peak memory at checkpoints
  - Tracks VmHWM (High Water Mark) to catch transient memory spikes
  - Granular tracking in all supportconfig sub-analyzers
  - Enable with `WEBAPP_DEBUG=1` environment variable

---
