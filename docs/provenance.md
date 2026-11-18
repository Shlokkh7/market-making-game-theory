# Source and figure provenance

This repository preserves the three recovered original Python scripts and the latest supplied report figures. Newly executed simulations are evidence for the preserved implementation; their output files are kept separately from the selected report images.

## Preserved scientific source

The original scripts were recovered from the earlier project conversation attachments, not reconstructed from the audit summary. Their byte-level SHA-256 digests are:

| File | SHA-256 |
|---|---|
| `mm_dynamic.py` | `5d3cbefe9870207d7b4fe1b18fa1a225967b23aadb6f328ac96bd52e64a33087` |
| `mm_bayes.py` | `4ac175f71ced092dc6db6f4720b7592ed504cfed562247232fd36f555ad4e293` |
| `simulate_game.py` | `182665d3d6818c834995c7b47e2307508734c318e059c4f8ca7c55d8400969da` |

The initial local preparation commit is `e654e6a16150152ce09a65b3da704bdb4e2c2226`. It identifies these source files and the selected report figures. Run manifests retain this local snapshot identifier and the per-file hashes. Publication uses the authenticated GitHub browser because the local Git authentication process is blocked; the local preparation commit is therefore not presented as a commit available from GitHub. The published `v1.0-course-submission` tag and final handoff identify the actual GitHub submission commit. Per-file source hashes connect that published tree to the executed local snapshot.

## Selected submission figures

On 18 November 2026, the two latest supplied PNGs were compared with extracted raster images from the supplied six-page `market_making_ieee.pdf`. The images were decoded to RGB and compared pixel-for-pixel. Both match exactly, and the PNG alpha channels are fully opaque. The TeX source also references the corresponding filenames.

| Repository figure | Report location | Dimensions | PNG SHA-256 |
|---|---|---|---|
| `figures/fig_sim_deviation.png` | Figure 1, PDF page 5, image `Im1.png` | 1050 x 660 | `f5497292e74f4e46728afc3f43f5acd5b7ab80acb3be00e8880d937fe56fd6d9` |
| `figures/fig_sim_belief.png` | Figure 2, PDF page 6, image `Im2.png` | 1125 x 660 | `9fea1fa14aed820c78a7680cc312fce0bd39435252095a1ca36dc543da578347` |

This establishes **which displayed images belong to the supplied report**. It does not establish identical PNG container bytes inside the PDF, or the historical simulation command. Decoded-pixel hashes and comparison evidence are recorded in [report-figure-evidence.json](report-figure-evidence.json).

The latest PNG metadata identifies **Matplotlib 3.10.8**. Earlier audited copies with the same filenames identified 3.10.0 and differed in content. The latest images are the submission references; earlier metadata must not be assigned to them.

## Generating-run provenance

`simulate_game.py` contains the plotting routines for both named images. Its source-defined full mode uses 40,000 A paths and 20,000 B paths, with seeds 7 and 8 respectively; quick mode uses 4,000 and 2,000 paths. Both modes save the same filenames. The report describes the full-mode settings, but that description alone does not prove which command generated the selected files.

| Provenance question | Evidence status |
|---|---|
| Are these the images displayed in the supplied PDF? | Established: exact decoded RGB equality. |
| Are the original PNG bytes preserved in `figures/`? | Identified by the SHA-256 digests above. |
| Is compatible generation code present? | Established by inspection of the preserved plotting routine. |
| Is the historical generating command known? | Unresolved from the supplied report and image files alone. |
| Are historical Python and NumPy versions known? | Unresolved. PNG software metadata does not establish them. |
| Has a newly executed run matched the reference bytes or pixels? | Established for both full-run figures: every decoded RGBA pixel matches, but PNG container bytes differ. See [the full-run comparison](../results/full/figure-comparison.json). |

The tested environment for new runs is recorded as current validation evidence, not inferred historical provenance. Exact PNG byte equality is stronger than pixel equality; pixel equality is stronger than visual similarity. Each comparison should state which level was tested.

## Full-run figure reproduction

The completed full run used the preserved source, 40,000 A paths, 20,000 B paths, seeds 7 and 8, 100 solver steps, and ten simulation substeps. Both generated PNGs have **zero differing decoded RGBA pixels** compared with the selected report references:

| Full-run output | Generated PNG SHA-256 | Decoded RGBA comparison with report reference |
|---|---|---|
| `results/full/fig_sim_deviation.png` | `9edf2f475ae5f4a23fc4e3fc7b2fc97098c1728a77afb4b7bbd5f46ca4748e62` | Exact equality; 0 different pixels |
| `results/full/fig_sim_belief.png` | `356dd89a2b88d091114bb0001c3c2c301b60db4b4258f28de3efcc7978b5b93d` | Exact equality; 0 different pixels |

The generated PNG byte hashes differ from the reference hashes even though their complete decoded images agree. Original reference files remain untouched in `figures/`; generated copies remain in `results/full/`. This demonstrates image-content reproduction under the documented full configuration. It does not establish the original historical Python/NumPy environment or authenticate a historical command log that was not supplied.

The active validation modules were NumPy 2.5.5 and Matplotlib 3.10.8 under Python 3.13.7 on Windows 11 build 26300. The initial full-run manifest's flat distribution inventory also listed a shadowed system NumPy 2.5.4. [Environment reconciliation](../results/environment-reconciliation.json) records the actual local imports, resolves the duplicate-metadata issue, and preserves the original manifest unchanged. After system package visibility was disabled, the imported package versions and origins stayed the same; unit tests and diagnostics passed. A clean-environment instrumented quick run matched both raw quick-run PNGs byte-for-byte. The full run was not repeated after isolation; the reason and scope are explicitly recorded in that reconciliation evidence.

## Report identifiers

The separately submitted report is not redistributed here. Its supplied files were identified by:

| File | SHA-256 |
|---|---|
| `market_making_ieee.pdf` | `386823d7872cfe5b4e6e9efa08e52655f365524e6b97e1be7a547370835fbf59` |
| `market_making_ieee.tex` | `b5f01872bb75135947cbf10efe3ef53cef1601c01db5e2f1522f209939fcd984` |

The read-only report review and remaining wording concerns are summarized in [report-consistency.md](report-consistency.md). The original report was not edited during repository preparation.
