# Reference implementation and original builds (read-only)

- **`ref_plan.py`:** the reference planner and compiler. It reproduces all 16 files in `../expected/` byte-for-byte:

  ```zsh
  python3 ref_plan.py /tmp/out ../candidates_*.json
  ```

  Port it into `streamtv/builder/planner.py` and `compiler.py` (CURSOR_PROMPT §5.4). Tests may import it to cross-check the port. Never ship it as product code.
- **`extract_candidates.py`:** how `../candidates_*.json` were produced from the original build data. Kept for audit only; it expects the original build folders under `/home/claude/`.
- **`original_builds/`:** the build scripts and recorded research data exactly as they ran:
  - `xmas/` builds channel 1225. `yt_search_results_round1.txt` is the saved YouTube search output.
  - `holidays/` builds channels 101, 214, 401, 704, 1031 and 1128.
  - `primetime/` builds channel 1224.

  They use absolute `/home/claude/...` paths. They are evidence of the process, not code to run in the repo.
