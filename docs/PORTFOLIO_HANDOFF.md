# Portfolio handoff

The planned four-stage project is complete at `v0.13.0`. Future changes should
be maintenance or a separately justified product milestone, not open-ended
feature accumulation.

## What this portfolio demonstrates

- a testing pyramid with isolated unit tests, service and data integration
  checks, and small user-facing E2E journeys;
- deterministic CI separated from optional external systems;
- branch-aware coverage, Python compatibility, Docker reproducibility, and
  retained evidence;
- explainable RAG evaluation across retrieval, answers, citations, safety,
  latency, consistency, and claim faithfulness;
- human labels as the authority before a candidate AI judge is trusted;
- clear communication of failed cases and measurement limits.

## Claims that are safe to make

> Built an AI quality engineering portfolio with Python, pytest, Playwright,
> GitHub Actions, Docker, and RAG evaluation; maintained 342 deterministic tests
> at 92.34% branch-aware coverage and validated retrieval, citations, prompt
> injection, stability, latency, and bounded claim faithfulness.

> Designed deterministic merge gates and kept paid external model comparisons
> opt-in, preventing network or provider variability from weakening normal CI.

> Built plain-English dashboards backed by versioned JSON evidence so technical
> and non-technical reviewers can understand both results and acceptance rules.

Do not describe the project as a certified compliance platform, a universal
hallucination detector, a production SLA benchmark, or proof that one model is
generally superior.

## Five-minute review path

1. Read the README problem statement and AI Quality Engineering table.
2. Open the RAG dashboard and explain one passing case and one diagnostic
   failure.
3. Open the benchmark dashboard and distinguish correctness from consistency.
4. Open the faithfulness dashboard and explain unfaithful recall and false
   negatives in plain English.
5. Show the CI workflow, test pyramid, and project-history pull requests.

## Maintenance policy

- Apply dependency and security updates through focused pull requests.
- Preserve deterministic offline gates; keep external provider tests opt-in.
- Regenerate evidence when evaluation data or scoring rules change.
- Version report schemas when meanings or required fields change.
- Add a product feature only when a real user need or target role exposes a
  meaningful gap.
- Record known limitations instead of converting them into false-green checks.

## Optional future products

The strongest adaptation is an AI knowledge-base quality platform for teams
testing internal policy, support, or documentation assistants. Natural later
milestones include document connectors, stored run history, scheduled
regression alerts, access control, and broader human-labelled datasets. Those
belong after portfolio release and should not block `v0.13.0`.

## Publishing v0.13.0 after closeout merges

The release tag must be created only after this closeout pull request is merged
and local `main` is synchronized. The tag should point to the closeout merge
commit so it includes the final history, demo, and release notes.

```bash
git switch main
git pull --ff-only origin main
make quality
git tag -a v0.13.0 -m "QA Compliance Sentry v0.13.0"
git push origin v0.13.0
gh release create v0.13.0 \
  --title "QA Compliance Sentry v0.13.0" \
  --notes-file docs/RELEASE_NOTES_V0.13.0.md
```

Creating and pushing the tag and GitHub release are deliberate external
publishing actions. They are not performed by the closeout branch itself.
