# ADR-0015 — CI/CD: GitHub Actions (Linux tests, Windows build + installer)

- Status: **Accepted** (Phase 1)

## Decision
Public repository `heyiamshohan-cloud/dentivaproofficial` with GitHub Actions:
- `ci.yml` (on push/PR): `lint` (ruff format/check, mypy), `tests-linux` (pytest,
  offscreen Qt), `tests-windows` (pytest + real print-path validation against
  "Microsoft Print to PDF" / "Microsoft XPS Document Writer"), `build` (PyInstaller
  on `windows-latest`, artifact upload), `installer` (Inno Setup, artifact upload).
- `release.yml` (on tag `v*.*.*` or manual dispatch): re-run the full gate, build,
  package, run the installer silently on a clean runner, execute
  `DentivaPro.exe --selftest`, then create the GitHub Release and attach the
  installer + checksums.
- Fallback required by the specification: if a GitHub Release cannot be published,
  the verified `.exe` is committed to the repository `dist/` directory.
- Branch policy: `main` protected; all work arrives via Pull Request; **the agent
  never merges** — only the user merges.

## Rejected
- Self-hosted runners (not available/needed).
- Third-party CI services (extra accounts/credentials for a public repo).
