# Collector development checks

This file records development defects in the NEW collector, not defects in the user's experiment.

1. Credential-shaped data in a provider's model field could survive in derived diagnostics after raw-data exclusion. A failing regression test reproduced it; source-derived diagnostic fields are now withheld as well.
2. Compatibility testing on actual prior logs revealed the original v0.1 request hash binds BOTH endpoint and payload. The first collector draft incorrectly hashed payload alone. The check now uses the frozen public endpoint only when its canonical hash matches the manifest; otherwise verification is explicitly unavailable. No user logs were modified.

Tests in verification/ are software development evidence, not new LLM measurements. The complete original batch still needs to be supplied by the user; it was not reconstructed here.
