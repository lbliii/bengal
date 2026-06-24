`bengal build`, `bengal serve`, and `bengal preview` now stop with a plain-language warning when free-threading is not active, and ask you to confirm before running on a slower GIL-enabled interpreter.

Detection now distinguishes real `python3.14t` builds from standard `3.14.x` installs that falsely looked free-threading-capable. Use `--yes` or `BENGAL_ALLOW_GIL=1` to skip the prompt in CI.
