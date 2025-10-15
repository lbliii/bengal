# Benchmarking

This directory contains the benchmark suite for the Bengal static site generator. The benchmarks are designed to be run using `pytest` and the `pytest-benchmark` plugin.

## Setup

To run the benchmarks, you first need to install the required dependencies:

```bash
pip install -r requirements.txt
```

You also need to install the `bengal` package in editable mode from the root of the project:

```bash
pip install -e .
```

## Running the Benchmarks

To run the benchmarks, simply run `pytest` from the `benchmarks` directory:

```bash
pytest
```

This will run the benchmarks for all the scenarios defined in the `scenarios` directory. The results will be displayed in the console.