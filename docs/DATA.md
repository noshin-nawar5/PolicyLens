# Data

PolicyLens uses two kinds of input. Neither is confidential.

## 1. The standard: PCI DSS

- Free to download from the PCI Security Standards Council document library (https://www.pcisecuritystandards.org/document_library/). You may need to accept their terms and fill a short form.
- Save the PDF as `data/standards/PCI-DSS-v4_0_1.pdf`, or change the `pdf:` path in `config/standards.yaml` to match your file name.
- The PDF and the text extracted from it are git-ignored on purpose. The standard is copyrighted and must not be committed to a public repo.

If you download a different version, update `name` and `pdf` in `config/standards.yaml`.

### Checking the parse

After `policylens ingest pci-dss-4 --debug`:

1. Open `data/processed/pci-dss-4.json` and check 10 random entries against the PDF. Are IDs right? Is text cut or mixed with page headers?
2. Open `data/processed/pci-dss-4.raw.txt`. Find lines that repeat on every page (headers, footers, copyright). Add a regex for each to `noise_patterns` in `config/standards.yaml` and rerun.
3. Entries from tables (e.g. testing procedures) can add noise. If so, note it in your report's limitations.

## 2. The policy: fictional FinCo

`data/policies/finco_policy.md` is an invented software development and change management policy written for testing. Some topics are covered clearly, some in a single vague sentence, and some not at all. See [SAMPLE_POLICY_NOTES.md](SAMPLE_POLICY_NOTES.md).

To test your own policy, upload a `.md` or `.txt` file in the app, or pass `--policy path/to/file.md` on the command line. Do not commit real company documents to a public repo.
