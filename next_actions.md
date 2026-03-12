# Next Actions

- [x] Move integration-test pytest flags into shared `conftest.py` so `run_integration.sh --update` and `--realworld` work reliably.
- [x] Port the low-risk “History / decision log” wording from the demo into `tools/intent_viewer/index.html` so `sigil serve` matches the stronger framing.
- [x] Ignore clearly generated local artifacts: root `.coverage`, root `.intent/config.yaml` + `.intent/export.html`, `examples/demo-app/.intent/index/`, `examples/demo-app/tools/`, `tools/sigil-vscode/out/`, and `tools/sigil-vscode/package-lock.json`.
- [x] Remove the stray scratch `nonexistent/` repo contents so it no longer pollutes working-tree status.
- [ ] Review the remaining demo/viewer drift and port any additional low-risk UX improvements from `docs/demo/index.html` into `tools/intent_viewer/index.html`.
- [ ] Verify whether the new real-world test suite belongs in the default CI path or should stay opt-in via `run_integration.sh --realworld`.
