# M04 bilingual fit-fold notebook replay

Date: 2026-10-28

## Scope

The M04 magnetic fit-objective and validation lesson pair was added to the
source-to-content inventory after the repository grew from 58 to 60 notebooks.
This record covers only the two new notebooks and the documentation coverage
check; it is not full M04 inverse acceptance or product release acceptance.

## Fresh-kernel execution

From the product repository root, each notebook was executed separately in a
fresh kernel with the pinned notebook runner and an external device temp root:

```powershell
python scripts/run_notebooks.py --check --only notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb
python scripts/run_notebooks.py --check --only notebooks/es/03-magnetics/04-m04-fit-objective-validation.ipynb
```

Both commands reported one notebook executed top-to-bottom successfully; the
runner wrote no outputs into the repository. The committed outputs were then
regenerated from fresh kernels and both notebooks passed `--check` against a
second fresh execution. The static notebook gate passed for 60 mirrored files,
the docs matrix passed for 13 methods and the complete 60-file manifest, and
`scripts/check_content_standards.py` passed with no banned punctuation or emoji.
`git diff --check` passed.

## Input identity

Base revision: `ff2b3536bbccdc694c85f468c8217bfea91b8c4a`, plus the source changes
listed below. Hashes identify the exact working-tree inputs used for this run.

| Input | SHA-256 |
|---|---|
| [English lesson](../../notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb) | `99c2f3b84e9306dcce330eb3bf4a62d2943ff4a89f32a0cc9f007c3928db80a6` |
| [Spanish lesson](../../notebooks/es/03-magnetics/04-m04-fit-objective-validation.ipynb) | `c53f70d90c3d1d847c08c3d2c52456a26b681c6bd4487f6d1781ce4596b40b64` |
| [Lesson generator](../../scripts/build_m04_fit_fold_lessons.py) | `b3f3e6eaaa8786d59cd6c39ecf6c206633b1917ad5d90c34e3dd909c5228805a` |
| [Notebook runner](../../scripts/run_notebooks.py) | `ad328c622e42db2f0331ebb7ea1870eb808bf27775bfd6e179c5c9a197f4abb0` |
| [Documentation matrix checker](../../scripts/check_docs_matrix.py) | `1fecb92df7bab5aa93e9b763fe8451d0176e87855ad5bfed3c38b1337658aace` |
| [Notebook checker](../../scripts/check_notebooks.py) | `7abe880dee2a14b80e3786af55fc18ebefb26a4a521020aabb7c32688365190e` |
| [Content standards checker](../../scripts/check_content_standards.py) | `e7d38de7d5ea63d7af83ab3b07a68c20b3b392fad636d6f4ea157eefc0e7cd2c` |
| [Coverage manifest](source-content-coverage.json) | `a390ccd7429a465c8ef9729d61091be0f46d8467c419bc23c7929696e799296f` |
| [Source-to-content review](source-to-content-review.md) | `632073861b7523207bc5469421bc892645bd86195efeebf5b470ff4255aa86d1` |
| `data-pipeline/magnetic_fit_assembly.py` | `32e8d896dce432bb7363784c778075771eeae113dde80cdfec23057fa420ead3` |
| `data-pipeline/magnetic_fold_score.py` | `ec10a9b53f038150df69fd2c13ae2b6bc100ab08e68a115b0ab337fc46cad9ef` |
| `data-pipeline/magnetic_forward.py` | `d42dac128182e2f5014800309cdfb39ce1eb9add4d498736bba306170e7a3c5e` |
| `data-pipeline/magnetic_objective.py` | `61f9728768fe98659b4dd3632731ac43e329d2df7fe77c1780849ec647a6223c` |
| `data-pipeline/magnetic_regularization.py` | `e1b2487d8666335e51df9cb168e59cd0ad70edbf66a5898f35aaf90a5150ac80` |
| `tests/fixtures/magnetic_survey/generate.py` | `876c459f033ac60c41337220093910730beeba9d39ad58ed6e290716365fae04` |

The lesson assembles and differentiates a magnetic fit-fold objective and scores
a frozen model on separate development-validation rows. It explicitly reports
that it does not run an inversion. Its protocol fixture is not a provider
acquisition or field dataset. The replay does not establish M04 solver,
user-data, host, visual-owner, or release acceptance.
