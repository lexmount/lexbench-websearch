# Repository guidance

LexBench Web Search owns versioned task definitions, provenance, reference qualifications and provider-independent scoring. Browser Eval owns provider execution and reporting. Extend the existing owners; do not copy implementations between the repositories.

Use `uv run --frozen python` or Make targets for Python. Run `make check` before delivery. Tests must cover supported behavior, including accepted and rejected inputs. Packaging checks must load definitions from an installed wheel outside this checkout.

Code, comments and guides use English. Preserve the original language of dataset material and quoted evidence. README translations are optional. Keep source attribution and license notices with the data. Apply the existing Humanizer skill to public prose when available.

Commit reusable source, compact definitions, acceptance contracts and provenance. Keep measured outputs, API credentials, captures, generated reports and internal work notes outside Git. Do not add provider calls to the benchmark package.

Use feature branches and PRs. Do not merge PRs, push to main or force push.
