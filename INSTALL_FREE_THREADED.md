# Installing Free-Threaded Python 3.14

## Quick Guide

1. **Run the installer again:**
   ```bash
   open python-3.14.0-macos11.pkg
   ```

2. **Click "Customize" on the installation type screen**

3. **Check the box for "Free-threaded Python" or "PythonT framework"**

4. **Complete installation**

5. **Verify:**
   ```bash
   python3.14t --version
   python3.14t -c "import sys; print(f'GIL disabled: {not sys._is_gil_enabled()}')"
   ```

## Alternative: Build from Source

If the installer doesn't offer free-threaded option:

```bash
# Download source
curl -O https://www.python.org/ftp/python/3.14.0/Python-3.14.0.tar.xz
tar xf Python-3.14.0.tar.xz
cd Python-3.14.0

# Configure with free-threading
./configure --disable-gil --enable-optimizations --with-lto

# Build and install
make -j$(sysctl -n hw.ncpu)
sudo make altinstall  # Install as python3.14t
```

This will take 10-15 minutes but gives you full control.

## Test Performance

Once installed, run our benchmark:

```bash
# Test with free-threading
python3.14t tests/performance/test_process_parallel.py

# Compare to standard Python
python3.14 tests/performance/test_process_parallel.py
```

Expected improvement: **2-5x faster** rendering with free-threading!
