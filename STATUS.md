# STATUS — gta6-twitch-ccu-forecast-01

- Repo: https://github.com/rismzz/gta6-twitch-ccu-forecast-01
- Commit: (filled after push — see below)
- Competition: $250 USDC, 20 paid places. Entries close 2026-11-19T01:00:00Z
  (08:00 WIB Wed 19 Nov 2026). Final window starts 2026-11-20T00:00Z.
- Entry: `main.py` (Python 3.13, stdlib only), original code written in this
  build session across an initial write plus later revisions.

## Local verification (done 2026-11-17)

- Practice cases p00–p03: all 4 outputs valid (23 rows, hours 2–24,
  five non-decreasing quantiles each, 0 < q <= 1e9, <= 65,536 bytes).
- Determinism: two runs on all 4 practice cases byte-identical.
- Runtime: ~0.2 s for all 4 practice cases (limit 8 s per case).
- Leave-one-out over the kit's 27 rolling-midnight comparables, scored
  with the contest's log-scale pinball loss on the shipped `main.py`:
  pinball **0.2175**, 90% coverage 0.892, typical median miss ~41%,
  vs house baseline 0.2965 on the same curves. House baseline scores
  ~0.387 on the official practice cases.
- Stress test: hour-1 prints of 500k / 1M / 2M viewers all produce sane
  forecasts (hour-18 median 1.05× / 0.88× / 0.81× hour 1) thanks to the
  extrapolation cap in `main.py`.

## What remains for submit (NOT done in this task)

1. Fill in the commit SHA above after the push.
2. Transcript bundle via the kit CLI (`node cli/makefun.mjs bundle`,
   from the kit directory) including this build session + the parent
   session, with the run-record flags from SUBMIT-PATH.md
   (--prompt-file, --mcp none, --provider meta, --effort default,
   --harness-version, --muse-usage).
3. Submit: `node cli/makefun.mjs submit --competition
   gta6-twitch-ccu-forecast-01 --repo-url
   https://github.com/rismzz/gta6-twitch-ccu-forecast-01 --commit <sha>
   --bundle <file> --keypair ~/workspace/makefun/makefun-keypair.json`
   (do NOT submit before the pre-flight checks: owner.json present,
   README badges correct, About set, LICENSE present, repo public).
