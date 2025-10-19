# RFC: Multi-Language Autodoc via AST Parsing

**Date:** October 19, 2025  
**Status:** Exploration / Viability Analysis  
**Priority:** Medium (niche but valuable feature)

## Problem Statement

Bengal can auto-document Python code via AST parsing. Can we extend this to C, C++, JavaScript, TypeScript, and other languages using the same AST-based approach?

**Current limitation:**
- Bengal: Python only
- Sphinx: Python, C, C++, JavaScript, etc.
- Gap affects: CPython extensions, polyglot projects, system libraries

## Core Question: Can We AST-All-The-Things?

**YES!** Multiple viable approaches exist.

## Option 1: Tree-sitter (Universal Parser)

### What is Tree-sitter?

- **Universal parsing library** created by GitHub/Atom
- **50+ language grammars** (Python, C, C++, JS, TS, Rust, Go, etc.)
- **Incremental parsing** - only reparse changed sections
- **Error-tolerant** - works with incomplete/invalid code
- **Fast** - written in C, ~10-100ms per file
- **Python bindings** - `py-tree-sitter`

### Example: Parse JavaScript

```python
from tree_sitter import Language, Parser

# One-time setup
Language.build_library(
    'build/languages.so',
    ['tree-sitter-javascript', 'tree-sitter-python', 'tree-sitter-cpp']
)

# Load language
JS_LANGUAGE = Language('build/languages.so', 'javascript')
parser = Parser()
parser.set_language(JS_LANGUAGE)

# Parse
source = """
/**
 * Calculate sum of two numbers
 * @param {number} x - First number
 * @param {number} y - Second number
 * @returns {number} Sum
 */
function add(x, y) {
    return x + y;
}
"""

tree = parser.parse(bytes(source, "utf8"))
root = tree.root_node

# Walk AST
def walk(node, depth=0):
    print("  " * depth, node.type, node.text[:20] if node.text else "")
    for child in node.children:
        walk(child, depth + 1)

walk(root)
```

**Output:**
```
program
  comment /** * Calcula...
  function_declaration
    function function
    identifier add
    formal_parameters
      ( (
      identifier x
      , ,
      identifier y
      ) )
    statement_block
      { {
      return_statement
        return return
        binary_expression
          identifier x
          + +
          identifier y
      } }
```

### Extraction Logic

```python
def extract_js_functions(tree):
    """Extract JavaScript function declarations."""
    functions = []
    
    def visit(node):
        if node.type == 'function_declaration':
            # Extract name
            name_node = node.child_by_field_name('name')
            name = name_node.text.decode() if name_node else None
            
            # Extract parameters
            params_node = node.child_by_field_name('parameters')
            params = extract_parameters(params_node) if params_node else []
            
            # Extract JSDoc comment (previous sibling)
            jsdoc = extract_jsdoc(node.prev_sibling)
            
            functions.append({
                'name': name,
                'params': params,
                'doc': jsdoc,
                'line': node.start_point[0] + 1
            })
        
        for child in node.children:
            visit(child)
    
    visit(tree.root_node)
    return functions
```

### Pros
- ✅ **One solution for all languages**
- ✅ **Actively maintained** by GitHub
- ✅ **Fast** (~10-100ms per file)
- ✅ **Error-tolerant** (works with broken code)
- ✅ **Incremental** (reparse only changes)
- ✅ **Python bindings** exist
- ✅ **50+ languages** supported

### Cons
- ❌ **Build step required** (compile language grammars)
- ❌ **C dependency** (needs compiler)
- ❌ **Each language has different AST structure** (need custom logic per language)
- ❌ **Documentation extraction varies** (JSDoc vs Doxygen vs Rustdoc)
- ⚠️ **Not as rich as native parsers** (e.g., doesn't resolve types)

## Option 2: Language-Specific Parsers

### C/C++ via libclang

```python
import clang.cindex

def extract_cpp_functions(filepath):
    index = clang.cindex.Index.create()
    tu = index.parse(filepath, args=['-std=c++17'])
    
    functions = []
    
    def visit(cursor):
        if cursor.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            # Extract function info
            name = cursor.spelling
            return_type = cursor.result_type.spelling
            params = [
                {'name': arg.spelling, 'type': arg.type.spelling}
                for arg in cursor.get_arguments()
            ]
            
            # Extract Doxygen comment
            doc = cursor.raw_comment
            
            functions.append({
                'name': name,
                'return_type': return_type,
                'params': params,
                'doc': doc,
                'line': cursor.location.line
            })
        
        for child in cursor.get_children():
            visit(child)
    
    visit(tu.cursor)
    return functions
```

**Example C++ code:**
```cpp
/**
 * @brief Add two integers
 * @param x First integer
 * @param y Second integer
 * @return Sum of x and y
 */
int add(int x, int y) {
    return x + y;
}
```

**Extracted:**
```python
{
    'name': 'add',
    'return_type': 'int',
    'params': [
        {'name': 'x', 'type': 'int'},
        {'name': 'y', 'type': 'int'}
    ],
    'doc': '/**\n * @brief Add two integers\n * ...',
    'line': 6
}
```

### JavaScript/TypeScript via Acorn or Babel

```python
import subprocess
import json

def extract_js_with_babel(filepath):
    """Use Babel parser (via Node.js) to parse JS/TS."""
    script = """
    const parser = require('@babel/parser');
    const fs = require('fs');
    
    const code = fs.readFileSync(process.argv[1], 'utf8');
    const ast = parser.parse(code, {
        sourceType: 'module',
        plugins: ['typescript', 'jsx']
    });
    
    console.log(JSON.stringify(ast, null, 2));
    """
    
    result = subprocess.run(
        ['node', '-e', script, filepath],
        capture_output=True,
        text=True
    )
    
    ast = json.loads(result.stdout)
    return extract_functions_from_ast(ast)
```

### Pros
- ✅ **Language-native parsers** (most accurate)
- ✅ **Rich type information** (especially libclang)
- ✅ **Handles complex features** (C++ templates, TS types)
- ✅ **Official/well-maintained** tools

### Cons
- ❌ **Different tool per language** (complexity)
- ❌ **External dependencies** (LLVM for clang, Node.js for JS)
- ❌ **Heavyweight** (LLVM is large)
- ❌ **Integration complexity** (different APIs)

## Option 3: Shell Out to Existing Tools

### Doxygen for C/C++

```python
def generate_cpp_docs_via_doxygen(source_dir, output_dir):
    """Use Doxygen to generate XML, then parse it."""
    
    # Create Doxyfile
    doxyfile = f"""
    INPUT = {source_dir}
    OUTPUT_DIRECTORY = {output_dir}
    GENERATE_XML = YES
    GENERATE_HTML = NO
    GENERATE_LATEX = NO
    """
    
    # Run Doxygen
    subprocess.run(['doxygen', '-'], input=doxyfile, text=True)
    
    # Parse generated XML
    xml_dir = output_dir / 'xml'
    return parse_doxygen_xml(xml_dir)
```

### TypeDoc for TypeScript

```python
def generate_ts_docs_via_typedoc(source_dir, output_dir):
    """Use TypeDoc to generate JSON, then convert."""
    subprocess.run([
        'npx', 'typedoc',
        '--json', output_dir / 'docs.json',
        '--entryPointStrategy', 'expand',
        source_dir
    ])
    
    # Parse TypeDoc JSON
    with open(output_dir / 'docs.json') as f:
        typedoc_data = json.load(f)
    
    return convert_typedoc_to_markdown(typedoc_data)
```

### Pros
- ✅ **Proven tools** (industry standard)
- ✅ **Comprehensive** (handle edge cases)
- ✅ **Less code to maintain**
- ✅ **Rich output formats**

### Cons
- ❌ **External dependencies** (Doxygen, Node.js, TypeDoc)
- ❌ **Complex setup** (config files)
- ❌ **Not pure Python** (installation hassle)
- ❌ **Format conversion needed** (XML/JSON → Markdown)

## Recommended Approach

### Phase 1: Tree-sitter for JavaScript/TypeScript (Proof of Concept)

**Rationale:**
1. JavaScript/TypeScript is the most requested after Python
2. Tree-sitter has excellent JS/TS support
3. No heavy external dependencies
4. Can validate approach before expanding

**Implementation:**
```python
# bengal/autodoc/extractors/javascript.py

from tree_sitter import Language, Parser
from bengal.autodoc.base import DocElement, Extractor

class JavaScriptExtractor(Extractor):
    """Extract JavaScript/TypeScript API docs via tree-sitter."""
    
    def __init__(self):
        self.parser = Parser()
        self.parser.set_language(Language('build/languages.so', 'javascript'))
    
    def extract(self, source: Path) -> list[DocElement]:
        """Extract documentation from JS/TS file."""
        code = source.read_bytes()
        tree = self.parser.parse(code)
        
        elements = []
        self._visit(tree.root_node, elements, source)
        return elements
    
    def _visit(self, node, elements, source):
        """Walk tree and extract functions/classes."""
        if node.type == 'function_declaration':
            elements.append(self._extract_function(node, source))
        elif node.type == 'class_declaration':
            elements.append(self._extract_class(node, source))
        
        for child in node.children:
            self._visit(child, elements, source)
    
    def _extract_function(self, node, source):
        """Extract function declaration."""
        name = node.child_by_field_name('name').text.decode()
        params = self._extract_params(node.child_by_field_name('parameters'))
        jsdoc = self._extract_jsdoc(node.prev_sibling)
        
        return DocElement(
            type='function',
            name=name,
            signature=self._build_signature(name, params),
            docstring=jsdoc,
            source_file=source,
            line_number=node.start_point[0] + 1
        )
```

**Config:**
```toml
[autodoc.javascript]
enabled = true
source_dirs = ["frontend/src"]
output_dir = "content/api/js"
include_private = false  # Skip _private functions
```

### Phase 2: C/C++ via libclang (If Demand Exists)

**Rationale:**
- Needed for CPython extensions
- libclang is mature and well-supported
- Can handle complex C++ (templates, namespaces)

**Implementation:**
```python
# bengal/autodoc/extractors/cpp.py

import clang.cindex
from bengal.autodoc.base import DocElement, Extractor

class CppExtractor(Extractor):
    """Extract C/C++ API docs via libclang."""
    
    def extract(self, source: Path) -> list[DocElement]:
        index = clang.cindex.Index.create()
        tu = index.parse(str(source), args=['-std=c++17'])
        
        elements = []
        self._visit_cursor(tu.cursor, elements, source)
        return elements
```

### Phase 3: Other Languages (On Demand)

- Rust via tree-sitter or rustdoc JSON
- Go via tree-sitter or go/ast
- Ruby via tree-sitter
- etc.

## Implementation Considerations

### 1. Docstring/Comment Conventions

Each language has different documentation conventions:

**Python:**
```python
def add(x, y):
    """Add two numbers.
    
    Args:
        x: First number
        y: Second number
    
    Returns:
        Sum of x and y
    """
```

**JavaScript (JSDoc):**
```javascript
/**
 * Add two numbers
 * @param {number} x - First number
 * @param {number} y - Second number
 * @returns {number} Sum
 */
function add(x, y) { }
```

**C++ (Doxygen):**
```cpp
/**
 * @brief Add two integers
 * @param x First integer
 * @param y Second integer
 * @return Sum of x and y
 */
int add(int x, int y) { }
```

**Rust (rustdoc):**
```rust
/// Add two numbers
///
/// # Arguments
/// * `x` - First number
/// * `y` - Second number
///
/// # Returns
/// Sum of x and y
fn add(x: i32, y: i32) -> i32 { }
```

**Solution:** Need parsers for each doc format (we already have Google/NumPy/Sphinx for Python).

### 2. Type Information

**JavaScript/TypeScript:**
- No runtime types in JS
- TypeScript has type annotations in AST
- JSDoc has type comments

**C/C++:**
- Strong typing
- libclang provides full type info
- Templates complicate extraction

**Solution:** Extract type info where available, gracefully degrade otherwise.

### 3. Build System

Tree-sitter requires compiling language grammars:

```bash
# Setup script
git clone https://github.com/tree-sitter/tree-sitter-javascript
git clone https://github.com/tree-sitter/tree-sitter-python
git clone https://github.com/tree-sitter/tree-sitter-cpp

python -c "
from tree_sitter import Language
Language.build_library(
    'bengal/autodoc/languages.so',
    ['tree-sitter-javascript', 'tree-sitter-python', 'tree-sitter-cpp']
)
"
```

**Options:**
1. Ship pre-compiled `.so` files (platform-specific)
2. Compile on installation (requires compiler)
3. Optional dependency (autodoc.javascript extra)

### 4. API Design

```toml
# bengal.toml

[autodoc.python]
enabled = true
source_dirs = ["src/mylib"]
output_dir = "content/api/python"

[autodoc.javascript]
enabled = true
source_dirs = ["frontend/src"]
output_dir = "content/api/js"
docstring_style = "jsdoc"  # or "tsdoc"

[autodoc.cpp]
enabled = true
source_dirs = ["native/src"]
output_dir = "content/api/cpp"
docstring_style = "doxygen"
compiler_flags = ["-std=c++17", "-I/usr/include"]
```

## Estimated Effort

### JavaScript/TypeScript (tree-sitter)
- **Effort:** 2-3 weeks
- **LOC:** ~500-800 lines
- **Dependencies:** py-tree-sitter (~100KB)
- **Complexity:** Medium

### C/C++ (libclang)
- **Effort:** 3-4 weeks
- **LOC:** ~800-1200 lines
- **Dependencies:** libclang (~50MB)
- **Complexity:** High (C++ is complex)

### Universal System (tree-sitter for all)
- **Effort:** 4-6 weeks
- **LOC:** ~1000-1500 lines
- **Dependencies:** py-tree-sitter + language grammars
- **Complexity:** Medium-High

## Competitive Analysis

### Can Sphinx do this?

**Yes, but differently:**
- Sphinx doesn't use AST for C/C++
- Uses autodoc extensions that parse docstrings
- C domain requires manual directives (not auto-extracted)
- JavaScript domain is manual

**Bengal could be better:**
- True AST extraction (like we do for Python)
- No manual directives needed
- Automatic from source code

## User Demand

**Who needs this?**
1. **CPython extension authors** - NumPy, Pandas, scikit-learn (C/C++)
2. **Full-stack projects** - Python backend + JavaScript frontend
3. **Polyglot libraries** - One project, multiple language bindings
4. **System libraries** - Rust/Go CLI tools with Python bindings

**Market size:**
- Small percentage of Python projects (~5-10%)
- But high-value users (major libraries)
- Differentiation opportunity

## Recommendation

### Do It, But Phased

**Phase 1: JavaScript/TypeScript via tree-sitter**
- Most requested after Python
- Validates approach
- Relatively simple
- High value for full-stack projects

**Phase 2: C/C++ via libclang** (if demand exists)
- Needed for CPython extensions
- More complex but valuable
- Targets major library authors

**Phase 3: Universal tree-sitter** (if successful)
- Rust, Go, Ruby, etc.
- Competitive advantage
- "AST-all-the-things" vision realized

### Why This Makes Sense

1. **We already AST Python** - proven approach
2. **Tools exist** - tree-sitter, libclang are mature
3. **Differentiation** - Sphinx doesn't auto-extract C/C++/JS from AST
4. **Niche but valuable** - High-value users (library authors)
5. **Modern architecture** - Fits Bengal's philosophy

### Risks

1. **Complexity** - Each language is different
2. **Maintenance** - Need to keep up with language changes
3. **Dependencies** - External parsing libraries
4. **Edge cases** - Languages have complex features
5. **Limited demand** - Maybe only 5-10% of users need this

### Mitigation

1. **Start small** - JS/TS only, prove concept
2. **Optional features** - Extra dependencies, not core
3. **Community** - Let users contribute language support
4. **Document limitations** - Be clear about what we support

## Conclusion

**YES, we can AST-all-the-things!**

**Should we?** 
- Yes for JavaScript/TypeScript (Phase 1)
- Maybe for C/C++ (Phase 2, if demand)
- Probably not for everything else (wait for user requests)

**Bottom line:** This is a viable path to close the "multi-language domain" gap with Sphinx, using modern AST tooling. Start with JS/TS to validate, expand if successful.

---

**Next Steps:**
1. Create spike/prototype with tree-sitter + JavaScript
2. Extract a few JS functions/classes
3. Generate markdown output
4. Measure effort and complexity
5. Decide whether to proceed with full implementation

