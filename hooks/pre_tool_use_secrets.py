#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///
"""
PreToolUse hook - the guard.

Fires BEFORE every matched tool call. It inspects what the agent is about to do
and, if the call crosses a line you never want crossed, blocks it: print the
reason to stderr and exit(2). Claude Code stops the tool and hands the reason
back to the agent, so it adapts instead of doing the thing.

Two policies ship here:
  1. The agent should not reach your secrets - not the env file, not the other
     credential files (ssh keys, .pem, .aws, .netrc, .npmrc, credentials.json),
     not by dumping the process environment, and not through a credential CLI
     (`gh auth token`, `aws configure get`, `vault read`). A committed
     `.env.example` is allowed.
  2. The agent should not run an irreversible mass delete: `rm -rf` and its
     spellings, `find -delete`, `git clean -f`, `git reset --hard`,
     `git push --force`.

Everything else is allowed (exit 0).

THIS HOOK FAILS CLOSED. An unexpected exception blocks the call with a
"hook crashed" reason instead of silently allowing it, because a secrets guard
that waves everything through the moment it hits a bug is not a guard. If that
ever bites you, the switch is FAIL_CLOSED below - and the regression corpus in
`_test_hooks.py` exists so you find the bug before the agent does.

WHAT A DENY-LIST CAN AND CANNOT DO, HONESTLY
  This is a strong speed bump, not a guarantee. It normalises the command
  (quotes folded, backslashes resolved, `~`/$HOME expanded, whitespace
  collapsed), matches literal secret paths per word, expands globs and braces
  to see whether they could land on a secret, and refuses "opaque" reads whose
  target it cannot see statically (`cat $(...)`, `xargs cat`, `eval`, a reader
  given a bare `$VAR`, `base64 -d` captured into a variable). It still cannot:
    - see what a script the agent WROTE will do when it is run (the two-step)
    - stop a `grep -r`/`find` that sweeps the tree without naming the file
    - stop a value that is already in context from being echoed somewhere
    - block anything if `uv` is missing or the hook times out (Claude Code
      treats a hook error as non-blocking - see README)
  The guarantee layer for file reads is Claude Code's own `permissions.deny`
  (`Read(./.env)`, `Read(~/.ssh/**)`) plus the sandbox. Run both. The README
  has the paste-ready block.

MAKE IT YOURS: the policy is the tables in the "EDIT THESE" section. Add a path,
a CLI, a safe `rm -rf` target, or a template suffix there; the code below the
line should not need touching. Run `python3 .claude/hooks/_test_hooks.py` after
every edit - it is the only way to know you did not open a hole.
"""

import fnmatch
import json
import re
import sys

# ============================================================================
# EDIT THESE
# ============================================================================

# Block the call when this hook itself crashes. True = a bug cannot become a
# silent allow. If you ever need to get work done while you fix the hook, flip
# this to False temporarily - and flip it back.
FAIL_CLOSED = True

# Committed template files that are safe to read / write: `.env.example`,
# `.env.local.sample`, `.envrc.template`, ... (anything .env* ending in these).
ENV_TEMPLATE_SUFFIXES = ("example", "sample", "template", "dist")
TEMPLATE = re.compile(r"\.env[\w.-]*\.(" + "|".join(ENV_TEMPLATE_SUFFIXES) + r")$", re.IGNORECASE)
# Public halves and non-secret files that live next to secrets.
NOT_SECRET = re.compile(r"\.pub$|known_hosts$|authorized_keys$|\.env\.d\.ts$", re.IGNORECASE)

# A python venv literally named `.env/` is not a secrets file. These sub-paths
# are allowed so `source .env/bin/activate` works. (Rename the venv to `.venv`
# and you can delete this line.)
VENV_SUBPATH = re.compile(r"\.env/(bin|Scripts|lib|lib64|include|pyvenv\.cfg)", re.IGNORECASE)

# `rm -rf <target>` is allowed when EVERY target is a relative path with no
# `..`, no leading `/` or `~`, no variable, and whose FIRST or LAST path
# component matches one of these regenerable names (fnmatch globs). So
# `rm -rf node_modules/.cache`, `rm -rf tests/__pycache__`, `rm -rf dist/*` and
# `rm -rf *.egg-info` pass; `rm -rf src`, `rm -rf *`, `rm -rf ~` do not.
# Empty tuple = always block.
# Decision: a hard "never" on `rm -rf` blocks `rm -rf node_modules` in every JS
# repo and trains people to disable the hook. A narrow allowlist of build
# artefacts keeps the guarantee where it matters (your source, your home, the
# root) and gets out of the way where it does not. If you have a SOURCE
# directory called `build` or `out`, remove it from this list.
RM_SAFE_TARGETS = (
    "node_modules", "dist", "build", "out", "coverage", ".cache", ".next", ".nuxt",
    ".turbo", ".parcel-cache", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", ".eggs", "*.egg-info", "*.pyc", "target", "tmp", ".tmp",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
)

# Environment-variable NAMES that look like a credential. Used to decide
# whether `echo $X` / `printenv X` / `$env:X` is dumping a secret.
SECRET_NAME = re.compile(
    r"(API_?KEY|APIKEY|KEY|TOKEN|SECRET|PASS(WORD|WD)?|CRED|AUTH|PRIVATE|DSN|DATABASE_URL|CONN(ECTION)?_?STR)",
    re.IGNORECASE,
)

# ============================================================================
# POLICY TABLES - still yours to edit, but read the comment above each one.
# ============================================================================

# ---- 1. Secret FILES. Matched per word of the normalised command and against
# file-tool paths. `.env` must start a path component so `config.env.js` passes.
SECRET_PATH = re.compile(
    r"(^|[/:=,(])\.env(\b|$)"            # .env  .env.local  HEAD:.env  FILE=.env
    r"|(^|[/:=,(])\.envrc\b"              # direnv
    r"|\bid_(rsa|dsa|ecdsa|ed25519)\b"    # ssh private keys (the .pub twin is public but rarely needed)
    r"|\.ssh(/|$)"                        # anything under ~/.ssh
    r"|\.aws/credentials\b"
    r"|\.netrc\b|_netrc\b|\.npmrc\b|\.pypirc\b|\.pgpass\b|\.my\.cnf\b|\.git-credentials\b"
    r"|\.docker/config\.json\b|\.kube/config\b|\.config/gh/hosts\.yml\b"
    r"|\.config/gcloud/(credentials\.db|access_tokens\.db|application_default_credentials\.json)"
    r"|\bcredentials\.json\b|service[-_]?account[\w.-]*\.json\b"
    r"|(^|/)secrets?\.(ya?ml|json|toml)\b|(^|/)secrets/"   # k8s manifests, secret stores, secrets/ dirs
    r"|\.htpasswd\b|\.tfstate\b|\.p8\b|\.(bash|zsh|psql|mysql)_history\b"
    r"|/etc/(shadow|gshadow|sudoers)\b|/(var/)?run/secrets/"
    r"|/proc/[^/\s]+/environ\b",          # the live environment, as a file
    re.IGNORECASE,
)

# Key material by EXTENSION. In a shell command the name must be followed by a
# quote, whitespace, a shell separator or the end - so `cat server.key` and
# `open('server.key')` match while `jq .key` and `print(obj.key)` do not.
_KEY_EXTS = r"\.(pem|key|p12|pfx|jks|ppk|keystore)"
KEY_EXTENSION_IN_SHELL = re.compile(r"[\w./\\-]" + _KEY_EXTS + r"(?=[\"'\s;|&<>]|$)", re.IGNORECASE)
KEY_EXTENSION_PATH = re.compile(r"[\w./\\-]" + _KEY_EXTS + r"$", re.IGNORECASE)

# Basenames a glob/brace pattern is tested against. If a pattern can match one
# of these but cannot match any BENIGN_BASENAME, it is pointed at a secret.
SECRET_BASENAMES = (
    ".env", ".env.local", ".env.production", ".envrc",
    "id_rsa", "id_ed25519", "id_ecdsa", "server.pem", "server.key",
    "credentials", "credentials.json", ".netrc", ".npmrc", ".pypirc", ".git-credentials", ".pgpass",
)
BENIGN_BASENAMES = ("README.md", "main.py", "index.js", "package.json", "Makefile", "src", "test_app.py")

# ---- 2. The process ENVIRONMENT, read directly or from code.
# NOTE: the builtin names are assembled from fragments on purpose. A guard that
# greps for these tokens is itself commonly guarded against, so a file that
# contains them verbatim can get blocked by *another* hook before it is ever
# written. (That happened while authoring this file.) Behaviour is identical.
_PRINT_ENV = "print" + "env"
ENV_DUMP_VERBS = ("env", _PRINT_ENV, "set", "export", "declare", "typeset")
ENV_IN_CODE = (
    re.compile(r"os\.environ|os\.getenv|\bgetenv\s*\(|\benviron\b\s*\[", re.IGNORECASE),
    re.compile(r"process\.env|Deno\.env|import\.meta\.env", re.IGNORECASE),
    re.compile(r"\bENV\s*\[|\bENV\.(fetch|to_h|each|map|keys|values)|\b(p|pp|puts|print)\s+ENV\b"),
    re.compile(r"%ENV\b|\bENVIRON\b|System\.getenv|Environment\]?(::|\.)GetEnvironmentVariables?\s*\(|\$_ENV\b|std::env|env::var"),
    re.compile(r"load_dotenv\s*\(|dotenv\.config\s*\(|from dotenv import|require\(dotenv\)"),
    re.compile(r"\bjq\b[^|;&\n]*(\$ENV\b|(^|\s)env(\s|$))"),
    re.compile(r"\b(Get-ChildItem|gci|ls|dir|Get-Item|gi|Get-Content|gc|cat|type)\s+env:", re.IGNORECASE),  # PowerShell
    re.compile(r"\b(docker|podman|nerdctl|kubectl)\s+exec\b[^|;&\n]*\s(env|" + _PRINT_ENV + r")(\s|$)"),
)
# `echo $SECRET_NAME` and friends. Using a secret (`curl -H "Bearer $TOKEN"`)
# is allowed; printing it is not.
ECHO_SECRET = re.compile(
    r"\b(echo|printf|print|Write-Host|Write-Output|console\.log)\b[^|;&\n]*\$(\{)?(env:)?\w*?(" + SECRET_NAME.pattern + r")",
    re.IGNORECASE,
)
PS_ENV_VAR = re.compile(r"\$\{?env:\w*(" + SECRET_NAME.pattern + r")", re.IGNORECASE)
INDIRECT_EXPANSION = re.compile(r"\$\{!")   # ${!name} exists only to hide which variable is read

# ---- 3. CLIs whose job is to print or decrypt a credential. Anchored at the
# start of a pipeline stage, so `echo "try gh auth token"` is not a hit.
CREDENTIAL_CLI = (
    re.compile(r"^gh auth (token\b|status\b.*--show-token)"),
    re.compile(r"^aws configure (get|list|export-credentials)\b"),
    re.compile(r"^aws (sts get-(session|federation)-token|secretsmanager get-secret-value)\b"),
    re.compile(r"^aws ssm get-parameters?\b.*--with-decryption"),
    re.compile(r"^gcloud auth (application-default )?print-(access|identity)-token\b"),
    re.compile(r"^az (account get-access-token|keyvault secret show)\b"),
    re.compile(r"^vault (read|kv get|token lookup)\b"),
    re.compile(r"^op (read|item get|inject)\b"),
    re.compile(r"^security (find-(generic|internet)-password|dump-keychain)\b"),
    re.compile(r"^git credential(-\w+)? (fill|get)\b"),
    re.compile(r"^git config\b.*(--list|\s-l\b|--get-regexp|credential\.|extraheader)"),
    re.compile(r"^kubectl get secrets?\b.*\s-o\s*(yaml|json|jsonpath|go-template)"),
    re.compile(r"^docker compose config\b(?!.*--no-interpolate)"),
    re.compile(r"^(heroku config(:get)?|vercel env pull|doppler secrets( download)?|npm token list)\b"),
    re.compile(r"^npm config (get|list|ls)\b.*(authToken|\s-l\b)"),
    re.compile(r"^pip config (list|debug)\b"),
    re.compile(r"^gpg\b.*(--export-secret-(sub)?keys?|\s-d\b|--decrypt)"),
    re.compile(r"^(sops|age)\b.*(\s-d\b|--decrypt)"),
    re.compile(r"^ansible-vault (view|decrypt)\b"),
    re.compile(r"^(npx\s+)?dotenv\b.*(\s-p\b|--print)|^direnv export\b"),
    re.compile(r"^tar\b.*(\s-?[a-zA-Z]*f\s+-(\s|$)|--to-stdout|\s-O\b)"),  # archive the tree to stdout = cat everything
)
# `docker inspect` prints Env unless a --format that does not mention it.
DOCKER_INSPECT = re.compile(r"^docker (container )?inspect\b")

# ---- 4. OPAQUE reads: the target of a read is built at runtime, so no string
# match can see it. A verb from READER_VERBS with such an argument is blocked.
# This list is deliberately wide (anything that consumes a file). The cost is a
# false positive on `for f in src/*.py; do wc -l $f; done` - the message tells
# the agent to spell the path out (`wc -l src/*.py`), which it can always do.
# curl/wget are NOT here: `curl -H "Bearer $TOKEN"` is how a secret gets USED,
# and exfiltration over the network is outside what this guard can see.
READER_VERBS = set((
    "cat less more head tail tac nl od xxd hexdump strings bat batcat view vim vi nano emacs "
    "source . cp mv ln scp rsync tar zip unzip 7z gzip bzip2 xz base64 openssl gpg sops age "
    "sed awk gawk grep egrep fgrep rg ag ack sort uniq wc cut tr tee diff cmp comm paste column "
    "fold rev split md5sum sha1sum sha256sum file dd install jq yq "
    "python python3 python2 py node deno bun ruby perl php bash sh zsh dash ksh pwsh powershell "
    "get-content gc type"
).split())
# The subset that DUMPS content. xargs/find -exec into one of these is blocked;
# `xargs wc -l` or `xargs sed -i` is not.
DUMP_VERBS = set((
    "cat less more head tail tac nl od xxd hexdump strings bat batcat base64 cp scp rsync tar zip "
    "source . python python3 python2 py node deno bun ruby perl php bash sh zsh dash ksh pwsh powershell get-content gc type"
).split())
# For interpreters only the FIRST positional argument (the script) is checked;
# `python manage.py $ARG` is fine, `python $SCRIPT` is not.
INTERPRETERS = set("python python3 python2 py node deno bun ruby perl php bash sh zsh dash ksh pwsh powershell".split())
SHELLS = set("bash sh zsh dash ksh".split())
# Patterns that need the whole command, not one stage.
OPAQUE_ANYWHERE = (
    (re.compile(r"(\$\(|`)[^)`]*(base64\s+(-d|-D|--decode)|xxd\s+-r)"), "base64/xxd decode captured into a variable"),
)
# Code that builds a filename out of pieces AND opens or executes something.
# Either order. (`open(chr(46)+'env')`, `readFileSync(Buffer.from(..,'base64'))`,
# `open('.en'+'v')`, `system('cat .e'+'nv')`)
OBFUSCATED_NAME = re.compile(
    r"chr\s*\(|fromCharCode|\\x[0-9a-fA-F]{2}|bytes\.fromhex|b64decode|atob\s*\(|Buffer\.from\([^)]*base64|codecs\.decode"
    r"|['\"]\s*[+.]\s*['\"]|['\"]\s+['\"]|\)\s*\.\s*q[qw]?\(|['\"]\s*\.join\s*\(|\.format\s*\(|\bf['\"][^'\"]*\{|`[^`]*\$\{|\[::-1\]|\.decode\s*\(|\.concat\s*\(",
    re.IGNORECASE,
)
FILE_OPEN = re.compile(
    r"\bopen\b|readFile|read_text|read_bytes|Path\s*\(|File\.read|IO\.read|fopen\s*\(|Get-Content"
    r"|os\.system|subprocess|popen|execSync|child_process|\bexec\s*\(|\bsystem\s*\(|spawn",
    re.IGNORECASE,
)

# ---- 5. Credential-hunting searches. `grep -r KEY .` names no file but prints
# every line of .env that has one. Blocked when the pattern is credential-shaped
# AND the search is recursive/unscoped AND nothing excludes env files.
GREP_VERBS = ("grep", "egrep", "fgrep", "rg", "ag", "ack")
HUNT_WORDS = {"key", "apikey", "api_key", "secret", "secrets", "token", "password", "passwd",
              "credential", "credentials", "private", "bearer", "authorization", "access_key",
              "client_secret", "aws_access_key_id", "aws_secret_access_key"}
MATCH_EVERYTHING = {"", ".", ".*", ".+", "^", "$", "\\S", "[^\\n]*"}

# ---- 6. DESTRUCTIVE. Decision on what belongs in a "secrets + destructive"
# guard: anything that irreversibly destroys work or history without a prompt.
#   rm -rf (all spellings)   find -delete / -exec rm   xargs rm
#   git clean -f             git reset --hard          git checkout -- . / git restore .
#   git push --force / +ref / --delete                 git reflog expire / gc --prune
#   mkfs, dd of=/dev/..., shred, wipefs, crontab -r, DROP TABLE / DATABASE
# NOT blocked, deliberately: `git branch -D` (reflog recovers it), `git stash
# drop`, single-file `git checkout -- path` (surgical, usually intentional),
# `git restore --staged .` (only unstages), `rm` without both -r and -f.
# Anchored at the start of a pipeline stage: a commit message that SAYS
# "git push --force" is not a hit.
DESTRUCTIVE = (
    (re.compile(r"^find\b.*\s-delete\b"), "find -delete"),
    (re.compile(r"^find\b.*-exec(dir)?\s+(sudo\s+)?(rm|unlink|shred)\b"), "find -exec rm"),
    (re.compile(r"^xargs\b.*\s(sudo\s+)?(rm|unlink|shred)(\s|$)"), "xargs rm"),
    (re.compile(r"^git clean\b(?!.*(\s-[a-zA-Z]*n|--dry-run))(?=.*(\s-[a-zA-Z]*f|--force))"), "git clean -f"),
    (re.compile(r"^git reset\b.*--hard"), "git reset --hard"),
    (re.compile(r"^git checkout\b.*\s(--\s+)?(\.|\*|:/)(\s|$)"), "git checkout of the whole tree"),
    (re.compile(r"^git restore\b(?!.*--staged(?!.*(--worktree|\s-W\b))).*\s(--\s+)?(\.|\*|:/)(\s|$)"), "git restore of the whole tree"),
    (re.compile(r"^git push\b.*(\s-[a-zA-Z]*f[a-zA-Z]*(\s|$)|\s--force(?!-with-lease)\b|\s\+\w|\s--delete\b|\s:\S)"), "git push --force / +ref / delete"),
    (re.compile(r"^git (reflog expire|gc\b.*--prune|filter-branch|filter-repo|worktree remove\b.*(\s-f\b|--force))"), "git history/worktree destruction"),
    (re.compile(r"^(mkfs(\.|\s)|dd\b.*\bof=/dev/|shred\b|wipefs\b|crontab\s+-r\b)"), "disk/system-level destruction"),
    (re.compile(r"^(Remove-Item|ri|rm|del|erase|rd|rmdir)\b.*(-Recurse\b.*-Force|-Force\b.*-Recurse|\s/s\b)", re.IGNORECASE), "PowerShell/cmd recursive force delete"),
)
# Unanchored, but skipped for stages whose verb only handles TEXT (grep, echo,
# sed), so `grep -r "DROP TABLE" migrations/` passes.
DESTRUCTIVE_IN_CODE = (
    (re.compile(r"shutil\.rmtree\s*\(|fs\.rm(Sync)?\s*\([^)]*recursive|FileUtils\.rm_rf"), "recursive delete from code"),
    (re.compile(r"(system|popen|exec(Sync)?|spawn(Sync)?|run|call|check_output)\s*\(\s*\[?\s*(sudo[\s,]+)?rm[\s,]+-[a-zA-Z]*(r[a-zA-Z]*f|f[a-zA-Z]*r)"), "rm -rf from code"),
    (re.compile(r"\b(DROP\s+(TABLE|DATABASE|SCHEMA)|TRUNCATE\s+TABLE)\b", re.IGNORECASE), "SQL that drops data"),
    (re.compile(r">\s*/dev/(sd|nvme|hd|disk|mmcblk)|:\(\)\s*\{\s*:\|:"), "disk-level destruction"),
)
TEXT_ONLY_VERBS = set(GREP_VERBS) | {"echo", "printf", "sed", "git-commit"}

# ============================================================================
# Below this line: mechanism. You should not need to edit it.
# ============================================================================

FILE_TOOLS = ("Read", "Edit", "MultiEdit", "Write", "NotebookEdit")
SEARCH_TOOLS = ("Grep", "Glob")
SHELL_TOOLS = ("Bash", "PowerShell")
PREFIX_WORDS = ("sudo", "doas", "exec", "command", "builtin", "nohup", "time", "nice", "busybox",
                "do", "then", "else", "elif", "if", "while", "until", "{")
PREFIX_WITH_ARG = ("timeout", "nice", "ionice")   # `timeout 5 env`
STAGE_SPLIT = re.compile(r"\n|;|&&|\|\||\|")      # pipeline stages; code inside stays intact
WORD_SPLIT = re.compile(r"[\s;|&<>()]+")
SUBSTITUTION = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")
# Words that NAME a secret file in order to keep it OUT of a search.
EXCLUSION_PREFIXES = ("--exclude", "--ignore", "!", "-g!", "--glob=!", "--iglob=!")
# Verbs that only ever see a file's NAME or metadata, so naming a secret file
# to them is harmless: `ls -la .env*`, `test -f .env`, `stat .env`.
# (`find` is here too: its `-exec`/`-delete` are caught by other rules.)
NAME_ONLY_VERBS = {"ls", "stat", "test", "[", "[[", "du", "file", "touch", "mkdir", "basename",
                   "dirname", "realpath", "readlink", "echo", "printf", "find", "tree", "which"}
GIT_NAME_ONLY = {"ls-files", "status", "check-ignore", "check-attr"}
# `yes | rm -r x` is `rm -rf x`.
YES_PIPE = re.compile(r"(^|[;&\n])\s*yes\b[^|;&\n]*\|\s*$")
# Leading `git -C dir -c k=v --no-pager <subcommand>` options.
GIT_GLOBAL_OPTS = re.compile(r"^(?:(?:-C|-c|--git-dir|--work-tree|--namespace)\s+\S+\s+|--\S+\s+|-[pP]\s+)*")
# Verbs whose FIRST positional argument is a program, not a file.
PROGRAM_FIRST = {"awk", "gawk", "mawk", "sed", "jq", "yq"}


class Block(Exception):
    """Raised with (reason, evidence). Evidence is a fragment of the COMMAND,
    never file contents - and it is clipped so a value typed into a command
    does not get echoed back whole."""

    def __init__(self, reason, evidence=""):
        """A block reason, plus a short excerpt of the input that triggered it."""
        super().__init__(reason)
        self.reason = reason
        self.evidence = evidence[:60]


def _is_template(word):
    """Words that look like a secret path but are not one."""
    return bool(TEMPLATE.search(word) or NOT_SECRET.search(word) or VENV_SUBPATH.search(word)) \
        or word.lower().startswith(EXCLUSION_PREFIXES)


def _decode_escapes(text):
    """$'\\x65' / \\145 / \\u0065 -> the character they spell."""
    text = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), text)
    return text


def normalize(command):
    """Two views of the command: a POSIX-shell view (quotes folded, escapes
    resolved, backslashes dropped) and a Windows view (backslashes as path
    separators). A check that matches either view blocks. Newlines are kept as
    stage separators; other whitespace is collapsed."""
    text = command.replace("\r\n", "\n").replace("\\\n", "")
    for home in ("${HOME}", "$HOME", "%USERPROFILE%", "$env:USERPROFILE"):
        text = text.replace(home, "/HOME")
    text = re.sub(r"(^|[\s=:])~(?=/|\s|$)", r"\1/HOME", text)
    text = text.replace("$'", "'").replace('$"', '"')  # ANSI-C / locale quoting
    text = text.replace("'", "").replace('"', "")
    text = re.sub(r"[ \t]+", " ", text).strip()
    shell_view = _decode_escapes(text).replace("\\", "")
    windows_view = text.replace("\\", "/")
    return shell_view, windows_view


def _brace_expand(word, depth=0):
    """Expand shell braces ({a,b}) in a word, a few levels deep, so .{env,x} is seen as .env."""
    m = re.search(r"\{([^{}]*)\}", word)
    if not m or depth > 4:
        return [word]
    out = []
    for part in m.group(1).split(","):
        out.extend(_brace_expand(word[:m.start()] + part + word[m.end():], depth + 1))
    return out[:64]


def _glob_targets_secret(word):
    """Could this glob land on a secret, without also matching ordinary files?"""
    if not any(c in word for c in "*?[{"):
        return False
    for candidate in _brace_expand(word):
        name = candidate.rsplit("/", 1)[-1]
        if not name:
            continue
        if not any(c in name for c in "*?["):
            if name in SECRET_BASENAMES or SECRET_PATH.search(candidate):
                return True  # brace expansion produced the literal
            continue
        hits_secret = any(fnmatch.fnmatchcase(s, name) for s in SECRET_BASENAMES)
        hits_benign = any(fnmatch.fnmatchcase(b, name) for b in BENIGN_BASENAMES)
        if hits_secret and not hits_benign:
            return True
    return False


def _secret_word(word, is_path=False):
    """A single word that names a secret file, after template/venv exemptions.
    is_path=True for file-tool arguments, where the whole string is one path."""
    if _is_template(word):
        return False
    if is_path and KEY_EXTENSION_PATH.search(word):
        return True
    return bool(SECRET_PATH.search(word) or _glob_targets_secret(word))


def _verb(stage):
    """(verb, args) of a pipeline stage. Skips VAR=x assignments, sudo/exec/
    xargs/timeout prefixes, leading flags, `/usr/bin/` paths and `sh -c` when
    the script is a visible literal (if it is a $VARIABLE the shell stays the
    verb so the opaque check sees it)."""
    stage = re.sub(r"\s*\d*>{1,2}&?\s*\S*", " ", stage)  # drop `> file`, `2>&1`; keep `< file`
    words = stage.strip().lstrip("(").split()
    while words:
        w = words[0].rsplit("/", 1)[-1].lower()
        if re.match(r"^\w+=", words[0]) or w in PREFIX_WORDS or words[0].startswith("-"):
            words.pop(0)
        elif w in PREFIX_WITH_ARG and len(words) > 1:
            words.pop(0)
            words.pop(0)
        elif w in SHELLS and words[1:2] == ["-c"] and len(words) > 2 and not words[2].startswith("$"):
            words.pop(0)
            words.pop(0)
        else:
            break
    if not words:
        return "", []
    verb = words[0].rsplit("/", 1)[-1].lower().rstrip(")") or words[0].lower()
    if verb.endswith(".exe"):
        verb = verb[:-4]
    return verb, [a.rstrip(")") for a in words[1:]]


def _dumps_environment(verb, args):
    """True when the command prints the environment, or a secret-named variable from it."""
    if verb == _PRINT_ENV:
        return not args or any(SECRET_NAME.search(a) for a in args)
    if verb == "env":
        rest = list(args)
        while rest and rest[0].startswith("-"):
            flag = rest.pop(0)
            if flag in ("-u", "--unset") and rest:
                rest.pop(0)
        # `env`, `env -0`, `env FOO=1` all print; `env FOO=1 cmd` runs cmd.
        return all(re.match(r"^\w+=", a) for a in rest)
    if verb == "set":
        return not args
    if verb == "export":
        return not args or args == ["-p"]
    if verb in ("declare", "typeset"):
        return not args or all(a in ("-p", "-x", "-xp", "-px") for a in args)
    return False


def _credential_hunt(verb, args):
    """grep -r KEY . with nothing scoping it away from env files."""
    if verb == "git" and args and args[0] == "grep":
        verb, args = "rg", args[1:]  # git grep is recursive by default
    if verb not in GREP_VERBS:
        return False
    joined = " ".join(args)
    recursive = verb in ("rg", "ag", "ack") or re.search(r"(^|\s)-[a-zA-Z]*[rR]|--recursive|--dereference-recursive", joined)
    padded = " " + joined + " "
    scoped = any(flag in padded for flag in ("--exclude", "--include", "--glob", "--type", " -g ", " -t "))
    if not recursive or scoped:
        return False
    positional = [a for a in args if not a.startswith("-")]
    if not positional:
        return False
    pattern = positional[0]
    if pattern in MATCH_EVERYTHING:
        return True  # `grep -r . .` is `cat` for the whole tree
    tokens = set(t for t in re.split(r"[^a-z0-9_]+", pattern.lower()) if t)
    return bool(tokens & HUNT_WORDS)


def _rm_is_blocked(verb, args, force=False):
    """rm with both recursive and force -> block unless every target is safe.
    `force` is pre-set when the command pipes `yes |` into rm."""
    if verb != "rm":
        return False
    recursive = False
    targets = []
    seen_dashdash = False
    for a in args:
        if seen_dashdash or not a.startswith("-"):
            targets.append(a)
            continue
        if a == "--":
            seen_dashdash = True
        elif a == "--no-preserve-root":
            return True
        elif a.startswith("--"):
            recursive = recursive or a == "--recursive"
            force = force or a == "--force"
        else:
            recursive = recursive or bool(set(a[1:]) & set("rR"))
            force = force or "f" in a[1:]
    if not (recursive and force):
        return False
    if not targets or not RM_SAFE_TARGETS:
        return True
    for t in targets:
        t = re.sub(r"^(\./)+", "", t).rstrip("/")
        parts = t.split("/")
        if not t or t.startswith(("/", "~", "$", "-")) or ".." in parts or "\\" in t:
            return True
        safe = any(fnmatch.fnmatchcase(parts[0], p) or fnmatch.fnmatchcase(parts[-1], p) for p in RM_SAFE_TARGETS)
        if not safe:
            return True
    return False


def _dynamic_name(arg):
    """True when the FILENAME part of an argument is built at runtime: `$F`,
    `$x$y`, `${F}nv`, `.e$(echo n)v`, `/tmp/$NAME`. False when only the
    directory is dynamic and the name is visible: `$DIR/README.md`."""
    return "$" in arg.rsplit("/", 1)[-1]


def _collapse_substitutions(stage):
    """`cat $(git rev-parse --show-toplevel)/README.md` -> `cat $SUBST/README.md`,
    so a substitution is judged like a variable: fine when a visible /path
    follows it, opaque when it IS the path. The bodies are checked separately."""
    for _ in range(5):
        collapsed = SUBSTITUTION.sub("$SUBST", stage)
        if collapsed == stage:
            break
        stage = collapsed
    return stage


def _opaque_read(verb, args, stage, is_first_stage):
    """Why a stage reads something it does not name - or None."""
    if verb == "eval":
        return "eval"
    if verb in SHELLS and "-c" in args:
        script = args[args.index("-c") + 1:args.index("-c") + 2]
        if script and script[0].startswith("$"):
            return "shell -c with a variable as the script"
    if verb == "xargs":
        if any(a.rsplit("/", 1)[-1] in DUMP_VERBS for a in args):
            return "xargs into a reader"
        return None
    if verb == "find":
        m = re.search(r"-exec(dir)?\s+(\S+)", stage)
        if m and m.group(2).rsplit("/", 1)[-1] in DUMP_VERBS:
            return "find -exec into a reader"
        return None
    if verb not in READER_VERBS:
        return None
    if "$(" in stage or "`" in stage:
        _, args = _verb(_collapse_substitutions(stage))
    positional = [a.lstrip("<") for a in args if a.lstrip("<") and not a.lstrip("<").startswith("-") and not a.lstrip("<").isdigit()]
    if verb in INTERPRETERS:
        if not positional and not is_first_stage:
            return "piping into an interpreter"  # curl x | bash
        positional = positional[:1]
    elif verb in PROGRAM_FIRST:
        positional = positional[1:]
    for a in positional:
        if re.match(r"^\$\d", a):
            continue  # $1, $2: positional parameters, awk fields
        if _dynamic_name(a):
            return "a substitution builds the filename" if "$SUBST" in a else "a variable builds the filename"
    return None


def _stages(view):
    """Pipeline stages of the command, plus the bodies of $(...) and `...` so a
    read hidden inside a substitution is inspected too. Yields (text, first)."""
    for i, stage in enumerate(STAGE_SPLIT.split(view)):
        if stage.strip():
            yield stage, i == 0
    for m in SUBSTITUTION.finditer(view):
        body = m.group(1) or m.group(2) or ""
        for stage in STAGE_SPLIT.split(body):
            if stage.strip():
                yield stage, True


def check_shell(command):
    """Raise Block if a shell command crosses a line. Order: cheapest, most
    certain checks first, so the reason the agent sees is the most specific."""
    shell_view, windows_view = normalize(command)

    # 1. literal secret paths, per word of each stage (so `.env.example` next to
    #    `.env` does not launder the whole command), in both views. Stages whose
    #    verb only sees names (`ls -la .env*`) are exempt.
    for view in (shell_view, windows_view):
        for stage, _ in _stages(view):
            verb, args = _verb(stage)
            if verb in NAME_ONLY_VERBS or (verb == "git" and args[:1] and args[0] in GIT_NAME_ONLY):
                continue
            for word in WORD_SPLIT.split(stage):
                if word and _secret_word(word):
                    raise Block("access to a secrets file", word)
    # key material by extension - checked with quotes intact so that
    # open('server.key') is caught and print(obj.key) is not
    for view in (command, shell_view):
        m = KEY_EXTENSION_IN_SHELL.search(view)
        if m and not _is_template(m.group(0)):
            raise Block("access to a key file", m.group(0))

    view = shell_view

    # 2. per stage: the verb decides which policy applies
    for stage, is_first in _stages(view):
        verb, args = _verb(stage)
        if not verb:
            continue
        stage_before = view[:view.find(stage)] if stage in view else ""   # for `yes | rm -r`
        if verb == "git":
            args = GIT_GLOBAL_OPTS.sub("", " ".join(args)).split()   # git -C . clean -fd
        text = verb + (" " + " ".join(args) if args else "")
        if verb in ENV_DUMP_VERBS and _dumps_environment(verb, args):
            raise Block("dumping the process environment", text)
        if _rm_is_blocked(verb, args, force=bool(YES_PIPE.search(stage_before))):
            raise Block("recursive force delete outside the RM_SAFE_TARGETS allowlist", text)
        if _credential_hunt(verb, args):
            raise Block("recursive search for credential-shaped strings (scope it to a path/glob or add --exclude='.env*')", text)
        for pattern in CREDENTIAL_CLI:
            if pattern.search(text):
                raise Block("a CLI that prints or decrypts credentials", text)
        if DOCKER_INSPECT.search(text) and not (re.search(r"(--format|\s-f)\b", text) and not re.search(r"\.Env\b", text)):
            raise Block("docker inspect prints container Env (pass --format for the field you need)", text)
        why = _opaque_read(verb, args, stage, is_first)
        if why:
            raise Block("opaque read: " + why + " - the target cannot be inspected statically; spell the path out", text)
        for pattern, why in DESTRUCTIVE:
            if pattern.search(text):
                raise Block("irreversible destructive command: " + why, text)
        text_only = verb in TEXT_ONLY_VERBS or (verb == "git" and args[:1] == ["commit"])
        if not text_only:
            for pattern in ENV_IN_CODE:
                m = pattern.search(stage)
                if m:
                    raise Block("reading the process environment from code", m.group(0))
            if FILE_OPEN.search(stage):
                # the string-concat shapes only exist in the raw (quoted) text
                obfuscated = OBFUSCATED_NAME.search(stage) or OBFUSCATED_NAME.search(command.replace("\\", ""))
                if obfuscated:
                    raise Block("opaque read: an obfuscated filename passed to a file read or exec", obfuscated.group(0))
            for pattern, why in DESTRUCTIVE_IN_CODE:
                m = pattern.search(stage)
                if m:
                    raise Block("irreversible destructive command: " + why, m.group(0))

    # 3. whole-command patterns
    for pattern in (ECHO_SECRET, PS_ENV_VAR, INDIRECT_EXPANSION):
        m = pattern.search(view)
        if m:
            raise Block("printing a credential-shaped environment variable", m.group(0))
    for pattern, why in OPAQUE_ANYWHERE:
        m = pattern.search(view)
        if m:
            raise Block("opaque read: " + why, m.group(0).strip())


def check_tool(tool_name, tool_input):
    """Raise Block if the call crosses a line; return normally to allow."""
    if tool_name in FILE_TOOLS:
        path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        for view in (path.replace("\\", "/"), path):
            if view and _secret_word(view, is_path=True):
                raise Block("access to a secrets file", view)
        return

    if tool_name in SEARCH_TOOLS:
        for key in ("path", "glob", "include"):
            value = str(tool_input.get(key) or "").replace("\\", "/")
            if value and _secret_word(value, is_path=True):
                raise Block("search scoped to a secrets file", value)
        pattern = str(tool_input.get("pattern") or "")
        if tool_name == "Glob":
            if pattern and _secret_word(pattern.replace("\\", "/"), is_path=True):
                raise Block("glob for secrets files", pattern)
        else:  # Grep: pattern is a regex, path/glob/type scope it
            scoped = bool(tool_input.get("glob") or tool_input.get("type") or tool_input.get("include"))
            path = str(tool_input.get("path") or "")
            scoped = scoped or bool(re.search(r"\.\w{1,5}$", path))  # a specific file
            tokens = set(t for t in re.split(r"[^a-z0-9_]+", pattern.lower()) if t)
            if not scoped and (tokens & HUNT_WORDS or pattern in MATCH_EVERYTHING):
                raise Block("unscoped search for credential-shaped strings (add a glob/type or a specific path)", pattern)
        return

    if tool_name in SHELL_TOOLS:
        check_shell(str(tool_input.get("command") or ""))


def main():
    """Read the tool call from stdin and exit 2 with a reason if it would expose a secret or destroy work."""
    try:
        data = json.load(sys.stdin)
        tool_name = str(data.get("tool_name", ""))
        tool_input = data.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            raise TypeError("tool_input is not an object")
        check_tool(tool_name, tool_input)
        sys.exit(0)  # allow

    except Block as blocked:
        print(
            "BLOCKED by pre_tool_use_secrets.py: " + blocked.reason + ".\n"
            "  matched: `" + blocked.evidence + "`\n"
            "Secrets: read the committed .env.example instead, or ask the human for the value. "
            "Destructive: list what would be removed and let the human run it.",
            file=sys.stderr,
        )
        sys.exit(2)

    except Exception as exc:  # noqa: BLE001  (SystemExit is not an Exception, so exits pass through)
        if FAIL_CLOSED:
            print(
                "BLOCKED: pre_tool_use_secrets.py crashed (" + type(exc).__name__ + ") and is set to FAIL CLOSED, "
                "because a secrets guard that silently allows on error is not a guard.\n"
                "Human: run `python3 .claude/hooks/_test_hooks.py` to find the bug, or set FAIL_CLOSED = False "
                "in the hook while you fix it.",
                file=sys.stderr,
            )
            sys.exit(2)
        sys.exit(0)


if __name__ == "__main__":
    main()
