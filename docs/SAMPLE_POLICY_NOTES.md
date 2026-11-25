# Notes on the sample policy

`data/policies/finco_policy.md` was written to contain a known mix, so the gap detector can be checked against a known answer.

| Topic | How it is treated in the sample |
|---|---|
| Secure coding guidelines, developer training, peer code review, automated code scanning | Covered with specific detail (section 3) |
| Separate environments, no live data in testing | Covered with specific detail (section 4) |
| Change requests, approvals, rollback, testing before release, emergency changes | Covered (section 5) |
| Vulnerability handling | One vague sentence (section 6): intended as **partial** |
| Third-party / open-source components | One vague sentence (section 7): intended as **partial** |
| Protection of public-facing web applications | One vague sentence (section 8): intended as **partial/gap** |
| Inventory and integrity control of scripts on payment pages, automated attack detection for web apps, a component inventory (SBOM) | Not mentioned: intended as **gap** |

This table says what the policy was written to contain. It is not the answer key. Your answer key must come from reading each parsed requirement and deciding for yourself, because the standard decides which requirement each topic maps to.

Feel free to edit the policy to create more interesting cases, such as a paragraph that uses the right words but states no actual control. That case shows why similarity is not compliance.
