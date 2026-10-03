# Release preparation

- Run make audit and retain the command log.
- Verify Python, API, frontend and CITATION.cff version 0.1.0.
- Verify both local demos, source labels and model metadata. Keep screenshots from actual streams.
- Verify complete held-out trial separation and no test-label adaptation.
- Confirm frozen benchmark hash, completed runs and probability artifacts.
- Generate all paper figures, tables and prose macros. Verify provenance.
- Compile main PDF and independently compile the arXiv bundle.
- Scan source and extracted PDF for semicolons, em dashes and missing references. Inspect rendered pages.
- Check MIT software license, separate dataset terms, citation and privacy/security documents.
- Do not include raw EEG, private sessions, model weights, virtual environments or node_modules in a release source tree.
- Review KNOWN_LIMITATIONS.md, especially absent physical hardware validation and offline trial filtering.
- Inspect CI on the actual hosting repository before tagging. CI is configured but cannot be claimed remotely run until pushed.
- Release is pre-1.0. Publishing or uploading to arXiv is a separate user action.
