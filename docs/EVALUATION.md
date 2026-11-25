# Evaluation

## Goal

Measure how well the embedding-based gap detector agrees with a human reviewer.

## Procedure

1. Parse the standard and inspect the output (`docs/DATA.md`).
2. `policylens init-key <standard-id>` creates `data/eval/answer_key.csv` with an empty `label` column.
3. Read each requirement and the sample policy. Label each one `covered`, `partial` or `gap`. Do this **before** looking at the tool's output, otherwise the key is biased toward the tool.
4. `policylens gap ...` then `policylens eval`.
5. `policylens eval --sweep` shows how thresholds change the result.

## Metrics

Per class (covered / partial / gap): precision, recall, F1. Also macro-F1 and accuracy. For a compliance tool the most important number is **gap recall** (how many real gaps were found) because a missed gap is worse than a false alarm.

## Avoiding fooling yourself

- The sweep tunes thresholds on the same key it reports on, which overfits with a small key. Tune on half the requirements and report on the other half, or say clearly that results are tuned.
- One fictional policy and one section of one standard is a small test. State this in the report.
- Add at least one adversarial case to the policy: text that uses the right vocabulary but states no real control. Report whether the tool is fooled.
- Having a second person label the key independently, even for a subset, tells you how subjective the labels are.

## Reporting template

| Item | Value |
|---|---|
| Standard / sections | e.g. PCI DSS v4.0.1, Requirement 6 |
| Number of requirements labelled | |
| Policy | FinCo sample (fictional) |
| Embedding model | |
| Thresholds (covered / partial) | |
| Accuracy / macro-F1 | |
| Gap precision / recall | |
| Notable failure cases | |
