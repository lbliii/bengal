class CascadeScope:
    def __init__(self, max_depth: int = 3, current_depth: int = 0):
        self.max_depth = max_depth
        self.current_depth = current_depth

    def apply(self, metadata: dict, base_meta: dict):
        if self.current_depth >= self.max_depth:
            return metadata  # No leak

        # Merge with bounds
        for k, v in base_meta.items():
            if k not in metadata:
                metadata[k] = v
        return metadata


# In cascade apply
def apply_cascade(page, scope: CascadeScope):
    scope.current_depth += 1
    try:
        return scope.apply(page.metadata, page.section.metadata)
    finally:
        scope.current_depth -= 1
