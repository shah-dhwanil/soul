# Persona asset split

The persona is split three ways: the canonical prompt is a hashed `prompt.md`, the fixed product constants (modes, dial floors, the four seeds, banned phrases, boundary scripts, crisis resources) are Python constants, and all per-user state lives in Postgres. We did not put the whole persona in YAML because the constants are read by type-checked code and not edited per deployment, while the prompt is edited often and needs version pinning and drift detection.
