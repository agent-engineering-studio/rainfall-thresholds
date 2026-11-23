# Contributing

Issues and pull requests are welcome.

- Run `make check` before pushing: ruff, `mypy --strict` and pytest must be
  clean, the same gate CI runs.
- `app/` runs on the library of this repository (a path dependency), so its
  lock file holds the library's metadata: after changing the root
  `pyproject.toml`, run `uv lock` in `app/` too, or the `app` job fails.
- The package imports no sister library (dpc-radar, ispra-idrogeo, Limen);
  a test checks it. Notebooks and `app/` may use them (see the README).
- Commits follow [Conventional Commits](https://www.conventionalcommits.org/).
- Contributions are accepted under the project's license, Apache-2.0
  (section 5 of the license: inbound = outbound). No separate CLA.
