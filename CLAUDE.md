# brownfield-compute

A data center a town would vote for: retired coal plant sites, shrinking towns, a data center
designed so the town comes out ahead, compared with a conventional one on the same site. Public on
GitHub. Read first:
- `README.md`: the question and the passes.
- `docs/PLAN.md`: status, decisions (D-numbers), what's next. **Start here.**
- `docs/SCORECARD.md`: the measures every design is scored on.
- `docs/RESEARCH.md`: sources, with their numbers and limits.
- `docs/CORTENFORGE.md`: what CortenForge lacks or does badly for this project (+ Suggestions).

## Rules

- Every number the model uses lives in `params/*.yaml` with value, low, high, unit, conf, source.
  Placeholders say `conf: placeholder` and are never passed off as sourced.
- Every number in the docs comes from a real run or a cited source.
- Always compare against the conventional design on the same site: the difference is the result.
- Check the model on known cases before trusting it (the site screen against sites real
  developers chose; physics against closed forms) in `brownfield check` and the tests.
- Each pass ends as a short report in `docs/` with figures and a "what we don't know" section.
- Plain language in public docs: "host-community benefits", not slogans. The vision lives in the
  README's "Why".
- Fusion is a site option in pass 5, never a dependency of the plan.
- CortenForge (`forge/`, from pass 3): published `cortenforge` 0.9 crates only, as an end user
  would. Log friction and every missing feature in `docs/CORTENFORGE.md` under its sub-crate
  (type, date, file:line) and add to its **Suggestions** list with what we built instead.
- Data: `data/raw/` is downloads (gitignored, re-fetched by the code); `data/` files in git are
  small derived tables with their source named.

## Working with Jon

- Commit only when he says "commit"; push only when he says "push".
- Ask before downloads over 1 GB and before deleting anything.
- Jon wants a firm steer toward work that will be taken seriously: say so when an idea won't
  hold up, and why.
