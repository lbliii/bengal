---
title: Code Tabs
description: Show code examples in multiple programming languages
type: doc
weight: 5
tags: ["directives", "code", "examples"]
toc: true
---

# Code Tabs

**Purpose**: Display code examples in multiple programming languages with tabbed interface.

## What You'll Learn

- Create multi-language code examples
- Use syntax highlighting
- Structure code comparison examples
- Best practices for code documentation

## Basic Syntax

Create code tabs with the `{code-tabs}` directive:

````markdown
```{code-tabs}
:id: unique-identifier

### Tab: Python

\`\`\`python
print("Hello, World!")
\`\`\`

### Tab: JavaScript

\`\`\`javascript
console.log("Hello, World!");
\`\`\`
```
````

**Format:** Similar to tabs directive but optimized for code.

## Use Cases

### Multi-Language Examples

Show the same functionality in different languages:

````markdown
```{code-tabs}
:id: hello-world

### Tab: Python

\`\`\`python
def greet(name):
    return f"Hello, {name}!"

print(greet("World"))
\`\`\`

### Tab: JavaScript

\`\`\`javascript
function greet(name) {
  return `Hello, ${name}!`;
}

console.log(greet("World"));
\`\`\`

### Tab: Ruby

\`\`\`ruby
def greet(name)
  "Hello, #{name}!"
end

puts greet("World")
\`\`\`
```
````

### API Client Examples

Show how to use an API in different languages:

````markdown
```{code-tabs}
:id: api-request

### Tab: Python

\`\`\`python
import requests

response = requests.get("https://api.example.com/users")
users = response.json()
\`\`\`

### Tab: JavaScript

\`\`\`javascript
fetch("https://api.example.com/users")
  .then(response => response.json())
  .then(users => console.log(users));
\`\`\`

### Tab: cURL

\`\`\`bash
curl -X GET https://api.example.com/users
\`\`\`
```
````

### Configuration Formats

Compare configuration file formats:

````markdown
```{code-tabs}
:id: config-formats

### Tab: TOML

\`\`\`toml
[server]
host = "localhost"
port = 8000
debug = true
\`\`\`

### Tab: YAML

\`\`\`yaml
server:
  host: localhost
  port: 8000
  debug: true
\`\`\`

### Tab: JSON

\`\`\`json
{
  "server": {
    "host": "localhost",
    "port": 8000,
    "debug": true
  }
}
\`\`\`
```
````

## Syntax Highlighting

Code tabs support full syntax highlighting:

**Supported languages:**
- Python, JavaScript, TypeScript, Ruby, PHP, Java, C#, C++, Go, Rust
- HTML, CSS, SCSS, Less
- Shell/Bash, PowerShell
- SQL, GraphQL
- TOML, YAML, JSON, XML
- Markdown, reStructuredText
- And many more via Pygments

## Best Practices

### Keep Examples Parallel

Show the same functionality in each language:

````markdown
✅ Good (parallel):
```{code-tabs}
:id: parallel-example

### Tab: Python
\`\`\`python
result = calculate(5, 3)
\`\`\`

### Tab: JavaScript
\`\`\`javascript
const result = calculate(5, 3);
\`\`\`
```

❌ Poor (different functionality):
```{code-tabs}
:id: non-parallel

### Tab: Python
\`\`\`python
# Installation instructions
pip install package
\`\`\`

### Tab: JavaScript
\`\`\`javascript
// Usage example
package.use();
\`\`\`
```
````

### Include Comments

Add explanatory comments in code:

````markdown
```{code-tabs}
:id: commented-example

### Tab: Python

\`\`\`python
# Import the required library
import requests

# Make a GET request
response = requests.get("https://api.example.com/data")

# Parse JSON response
data = response.json()
\`\`\`

### Tab: JavaScript

\`\`\`javascript
// Use fetch API for HTTP requests
fetch("https://api.example.com/data")
  .then(response => response.json())  // Parse JSON
  .then(data => console.log(data));   // Log result
\`\`\`
```
````

### Test All Code

Ensure all code examples:
- Run without errors
- Produce expected output
- Use current syntax
- Follow language conventions

## Quick Reference

**Basic code tabs:**
````markdown
```{code-tabs}
:id: example

### Tab: Python
\`\`\`python
code here
\`\`\`

### Tab: JavaScript
\`\`\`javascript
code here
\`\`\`
```
````

## Next Steps

- **[Tabs](tabs.md)** - General tabbed content
- **[Admonitions](admonitions.md)** - Highlight code notes
- **[Cards](cards.md)** - Visual layouts
- **[Kitchen Sink](../kitchen-sink.md)** - See examples

## Related

- [Markdown Basics](../writing/markdown-basics.md) - Code blocks
- [Directives Overview](index.md) - All directives
- [Quick Reference](quick-reference.md) - Syntax cheatsheet

