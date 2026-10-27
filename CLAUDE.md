# Team Workflow Rules (read before doing anything)

This project is built by multiple people, each using their own Claude Code.
GitHub is the single source of truth. `PROGRESS.md` is how we avoid doing the same work twice.

## 1. Before starting ANY session or task

1. Sync with GitHub first:
   ```bash
   git pull --rebase --autostash
   ```
   If there is a merge conflict, stop and tell the user. Never discard someone else's changes.
2. Read `PROGRESS.md` completely.
3. Tell the user in 2-3 lines:
   - what is currently being worked on and by whom
   - what is completed
   - what is next and who it is assigned to
4. If the user asks for a task that is already **Completed** or **In Progress by someone else**, warn them before writing any code.
5. If `PROGRESS.md` has a **🔴 HIGH PRIORITY** table with a task assigned to the user, tell the user about it first (with its instructions file in `docs/messages/`) and start with it before any other task, unless the user says otherwise.

## 2. Before starting work on a task (claim it)

1. Move the task to **In Progress** in `PROGRESS.md` with the user's name and today's date.
2. Commit and push only `PROGRESS.md` immediately, so teammates see the task is taken:
   ```bash
   git add PROGRESS.md
   git commit -m "progress: <name> started <task>"
   git pull --rebase --autostash && git push
   ```

## 3. After completing each task or meaningful piece of work

1. Update `PROGRESS.md`:
   - move the task to **Completed** (who, date, files changed, short note)
   - update **Next Up** with the next task and who will do it
   - add a line to **Activity Log**
2. Commit and push the code and `PROGRESS.md` together:
   ```bash
   git add <changed code files> PROGRESS.md   # stage specific files, never `git add -A`
   git commit -m "<short description of what was done>"
   git pull --rebase --autostash && git push
   ```
3. If the push fails, pull again, resolve, and retry. Never use `git push --force`.

## 4. Commit rules (important)

- Commits are made **on behalf of the user** using their own git identity (`git config user.name` / `user.email`).
- Do **NOT** add Claude as author or co-author.
- Do **NOT** add `Co-Authored-By: Claude ...` trailers.
- Do **NOT** add "Generated with Claude Code" or any Claude/AI mention in commit messages or PR descriptions.
- Commit messages: short, present tense, describe the change (e.g. `add data loader for training set`).
- Never commit secrets (`.env`, API keys), large datasets, or model weights.

## 5. Working together

- Only work on tasks assigned to the current user in `PROGRESS.md`, unless the user says otherwise.
- Do not edit files that another teammate is actively working on (see **In Progress**) without asking the user.
- Keep `PROGRESS.md` short and accurate. It is what teammates check before starting work.

## 6. Human labelling: NO LLM (strict, set by Prateek)

Risk-type labels (`data/external/risk_type_recheck.csv`, the kappa study, any `*_review.csv` / `*_check.csv` label column) must be made by the human alone, using `data/external/risk_type_categories.txt`.

- Claude must **refuse** to label, suggest, rank, "sanity check" or confirm a risk type for any record in these files, even one row, even if asked as a hint. Do not read the record trajectories to the user with an opinion attached.
- Claude must not write values into `recheck_type` / label columns. The human types them. Claude may only: run `python scripts/show_recheck.py <Name>`, explain the guide's rules in general terms (without applying them to a specific record), and check spelling/format after the human has finished.
- If the user insists, or labels already in the file were made with an LLM: do not commit them. Add a line to `PROGRESS.md` Activity Log and Blockers: `<date>, <name>: used an LLM to label <rows>; labels rejected, must be redone` — commit and push that, and tell the user to inform Prateek.

## Team Workflow

- **Before any task:** run `git pull --rebase --autostash`, read `PROGRESS.md`, and tell me in 2-3 lines what is in progress (and by whom), what is done, and what is next.
- If my task is already **Completed** or **In Progress by someone else**, warn me before coding.
- If `PROGRESS.md` has a **🔴 HIGH PRIORITY** task for me, tell me first and start with it.
- **When starting a task:** move it to **In Progress** in `PROGRESS.md` with my name and date, then commit and push only `PROGRESS.md`.
- **After finishing a task:** move it to **Completed** (who, date, files changed), update **Next Up** (task + who), add an **Activity Log** line, then commit the code and `PROGRESS.md` and run `git pull --rebase --autostash && git push`.
- Commit as the user (their git config). Never add Claude as author or co-author, never add `Co-Authored-By` or "Generated with Claude Code" lines.
- Never use `git push --force`. On a conflict, stop and ask me.
- Never commit secrets (`.env`, keys), datasets, or model weights.
