# ergonomics

A collection of small macOS quality-of-life tools for the things Apple and
Microsoft forgot (or refused) to make easy.

## Tools

### 1. Sleep - Sleep keyboard shortcut

macOS has no built-in keyboard shortcut to put the machine to sleep.
This installs an Automator Quick Action that you can bind to any key combo.

**Install:**

```bash
./sleep/install.sh
```

**Then assign a keyboard shortcut:**

1. Open **System Settings > Keyboard > Keyboard Shortcuts > Services**
2. Find **Sleep** under General
3. Double-click the shortcut area and press `Ctrl+Option+S` (or your preferred combo)

### 2. out_for_a_walk - Teams walking status

Sets your Microsoft Teams status message to a random walking person emoji
with a random skin tone. Because telling your colleagues you're going for
a walk shouldn't require 47 clicks.

```
out_for_a_walk          # set status to a random walking emoji
out_for_a_walk --clear  # clear the status message
```

**How it works:** UI automation via macOS CGEvents (mouse clicks + clipboard
paste). No Microsoft Graph API, no third-party apps, no browser extensions.
The script activates Teams, clicks through the profile flyout, pastes the
emoji, and clicks Done. Your clipboard is saved and restored.

**Install:**

```bash
cd walk

# Set up the Python virtual environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Make it available system-wide
ln -s "$(pwd)/out_for_a_walk" /usr/local/bin/out_for_a_walk
```

**Prerequisites:**

- macOS (tested on Tahoe 26.x)
- Python 3.10+
- Microsoft Teams (new version, `com.microsoft.teams2`)
- Your terminal needs **Accessibility** permissions:
  System Settings > Privacy & Security > Accessibility

**Caveats:**

- The script locates UI elements by pixel offsets relative to the Teams
  window. If Microsoft redesigns the profile flyout, offsets may need
  updating (see `PROFILE_OFFSET`, `STATUS_MSG_OFFSET`, `DONE_BTN_OFFSET`
  in `out_for_a_walk.py`).
- Teams must be running (the script will launch/unminimize it if needed,
  but it needs to be installed).
- Don't interact with the mouse while the script is clicking through the
  UI (~5 seconds).

### 3. aliases - Bash alias manager

A curated collection of bash aliases for git, cargo, and everyday commands,
with a sync tool to keep the base aliases in step with the repo.

Includes 120+ aliases, bug-fixed and macOS-compatible.
See the [cheatsheet](aliases/CHEATSHEET.md) for a quick reference.

**How it works:**

- `~/.bash_aliases_base` — the portable base (synced with the repo)
- `~/.bash_aliases` — sources the base, then holds your local/machine-specific aliases

**Install (new machine):**

```bash
./aliases/install.sh     # copies base to ~/.bash_aliases_base,
                         # sets up ~/.bash_aliases to source it
source ~/.bash_aliases   # activate immediately
```

**Sync:**

```bash
./aliases/sync.sh        # show diff between local base and repo
./aliases/sync.sh pull   # pull repo changes into local base
./aliases/sync.sh push   # push local base changes into the repo
```

### 4. resources - Dev environment bootstrap

Installs GNU utils and essential dev tools via Homebrew, and sets up a
portable `.bashrc` config. Because the first thing you do on a new Mac is
spend two hours making the terminal not terrible.

**What it installs:**

- GNU coreutils, findutils, sed, tar, units, getopt, awk, make, grep, less
- git, gh, git-delta (side-by-side diffs)
- bash, bash-completion, shellcheck, tmux
- ripgrep, fd, fzf (Ctrl+R history search), jq, yq
- bat (syntax-highlighted cat), eza (modern ls), htop, tldr
- wget, tree, watch, bc, vim, gnupg

**Install:**

```bash
./resources/install.sh
```

This runs `brew bundle` with the included `Brewfile` and adds a single
`source` line to your `~/.bashrc` that loads the portable config from
`bashrc_base` (GNU utils PATH, prompt, history, completions, nvm).

Machine-specific config (secrets, tokens, tool-specific paths) stays in
your `~/.bashrc` — `bashrc_base` only manages the portable parts.

**Prerequisites:** [Homebrew](https://brew.sh)

## Why does this exist?

- **Sleep:** Apple provides no native keyboard shortcut to sleep.
  `Cmd+Option+Power` only sleeps the display. Creating a Quick Action and
  binding it to a shortcut is the only native-only solution.

- **out_for_a_walk:** Microsoft's Conditional Access policies block API
  access via the Graph API device code flow from unmanaged devices
  (error 53003). Since the Teams accessibility tree is completely opaque
  (Electron renders everything as empty `AXGroup` elements), the only
  reliable automation path is CGEvent mouse clicks at known pixel offsets.
  It's ugly, but it works.

## Authors

- **Mauro Lacy**
- **Claude Opus 4.6**

## License

MIT
