# Note 10 v136 result

**CI run:** `42163322909` failed on its first attempt  
**Scope:** typed native CAL, SCORE, G2D, and NPU terminal proof

## Host validation

The v136 new-only synthetic checks passed locally; earlier test suites were not replayed. The authenticated CI build failed during native compilation, before an image was accepted. Two compiler diagnostics had the same cause: a new CAL implementation identifier named `current` collided with Linux's `current` macro, which expands to `get_current()`.

No package was generated and no device queries or operations occurred. This run provides no XNU entry or full-boot evidence.