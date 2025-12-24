# Archive of reference and generated artifacts

Created: 2025-12-24

This repository had several large or reference directories that should not be refactored in-place.
They have been archived and the originals moved to `archive/originals/` for safekeeping.

Archived items (tarballs saved in `archive/`):

- `ref/` -> `archive/ref_20251224_095425.tar.gz`
- `.ref/` -> `archive/.ref_20251224_095425.tar.gz`
- `reports/` -> `archive/reports_20251224_095425.tar.gz`
- `generated/` -> `archive/generated_20251224_095425.tar.gz`

Original directories were moved to:

- `archive/originals/ref_moved_20251224_095425/`
- `archive/originals/.ref_moved_20251224_095425/`
- `archive/originals/reports_moved_20251224_095425/`
- `archive/originals/generated_moved_20251224_095425/`

Notes:
- The archives are compressed tarballs and can be extracted with `tar -xzf <archive>`.
- If you want these directories removed entirely from the repo or from disk, confirm and I will delete them after your approval.
- Next step: scaffold the `singularity/` package and create compatibility shims for a smooth refactor.
