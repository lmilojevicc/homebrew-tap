# Brewnicle formula updates

`Formula/brewnicle.rb` starts HEAD-only. The **Update Brewnicle** workflow runs
hourly and manually from `main`. After the first published stable release at
<https://github.com/lmilojevicc/brewnicle/releases>, it verifies all four macOS/Linux
AMD64/ARM64 archives, their SHA-256 hashes, executable headers and notices before
atomically generating the stable formula. HEAD remains source-built with Go.

No release is a no-op only when the public API confirms an empty release list.
Drafts, prereleases, malformed responses, unexpected URLs, missing/duplicate
assets, checksum errors, unsafe archive members, and same-version changes fail
closed. Older versions never replace newer ones. Downloads have size limits and
30-second socket timeouts; the entire workflow has a 15-minute timeout. Archives
are inspected without extracting them or running the binary.

The workflow uses this tap's `GITHUB_TOKEN` to commit only the Brewnicle formula.
It needs no PAT or secret from Brewnicle. Tests and Ruby syntax checks run before
commit because token-generated pushes do not start another CI run. The current
unprotected `main` permits these bot commits; revisit that contract before adding
branch protection. A concurrent branch update causes a normal push failure, never
a force push. Retry on the next schedule or dispatch manually.

Local checks (Python 3.10+ and Ruby; no package installs required):

```sh
python3 -m unittest discover -s tests -v
ruby -c Formula/brewnicle.rb
python3 scripts/update_brewnicle.py --dry-run
```

The dry run performs real public downloads and all validation without writing.
Fixture tests are offline. Formula tests check installed files only: launching the
TUI would start network indexing, and Brewnicle has no version flag.

Release asset names and notice requirements are defined in Brewnicle's
[release guide](https://github.com/lmilojevicc/brewnicle/blob/main/docs/releasing.md).
A contract change needs coordinated updates to the generator, tests and formula;
do not hand-edit generated stable checksums to bypass validation. Unrelated
formulas are not managed by this workflow.
