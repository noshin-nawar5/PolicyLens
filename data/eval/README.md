# Evaluation data

`answer_key.csv` is your own hand-labelled ground truth: one row per requirement
with a label of `covered`, `partial` or `gap`.

Create a blank one after parsing the standard:

```bash
policylens init-key pci-dss-4
```

Then read each requirement and the sample policy and fill in the `label`
column BEFORE looking at the model's output. See `docs/EVALUATION.md`.
