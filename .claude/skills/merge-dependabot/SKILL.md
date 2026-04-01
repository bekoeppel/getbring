---
name: merge-dependabot
description: Find and merge open Dependabot PRs after verifying CI passes
allowed-tools: Bash(gh *), Bash(git *)
---

# Merge open Dependabot PRs

Resolve all open Dependabot pull requests in this repo. Only Dependabot PRs -- never touch other PRs.

## Steps

1. List open Dependabot PRs:
   ```
   gh pr list --author "app/dependabot" --state open --json number,title,headRefName
   ```

2. If none are open, report "No open Dependabot PRs" and stop.

3. For each open Dependabot PR:
   a. Check CI status:
      ```
      gh pr view <number> --json statusCheckRollup,mergeable,mergeStateStatus
      ```
   b. If tests are still running, wait up to 2 minutes (check every 15s).
   c. If tests failed, report the failure and skip that PR.
   d. If tests passed and the PR is mergeable, merge it:
      ```
      gh pr merge <number> --squash
      ```
   e. After merging, pull the changes locally:
      ```
      git pull --rebase
      ```

4. Summarize what was merged and what was skipped.
