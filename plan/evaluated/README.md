<!-- markdownlint-disable MD013 -->

# Evaluated Notes Archive

Updated: 2026-05-28

Most evaluated reports were removed after distillation. They were useful for
past prioritization, but current source and the active roadmap are more useful
for implementation.

## Kept Reference Notes

- `commonmark-deviations.md`: durable parser/spec behavior reference.
- `investigation-ruff-format-except-parenthesis.md`: durable Python 3.14 / PEP
  758 formatting explanation that prevents repeated false alarms.

## Distilled Findings

- Production maturity and maturity-assessment reports were replaced by the
  active roadmap snapshot.
- Cache/provenance quick wins from the 2026-03-14 evaluation have since shipped:
  corrupt provenance payload warnings, output source key normalization,
  constant-time output-dir emptiness checks, and cache recovery signaling. The
  remaining larger issues are cache-generation/divergence design, data-file
  fingerprint update cost, synthetic generated-key formalization, and broader
  warm-build parity/performance proof.
- Reload-tier, deployment, documentation completeness, stdlib, and
  free-threading audits should be re-run from source before they drive new work.
- Hardening proof notes were useful evidence for the May 2026 batch, but no
  longer need a full standalone body in planning.
