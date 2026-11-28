# Triage of the review of the upstream 1.11.0 merge — November 2026

PR #7 merged `coleam00/skills` 1.11.0 into this fork and brought in four skills: `plan-with-priorities`,
`second-brain-prd`, `edit-video` and `agent-config-audit`. CodeRabbit reviewed that PR and left 99 comments:
37 Major, 52 Minor, 10 Trivial, none Critical. This file records what became of the 37 Major ones.

**Result: all 37 describe real behaviour. 32 are confirmed as written, 5 are real but overstated or a
deliberate trade-off, none is a false alarm.** One is fixed (F32, by PR #8). The other 36 are open.

Every finding except F32 is in code or text that came from upstream, at merge commit `5c5ce46`.

## Method and limits

- **Who checked.** Three independent checkers took F01–F31, one batch each. Each was told to try to refute
  the claim first, and to run the code rather than read it. F33–F37 were checked by reading only: they are
  about design guidance in a skill and its worked example, so there is nothing to execute.
- **How.** Every one of F01–F31 was reproduced by execution, on copies of the scripts with synthetic input.
  ffmpeg, node and headless Chrome were present. HyperFrames was replaced by a stand-in `npx`, `soundfile`
  by a small WAV shim, and the transcriber by a stub. No real credential or recording was used.
- **Not kept.** The repro drivers lived in a scratch folder and are not in this repository. The "Evidence"
  column gives the input that shows each defect, which is enough to rebuild them.
- **Not done.** No fix was written or tested. The Minor and Trivial comments were not triaged. No live
  Claude Code session, real HyperFrames render or real transcription was run.
- **Severity** is this triage's own judgment, not CodeRabbit's (which called all 37 Major).

## agent-config-audit: the auditor (`scripts/agent_config_audit.py`)

| ID | Where | Verdict | Sev. | What happens | Evidence | Smallest fix |
|---|---|---|---|---|---|---|
| F01 | `:432-433` | Confirmed | Medium | A literal credential in an MCP server's `args` is redacted in the output but never reported. | `"args": ["x==1.0","--api-key","FAKE..."]` gives flags `[]`; the same text in a hook `command` gives `secret-in-config`. | In `server()`, add `secret-in-config` when `redact(line, blobs=False) != line`. VS Code `task()` has the same gap. |
| F02 | `:167-168` | Confirmed | Medium | `${VAR:-fallback}` counts as a reference, so a literal fallback password is printed and not flagged. | `PASSWORD=${PASSWORD:-r4nd0m-p4ss} ./run.sh` is printed unchanged, `0 flagged`. | Accept `:-` only when the fallback is empty or itself a reference. |
| F03 | `:858-860` | Confirmed | Medium-low | A known-poisoned release pinned in a `Pipfile` or Poetry table is missed when there is no lockfile. | `agent-framework = "==1.26.1"` gives `[]`; the same pin in `Pipfile.lock` is caught. | Parse the dependency tables with `tomllib` and compare exact versions. |

## agent-config-audit: the skill text and remediation

| ID | Where | Verdict | Sev. | What happens | Evidence | Smallest fix |
|---|---|---|---|---|---|---|
| F04 | `SKILL.md:143-144` | Confirmed | **High** | The skill tells the agent to run `git log -p` on the config paths, which prints current and past secrets into the stored conversation. | A token committed and later replaced by `${API_TOKEN}`: the scanner prints `<redacted>`, `git log -p` prints the token twice. | Default to `git log --stat --format='%h %an %ad %s'`; show patches only through a redacting filter. |
| F10 | `references/remediation.md:68` | Partly | Medium | The suggested hook command leaves `${CLAUDE_PROJECT_DIR}` unquoted, so a project path with a space breaks it. It fails closed: every matched tool call is refused. | With `.../My Project`: `error: Failed to spawn: .../My`, exit 2, even for a harmless Read. | Quote the path, or use the exec (`args`) form. |

## agent-config-audit: the reference guard hook (`references/secrets-guard-hook.py`)

This file is an older, weaker copy of the guard this fork already hardened as `hooks/pre_tool_use_secrets.py`.
Run against the same inputs, the fork's hook blocks every bypass below and allows the two harmless commands
the reference wrongly blocks (`rm build/app-frontend.js`, `git rm docs/self-reference.md`).

| ID | Where | Verdict | Sev. | Allowed by the reference hook | Fork's hook |
|---|---|---|---|---|---|
| F05 | `:67` | Confirmed | Low | `echo "$DOCKER_AUTH_CONFIG"`, `echo $DATABASE_URL`, `printf %s "$API_KEY"` | blocks |
| F06 | `:112`, `:122` | Confirmed | **High** | `cat .env .env.example`; `cat ~/.ssh/id_rsa # .env.example`. The substring `.env.example` anywhere switches off every path check. | blocks |
| F07 | `:48` | Confirmed | Medium-high | `cat /tmp/signing.pem \| head`; `cat /tmp/server.key && echo ok`. The pattern is anchored to the end of the command. | blocks |
| F08 | `:136-139` | Confirmed | Medium | `rm -r -f`, `rm -f -r`, `rm --recursive -f` | blocks |
| F09 | `:62` | Confirmed | Medium-high | `cd /tmp && env`; `(env)`; `true && env > /tmp/x` | blocks |

Smallest fix for all five: ship the fork's hardened hook as the skill's reference instead of this copy.

## edit-video: wrong output shipped, or a check that passes when it should not

| ID | Where | Verdict | Sev. | What happens | Evidence | Smallest fix |
|---|---|---|---|---|---|---|
| F22 | `scripts/finalize.py:54` | Confirmed | **High** | The render's return code is never read. If the render fails, the previous render is packaged as a new version and reported OK. | A page with a missing image: `render.py` exits 1, `finalize.py` prints `myvideo_v1.mp4 ... OK`, exit 0. | Exit when the render's return code is non-zero. |
| F14 | `scripts/captions.py:22-31` | Confirmed | **High** | The phrase splitter loops forever when a phrase cannot fit. No output, no error. | 1080x1920 with `_keep: ["Model Context Protocol servers"]`: killed by `timeout 10`, exit 124. | Stop when `k > n`; let an over-long phrase stand alone. |
| F17 | `scripts/push.py:116-121` | Confirmed | Medium | An interrupted push render leaves a partial file that the next run moves over the kept composite. | Run 1 killed mid-encode, run 2 plain: `composite_a1.mp4` becomes the unreadable 3 MB partial. | Encode to a temp name, replace on success, then write the marker. |
| F13 | `scripts/cutpoints.py:209` | Confirmed | Medium | A splice outside the segment, or overlapping another, writes a negative-length part and restores audio that was cut. | Splice `[5,6]` with in point 10 gives `in 10.00 out 5.00 (-5.00s)`. Also fires with no override when the detected in point lands inside a splice. | Clamp splices to the segment, merge overlaps, exit if any part has out <= in. |
| F16 | `scripts/long_to_shorts.py:64` | Confirmed | Medium | Re-running with fewer spans leaves the old clips in place, and the next step picks them up. A span dropped on purpose comes back. | 3 spans then 2: `s1-face 03.mkv` remains, `init_workspace.py` reports `clips=3`. | Delete the name's old clips before writing. |
| F18 | `scripts/empty_card.py:39` | Confirmed | Medium | A missing or unreadable file reports "0 empty card stretches", exit 0. | `empty_card.py /nonexistent/draft.mp4` passes. | Exit when ffmpeg fails or no frame decodes. |
| F26 | `scripts/flicker_check.py:45-46` | Confirmed | Medium | A bad `--crop` or an `--ss` past the end reports "0 frames over", exit 0. | `--crop 0:0:4000:4000` passes; the same clip uncropped exits 1. | Exit 2 when ffmpeg fails or fewer than three frames are read. |
| F19 | `scripts/finalize.py:28-33` | Partly | Low | The sync check returns numbers for windows it could not measure. In every case tried it ended in a false CHECK, never a false OK. A cut under 5 s always prints CHECK. | Identical 4 s cut: `[-100.0, 0.0, 0.0, 0.0] CHECK`. | Skip windows outside the file or under an energy floor; print INCONCLUSIVE. |

## edit-video: broken or wrong render

| ID | Where | Verdict | Sev. | What happens | Evidence | Smallest fix |
|---|---|---|---|---|---|---|
| F29 | `scripts/hf/motion.py:164` | Confirmed | Medium | An apostrophe in a counter label produces invalid script and stops the whole timeline. | `label_to="It's ready"`: `SyntaxError: Unexpected identifier 's'`. | Emit the label with `json.dumps`. |
| F25 | `scripts/hf/engine.py:476` | Confirmed | Medium | After a picture-in-picture span, the next cross-fade fades the wrong scene, so two graphics stay stacked. Also fires on PIP, face, FULL, PIP. | After `full(30,"C")` then `pip(40,"D")`: opacity `C: 1.0, D: 1.0`. | Set `self.full_sid = scene` at that line. |
| F15 | `references/transitions.md:107` | Confirmed | Medium | The documented soft-wipe command omits `--kind`, so it defaults to `push` and exits with an error whose advice is wrong for this case. | The command as documented exits 1; with `--kind smoothleft` it works. | Add `--kind smoothleft` to that line. |
| F23 | `scripts/page_render.py:209-214` | Confirmed | Medium | Preview skips the clock on unselected frames but still fires actions, so a clicked element looks closed or in the wrong phase. Final renders are right. | `PREVIEW=1.0,3.0` with a click at 2.0 s: row height 0 px, not 400 px. | Tick every frame in preview; capture only the selected ones. |
| F11 | `scripts/common.py:182` | Confirmed | Medium | The loudness envelope builds one array for the whole recording: about 107 MB per minute. CodeRabbit's "second 8 GB array" did not appear. | 10 min costs 1.07 GiB, so about 9.7 GiB at 90 min. | Take the mean square in row chunks (bit-identical result). |
| F30 | `scripts/render.py:78` | Partly | Low-medium | Chunked renders take audio from the first media file by name, not from the face track. The standard page is correct. | `demo.mp4` + `face.mp4` gives the demo's audio. | Use the `src` of `<audio id="vo">`. |
| F28 | `scripts/hf/scenes.py:111` | Confirmed | Low | Typed text containing a literal `</script>` ends the inline script early. | A `typeon` of `echo "</script>" > a.html` loses the page's animation. | Escape `</` after `json.dumps`. |
| F24 | `scripts/page_render.py:66-74` | Confirmed | Low | A video seek slower than 1.5 s is recorded as done, leaving a stale frame. | Only with a seek delayed to 2.5 s; normal seeks take 50-100 ms. | Record the frame only after the seek is confirmed. |
| F27 | `scripts/hf/style.py:110` | Confirmed | Low | Assets are copied only when the source is newer, so rebuilding one project name from an older cut keeps the newer file. | Build tag v2 then v1: video from v2, captions from v1. | Copy when size or time differ. |

## edit-video: state, quoting and overwrites

| ID | Where | Verdict | Sev. | What happens | Evidence | Smallest fix |
|---|---|---|---|---|---|---|
| F12 | `scripts/fix_word.py:197` | Confirmed | Low | Media and config are updated before the final transcription. If that fails, `words.json` keeps the old words. Captions are re-transcribed, so they are unaffected. | Final transcribe raises: config points at the fixed clip, words still read the old phrase. | Transcribe first, then publish media, config and words together. |
| F20 | `scripts/finalize.py:52` | Partly | Low | The page name goes into a shell string unquoted. It is the operator's own argument, so this is a quoting bug, not a security hole. | A name with a space splits into two arguments. | Pass an argument list, no shell. |
| F31 | `scripts/render.py:26` | Confirmed | Low | Same pattern: `shell=True`, and `fps` from `config.json` is not forced to an integer. Injection needs a prepared workspace, which already holds scripts the user runs. | A workspace named `ws $100 tips` renders as `ws 00 tips`. | Argument lists, no shell; `int(cfg["fps"])`. |
| F21 | `scripts/finalize.py:44` | Confirmed | Low | The version number is chosen before the render and counts only the `.mp4`. Overlapping exports of one name, or a leftover `.srt`, are overwritten. | An orphan `Demo_v1.srt` is overwritten. | Pick the number just before the encode with an exclusive create. |

## second-brain-prd: design guidance (read only)

| ID | Where | Verdict | Sev. | What the guidance says | Smallest fix |
|---|---|---|---|---|---|
| F33, F36 | `SKILL.md:121`, `example-prd.md:641` | Confirmed | Low-medium | The vault merge driver "appends any lines local added that aren't already present". A line that also exists on the other machine is dropped, so identical log lines from two events collapse into one. | Append what local added relative to the ancestor, without comparing line content. |
| F34 | `SKILL.md:91` | Partly | Medium | On a guardrail `fail` the heartbeat aborts and saves the snapshot, so legitimate items in the same batch are never processed. This is stated as deliberate ("so one hostile message can't block every later run"), and the user is notified. | Quarantine the offending item and keep the rest for the next run. |
| F35 | `example-prd.md:372`, `:375` | Confirmed | Medium | Step 2 says to persist the state; step 5 says to commit it only after the notification succeeds. An implementer following step 2 loses the alert when notification fails. Together with F34, the skill and its example give three different rules for when state is saved. | State one rule in both files: save after a successful notification, and on `fail` save only the quarantined item. |
| F37 | `example-prd.md:181` | Confirmed | Low | The memory flush skips a session flushed under 60 seconds ago, so what is said between a pre-compaction flush and a session end inside that window is not saved. | Track the flushed transcript position, not the time. |

## README

| ID | Where | Verdict | What happens | Status |
|---|---|---|---|---|
| F32 | `README.md:34` | Confirmed | The install commands pointed at `coleam00/skills`, so users got upstream. | Fixed by PR #8. |

## Found by the checkers, not by CodeRabbit

All executed unless marked.

- **Reference guard hook:** `set`, `export -p` and `cat /proc/self/environ` are allowed. The fork's hook
  blocks all three.
- **Auditor:** an env map whose last secret-named key holds a clean `${REF}` prints as
  `{API_TOKEN=<redacted>`, with the closing brace missing.
- **Reference guard hook:** its docstring cites `hooks/README.md`, which the skill does not ship.
- **`render.py`:** a failed chunk leaves the old output in place, which widens F22.
- **`common.py:188-189` (read only):** `bands()` holds a 721 x frames STFT that looks larger than the array in F11.

## Suggested order

1. **Guard hook (F05–F09).** Replace the reference copy with the fork's hardened hook. One change, five findings.
2. **F04.** A wording change in `SKILL.md`; it stops the skill leaking the secrets it is looking for.
3. **F22 and F14.** One- and two-line fixes for the two `edit-video` defects that fail silently.
4. **Auditor false negatives (F01, F02, F03) and F10.** The skill has a 188-check test suite to extend.
5. **Report all of it upstream.** Every open finding is upstream's code. Fixes made only here will conflict
   with upstream's next release of the same files; upstream changed `edit-video` in seven commits between
   2026-11-09 and 2026-11-14.
