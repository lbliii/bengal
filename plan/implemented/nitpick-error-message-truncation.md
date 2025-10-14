# Error Message Truncation for Security

## Nitpick Addressed
Consider limiting error message length to prevent potential information disclosure through exception details.

## Analysis
Long error messages, particularly exception strings and tracebacks, can potentially disclose:
- Internal file paths and project structure
- Variable contents or user data in exception contexts
- Stack traces revealing implementation details
- In dev server HTTP responses, full errors visible in browser

Risk is low for local development but good practice to limit exposure, especially in error pages and logs.

Main exposure points identified:
- CLI error displays (build/serve commands)
- Dev server component preview error pages (full str(e) in HTML)
- Template rendering errors (full Jinja2 messages)
- Preprocessing warnings (full str(e) in logs)
- Strict mode RuntimeError messages

## Implementation
Added utility functions in `bengal/utils/logger.py`:
- `truncate_str(s, max_len=500, suffix=" ... (truncated)")`: General string truncation
- `truncate_error(e, max_len=500)`: Truncates str(e) with informative suffix showing truncation amount

Updated key locations to use truncation:
- **CLI Commands** (`build.py`, `serve.py`): `show_error(f"Failed: {truncate_error(e)}")`
- **Rendering Pipeline** (`pipeline.py`): Logger warnings and prints use `truncate_error(e)`
- **Template Renderer** (`renderer.py`): Strict mode `RuntimeError` uses `truncate_error(rich_error.message)`
- **Template Errors** (`errors.py`): `TemplateRenderError.message = truncate_error(error)`
- **Template Engine** (`template_engine.py`): Logger error uses `truncate_error(e, 500)`
- **Dev Server Handler** (`request_handler.py`): Component preview error page truncates to 2000 chars with security note

## Benefits
- Limits error messages to 500 chars by default (configurable via max_len)
- Preserves essential error information while preventing verbose disclosures
- Consistent truncation across CLI, logs, and HTTP responses
- Informative suffixes indicate when truncation occurred
- No impact on debug mode tracebacks (rich.traceback handles full stacks for uncaught errors)

## Testing
- Verified truncation in CLI build/serve error outputs
- Component preview errors now show truncated messages in browser
- Template errors in strict mode are limited
- Logs remain readable without excessive lengths

## Future Considerations
- Add config option for `error_truncate_len` (default 500)
- Extend to more logger calls via automatic truncation in BengalLogger.error()
- Consider sanitization for sensitive data (e.g., redact paths, API keys) in production builds
