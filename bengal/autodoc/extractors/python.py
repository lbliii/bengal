"""
Python API documentation extractor.

Extracts documentation from Python source files via AST parsing.
No imports required - fast and reliable.
"""

import ast
from pathlib import Path

from bengal.autodoc.base import DocElement, Extractor
from bengal.autodoc.docstring_parser import parse_docstring
from bengal.autodoc.utils import sanitize_text


class PythonExtractor(Extractor):
    """
    Extract Python API documentation via AST parsing.
    
    Features:
    - No imports (AST-only) - fast and reliable
    - Extracts modules, classes, functions, methods
    - Type hint support
    - Docstring extraction
    - Signature building
    
    Performance:
    - ~0.1-0.5s per file
    - No dependencies loaded
    - No side effects
    """
    
    def __init__(self, exclude_patterns: list[str] | None = None):
        """
        Initialize extractor.
        
        Args:
            exclude_patterns: Glob patterns to exclude (e.g., "*/tests/*")
        """
        self.exclude_patterns = exclude_patterns or [
            "*/tests/*",
            "*/test_*.py",
            "*/__pycache__/*",
        ]
    
    def extract(self, source: Path) -> list[DocElement]:
        """
        Extract documentation from Python source.
        
        Args:
            source: Directory or file path
            
        Returns:
            List of DocElement objects
        """
        if source.is_file():
            return self._extract_file(source)
        elif source.is_dir():
            return self._extract_directory(source)
        else:
            raise ValueError(f"Source must be a file or directory: {source}")
    
    def _extract_directory(self, directory: Path) -> list[DocElement]:
        """Extract from all Python files in directory."""
        elements = []
        
        for py_file in directory.rglob("*.py"):
            if self._should_skip(py_file):
                continue
            
            try:
                file_elements = self._extract_file(py_file)
                elements.extend(file_elements)
            except SyntaxError as e:
                print(f"  ⚠️  Syntax error in {py_file}: {e}")
            except Exception as e:
                print(f"  ⚠️  Error extracting {py_file}: {e}")
        
        return elements
    
    def _should_skip(self, path: Path) -> bool:
        """Check if file should be skipped."""
        path_str = str(path)
        
        for pattern in self.exclude_patterns:
            # Simple pattern matching
            if pattern.replace('*/', '').replace('/*', '') in path_str:
                return True
            if pattern.startswith('*/') and path.name.startswith(pattern[2:].replace('*', '')):
                return True
        
        return False
    
    def _extract_file(self, file_path: Path) -> list[DocElement]:
        """Extract documentation from a single Python file."""
        source = file_path.read_text(encoding='utf-8')
        
        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            raise
        
        # Extract module-level documentation
        module_element = self._extract_module(tree, file_path, source)
        
        return [module_element] if module_element else []
    
    def _extract_module(self, tree: ast.Module, file_path: Path, source: str) -> DocElement | None:
        """Extract module documentation."""
        module_name = self._infer_module_name(file_path)
        docstring = ast.get_docstring(tree)
        
        # Extract top-level classes and functions
        children = []
        
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_elem = self._extract_class(node, file_path)
                if class_elem:
                    children.append(class_elem)
            
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_elem = self._extract_function(node, file_path)
                if func_elem:
                    children.append(func_elem)
        
        # Only create module element if it has docstring or children
        if not docstring and not children:
            return None
        
        return DocElement(
            name=module_name,
            qualified_name=module_name,
            description=sanitize_text(docstring),
            element_type='module',
            source_file=file_path,
            line_number=1,
            metadata={
                'file_path': str(file_path),
                'has_all': self._extract_all_exports(tree),
            },
            children=children,
        )
    
    def _extract_class(self, node: ast.ClassDef, file_path: Path, parent_name: str = "") -> DocElement | None:
        """Extract class documentation."""
        qualified_name = f"{parent_name}.{node.name}" if parent_name else node.name
        docstring = ast.get_docstring(node)
        
        # Parse docstring
        parsed_doc = parse_docstring(docstring) if docstring else None
        
        # Extract base classes
        bases = []
        for base in node.bases:
            bases.append(self._expr_to_string(base))
        
        # Extract decorators
        decorators = [self._expr_to_string(d) for d in node.decorator_list]
        
        # Extract methods and properties
        methods = []
        properties = []
        class_vars = []
        
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method = self._extract_function(item, file_path, qualified_name)
                if method:
                    # Check if it's a property
                    if any('property' in d for d in method.metadata.get('decorators', [])):
                        properties.append(method)
                    else:
                        methods.append(method)
            
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                # Class variable with type annotation
                var_elem = DocElement(
                    name=item.target.id,
                    qualified_name=f"{qualified_name}.{item.target.id}",
                    description="",
                    element_type='attribute',
                    source_file=file_path,
                    line_number=item.lineno,
                    metadata={
                        'annotation': self._annotation_to_string(item.annotation),
                    },
                )
                class_vars.append(var_elem)
        
        # Combine children
        children = properties + methods + class_vars
        
        # Use parsed description if available
        raw_description = parsed_doc.description if parsed_doc else docstring
        description = sanitize_text(raw_description)
        
        return DocElement(
            name=node.name,
            qualified_name=qualified_name,
            description=description,
            element_type='class',
            source_file=file_path,
            line_number=node.lineno,
            metadata={
                'bases': bases,
                'decorators': decorators,
                'is_dataclass': 'dataclass' in decorators,
                'is_abstract': any('ABC' in base for base in bases),
                'parsed_doc': parsed_doc.to_dict() if parsed_doc else {},
            },
            children=children,
            examples=parsed_doc.examples if parsed_doc else [],
            see_also=parsed_doc.see_also if parsed_doc else [],
            deprecated=parsed_doc.deprecated if parsed_doc else None,
        )
    
    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        parent_name: str = ""
    ) -> DocElement | None:
        """Extract function/method documentation."""
        qualified_name = f"{parent_name}.{node.name}" if parent_name else node.name
        docstring = ast.get_docstring(node)
        
        # Skip private functions unless they have docstrings
        if node.name.startswith('_') and not node.name.startswith('__') and not docstring:
            return None
        
        # Parse docstring
        parsed_doc = parse_docstring(docstring) if docstring else None
        
        # Build signature
        signature = self._build_signature(node)
        
        # Extract decorators
        decorators = [self._expr_to_string(d) for d in node.decorator_list]
        
        # Extract arguments
        args = self._extract_arguments(node)
        
        # Extract return annotation
        returns = self._annotation_to_string(node.returns) if node.returns else None
        
        # Determine function type
        is_property = any('property' in d for d in decorators)
        is_classmethod = any('classmethod' in d for d in decorators)
        is_staticmethod = any('staticmethod' in d for d in decorators)
        is_async = isinstance(node, ast.AsyncFunctionDef)
        
        element_type = 'method' if parent_name else 'function'
        
        # Merge parsed docstring args with signature args
        merged_args = args  # Start with signature args
        if parsed_doc and parsed_doc.args:
            # Add descriptions from parsed docstring
            for arg in merged_args:
                if arg['name'] in parsed_doc.args:
                    arg['docstring'] = parsed_doc.args[arg['name']]
        
        # Use parsed description if available
        raw_description = parsed_doc.description if parsed_doc else docstring
        description = sanitize_text(raw_description)
        
        return DocElement(
            name=node.name,
            qualified_name=qualified_name,
            description=description,
            element_type=element_type,
            source_file=file_path,
            line_number=node.lineno,
            metadata={
                'signature': signature,
                'args': merged_args,
                'returns': returns,
                'decorators': decorators,
                'is_async': is_async,
                'is_property': is_property,
                'is_classmethod': is_classmethod,
                'is_staticmethod': is_staticmethod,
                'parsed_doc': parsed_doc.to_dict() if parsed_doc else {},
            },
            examples=parsed_doc.examples if parsed_doc else [],
            see_also=parsed_doc.see_also if parsed_doc else [],
            deprecated=parsed_doc.deprecated if parsed_doc else None,
        )
    
    def _build_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Build function signature string."""
        args_parts = []
        
        # Regular arguments
        for arg in node.args.args:
            part = arg.arg
            if arg.annotation:
                part += f": {self._annotation_to_string(arg.annotation)}"
            args_parts.append(part)
        
        # Add defaults
        defaults = node.args.defaults
        if defaults:
            for i, default in enumerate(defaults):
                idx = len(args_parts) - len(defaults) + i
                if idx >= 0:
                    args_parts[idx] += f" = {self._expr_to_string(default)}"
        
        # *args
        if node.args.vararg:
            part = f"*{node.args.vararg.arg}"
            if node.args.vararg.annotation:
                part += f": {self._annotation_to_string(node.args.vararg.annotation)}"
            args_parts.append(part)
        
        # **kwargs
        if node.args.kwarg:
            part = f"**{node.args.kwarg.arg}"
            if node.args.kwarg.annotation:
                part += f": {self._annotation_to_string(node.args.kwarg.annotation)}"
            args_parts.append(part)
        
        # Build full signature
        async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        signature = f"{async_prefix}def {node.name}({', '.join(args_parts)})"
        
        # Add return annotation
        if node.returns:
            signature += f" -> {self._annotation_to_string(node.returns)}"
        
        return signature
    
    def _extract_arguments(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict]:
        """Extract argument information."""
        args = []
        
        for arg in node.args.args:
            args.append({
                'name': arg.arg,
                'annotation': self._annotation_to_string(arg.annotation) if arg.annotation else None,
                'default': None,  # Will be filled in with defaults
            })
        
        # Add defaults
        defaults = node.args.defaults
        if defaults:
            for i, default in enumerate(defaults):
                idx = len(args) - len(defaults) + i
                if idx >= 0:
                    args[idx]['default'] = self._expr_to_string(default)
        
        return args
    
    def _annotation_to_string(self, annotation: ast.expr | None) -> str | None:
        """Convert AST annotation to string."""
        if annotation is None:
            return None
        
        try:
            return ast.unparse(annotation)
        except Exception:
            # Fallback for complex annotations
            return ast.dump(annotation)
    
    def _expr_to_string(self, expr: ast.expr) -> str:
        """Convert AST expression to string."""
        try:
            return ast.unparse(expr)
        except Exception:
            return ast.dump(expr)
    
    def _infer_module_name(self, file_path: Path) -> str:
        """Infer module name from file path."""
        # Remove .py extension
        parts = list(file_path.parts)
        
        # Find the start of the package (look for __init__.py)
        package_start = 0
        for i in range(len(parts) - 1, -1, -1):
            parent = Path(*parts[:i+1])
            if (parent / '__init__.py').exists():
                package_start = i
                break
        
        # Build module name
        module_parts = parts[package_start:]
        if module_parts[-1] == '__init__.py':
            module_parts = module_parts[:-1]
        elif module_parts[-1].endswith('.py'):
            module_parts[-1] = module_parts[-1][:-3]
        
        return '.'.join(module_parts)
    
    def _extract_all_exports(self, tree: ast.Module) -> list[str] | None:
        """Extract __all__ exports if present."""
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == '__all__':
                        # Try to extract the list
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            exports = []
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exports.append(elt.value)
                            return exports
        return None
    
    def get_template_dir(self) -> str:
        """Get template directory name."""
        return "python"
    
    def get_output_path(self, element: DocElement) -> Path:
        """
        Get output path for element.
        
        Examples:
            bengal.core.site (module) → bengal/core/site.md
            bengal.core.site.Site (class) → bengal/core/site.md (part of module)
        """
        if element.element_type == 'module':
            # Module gets its own file
            return Path(element.qualified_name.replace('.', '/') + '.md')
        else:
            # Classes/functions are part of module file
            parts = element.qualified_name.split('.')
            module_parts = parts[:-1] if len(parts) > 1 else parts
            return Path('/'.join(module_parts) + '.md')

