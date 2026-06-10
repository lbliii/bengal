Removed the experimental in-repo `chirpui` bridge theme so Bengal bundles a
single stable `default` theme. The bridge shell (24 templates, a small Bengal
bridge stylesheet, a bridge JavaScript file, and a `libraries = ["chirp_ui"]`
`theme.toml`) only re-exposed the generic theme library asset contract through a
bundled slug. Component-library integration such as Chirp UI is now delivered
through external theme packages (for example the chirp_theme package) using the
same library-provider contract, which remains covered by the provider and
metadata contract-shape tests.
