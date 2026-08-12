# Deprecated VAP entrypoints

The following overlapping skill entrypoints are retired in favor of the single canonical `png-to-vap-mp4` Skill:

- `vap-generator`
- `vap-master`
- legacy fixed-layout `vap-video-generator`

Migration rules:

- Use `scripts/png_to_vap_mp4.py` for all new generation work.
- Legacy CLI aliases remain available: `--platform` -> `--target`, `--mode` -> `--layout`.
- The root `vap_master.py` remains only as a compatibility wrapper.
- Do not restore fixed `1668x1112`, `834x556`, or `1680x1680` layout constants.
- Do not remove this compatibility layer until downstream automation references have been audited.

The separate `opencode-skill-vap-tool` repository is an installer/toolchain helper rather than the canonical media-generation Skill; keep its scope limited to installing/verifying VapTool to avoid trigger overlap.
