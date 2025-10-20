# Installing Free-Threaded Python 3.14

Free-threaded Python (PEP 703) removes the Global Interpreter Lock (GIL), enabling true parallel execution with threads. Bengal automatically detects and uses this for **~1.8x faster rendering** on multi-core machines.

## Performance Comparison

**Rendering 1000 pages on 11-core Mac:**
- Python 3.14 (GIL enabled): 3.46s (289 pages/sec)
- Python 3.14t (free-threaded): 1.94s (515 pages/sec) ⚡ **1.78x faster**

## Step 1: Install Python 3.14t

### macOS - Using Installer (Easiest)

1. **Download the installer:**
   ```bash
   curl -O https://www.python.org/ftp/python/3.14.0/python-3.14.0-macos11.pkg
   ```

2. **Run the installer:**
   ```bash
   open python-3.14.0-macos11.pkg
   ```

3. **Click "Customize" on the installation type screen**

4. **Check the box for "Free-threaded Python" or "PythonT framework"**

5. **Complete installation**

6. **Verify installation:**
   ```bash
   python3.14t --version
   python3.14t -c "import sys; print(f'GIL disabled: {not sys._is_gil_enabled()}')"
   ```

   You should see:
   ```
   Python 3.14.0
   GIL disabled: True
   ```

### macOS/Linux - Build from Source

If the installer doesn't offer free-threaded option:

```bash
# Download source
curl -O https://www.python.org/ftp/python/3.14.0/Python-3.14.0.tar.xz
tar xf Python-3.14.0.tar.xz
cd Python-3.14.0

# Configure with free-threading
./configure --disable-gil --enable-optimizations --with-lto

# Build and install (macOS)
make -j$(sysctl -n hw.ncpu)
sudo make altinstall  # Install as python3.14t

# Build and install (Linux)
make -j$(nproc)
sudo make altinstall  # Install as python3.14t
```

This will take 10-15 minutes but gives you full control.

## Step 2: Create a Virtual Environment

Once Python 3.14t is installed, create a venv for your Bengal project:

```bash
# Navigate to your Bengal project directory
cd /path/to/bengal

# Create venv with Python 3.14t
python3.14t -m venv venv-3.14t

# Activate the venv
source venv-3.14t/bin/activate  # macOS/Linux
# OR
venv-3.14t\Scripts\activate     # Windows

# Verify you're using the free-threaded Python
python --version  # Should show Python 3.14.0
python -c "import sys; print(f'GIL disabled: {not sys._is_gil_enabled()}')"
```

## Step 3: Install Bengal

With the venv activated:

```bash
# Install Bengal in development mode
pip install -e .

# Or using uv (faster)
uv pip install -e .
```

## Step 4: Verify Performance

Test that Bengal is using free-threaded Python:

```bash
# Run the parallel rendering test
python tests/performance/test_process_parallel.py
```

You should see:
- ThreadPoolExecutor: **~1.9-2.0s** (500+ pages/sec) ✅
- ProcessPoolExecutor: Much slower due to pickling overhead

Compare this with regular Python 3.14 (if you have it):

```bash
# Deactivate current venv
deactivate

# Use regular Python 3.14
python3.14 tests/performance/test_process_parallel.py
```

You should see ThreadPoolExecutor is ~1.8x slower with the GIL.

## Using Bengal with Free-Threading

Once set up, Bengal **automatically detects** free-threaded Python and uses it for optimal performance. No configuration needed!

When you run `bengal site build`, you'll see:

```
● free_threaded_python_detected python_version=3.14.0 message="Using ThreadPoolExecutor with true parallelism (no GIL)"
```

### Fast Mode (Recommended)

For the absolute fastest build experience, use `--fast` mode:

```bash
# Maximum speed with clean output
PYTHON_GIL=0 bengal site build --fast
```

**What `--fast` mode does:**
- **Quiet output** for minimal overhead
- **Parallel rendering** guaranteed enabled
- **Clean, focused output** showing only what matters

**To suppress GIL warnings**, set `PYTHON_GIL=0` in your shell:

```bash
# One-time
PYTHON_GIL=0 bengal site build --fast

# Permanent (add to ~/.zshrc or ~/.bashrc)
export PYTHON_GIL=0
```

**Make fast mode permanent** by adding to your `bengal.toml`:

```toml
[build]
fast_mode = true  # Always use quiet + parallel
```

Then just run `PYTHON_GIL=0 bengal site build` for the cleanest experience.

## Switching Between Versions

You can keep both Python 3.14 and 3.14t installed:

```bash
# Regular Python (with GIL)
python3.14 -m venv venv-regular
source venv-regular/bin/activate

# Free-threaded Python (no GIL)
python3.14t -m venv venv-free-threaded
source venv-free-threaded/bin/activate
```

## Troubleshooting

### python3.14t not found

If `python3.14t` is not in your PATH after installation:

```bash
# macOS - Check if it exists
ls -la /Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14t
ls -la /usr/local/bin/python3.14t

# Add to PATH if needed
export PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH"
```

### File Watching in Dev Server

Bengal's dev server (`bengal site serve`) automatically avoids GIL warnings by using a polling-based file watcher when the GIL is disabled, rather than loading native extensions.

If you want to use the dev server without any file watching dependencies:

```bash
# Install without watchdog (optional)
pip install bengal

# Run dev server without file watching
bengal site serve --no-watch
```

Or install with dev server support:

```bash
# Install with file watching support
pip install bengal[server]

# Dev server with auto-reload (automatically uses polling in free-threaded Python)
bengal site serve
```

**Note:** In free-threaded Python with GIL disabled, Bengal automatically uses a pure-Python polling watcher instead of native file system extensions, so you won't see GIL warnings.

### Import errors with native extensions

Some packages may not yet support free-threaded Python. If you encounter import errors:

1. Check if a newer version of the package exists
2. File an issue with the package maintainer
3. Use regular Python 3.14 until the package is updated

Bengal's dependencies are tested with Python 3.14t and should work out of the box.

## Performance Notes

**What to expect:**
- **1.5-2x faster** multi-threaded rendering
- **No slowdown** for single-threaded operations (5-10% overhead per PEP 703)
- **Best results** on multi-core machines (4+ cores)
- **Same memory usage** as regular Python

**When it helps most:**
- Large site builds (100+ pages)
- Content-heavy pages with complex templates
- Sites with many API documentation pages
- Incremental builds touching multiple pages
