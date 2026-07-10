# Aliases cheatsheet

## Git

| Alias | Command | Notes |
|-------|---------|-------|
| `ga` | `git add` | |
| `gb` | `git branch` | `gba` all, `gbd` delete |
| `gc` | `git commit` | `gcs` signed, `gcam` amend |
| `gcout` | `git checkout` | |
| `gf` | `git fetch` | `gfa` all, `gfo` origin, `gfu` upstream, `gfp` prune |
| `gl` | `git log` | `gln` with filenames |
| `gs` | `git status` | `gsu` untracked, `gsi` ignored |
| `gd` | `git diff` | `gdh` HEAD, `gdhp` HEAD^, `gdn` names-only |
| `gpull` | `git pull` | `gpullr` rebase |
| `gpush` | `git push` | `gpusho` set upstream origin, `gpushf` force-with-lease |
| `greset` | `git reset` | `greseth` HEAD, `gresethp` HEAD^ |
| `gr` | `git restore` | `grs` staged |
| `grm` | `git rm` | `grmf` force |
| `gt` | `git tag` | `gts` sorted by date (last 24) |
| `gstash` | `git stash` | |

## Cargo (Rust)

| Alias | Command | Notes |
|-------|---------|-------|
| `cb` | `cargo fmt; cargo build` | `cbr` release, `cbe` examples, `cbnd` no-default-features |
| `ct` | `cargo test` | `ctl` lib, `cta` all-features, `ctr` release, `ctnc` nocapture |
| `clip` | `cargo clippy` | `clipa` all-targets, `clipf` fix, `clipau` allow-unused |
| `clipn` | `cargo +nightly clippy` | nightly variants: `clipnf`, `clipnt`, `clipna` |
| `cf` | `cargo fmt --all` | `cfc` check-only |
| `cc` | `cargo clean` | |
| `ccheck` | `cargo check` | |
| `cfix` | `cargo fix` | lib, allow-dirty |
| `cup` | `cargo update` | |
| `cr` | `cargo run --` | `crb` specific binary |
| `cbench` | `cargo fmt; cargo bench` | `cbenchn` nightly |

## System & Utils

| Alias | Command | Notes |
|-------|---------|-------|
| `ll` | `ls -alF` | `la` hidden, `l` compact |
| `eq` | `bc -l <<<` | Quick math: `eq '2^10'` |
| `make` | `make -j(ncpu-2)` | Parallel build, leaves 2 cores free |
| `pe` | `ps -ef` | Process list |
| `my_ip` | DNS lookup | Public IP via OpenDNS |
| `killbrowser` | kill top CPU browser | Chrome or Firefox |
| `locate` / `updatedb` | GNU locate | `glocate` / `gupdatedb` |
| `unhash` | `hash -r` | Clear command path cache |
| `xnargs` | `tr + xargs -0 -n1` | Pipe newline-separated input to xargs |

## Claude

| Alias | Command | Notes |
|-------|---------|-------|
| `clauder` | `claude --resume` | Resume last conversation |
| `claude4.6` | `claude --model claude-opus-4-6` | `clauder4.6` resume + opus |
| `claudeh` | `claude --model claude-haiku-4-5` | `clauderh` resume + haiku |
