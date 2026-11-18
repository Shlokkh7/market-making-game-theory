# Report consistency review

The supplied six-page IEEE report was reviewed read-only alongside its TeX source and latest figure files. All six PDF pages were rendered and visually inspected; no clipping, broken figures, overlapping text, or missing glyphs was observed. The two figures match the supplied PNGs exactly after decoding to RGB. A completed full run subsequently reproduced both reference PNGs pixel-for-pixel in RGBA, with different container bytes; see [provenance.md](provenance.md).

This repository accompanies the report. It neither modifies the report nor endorses every historical numerical claim without corresponding evidence.

## Source-defined settings versus historical results

The report's main simulation configuration matches the preserved source: `Q=5`, three rivals, 100 solver steps, ten simulation substeps, 40,000 A paths, and 20,000 B paths. Its `Q=10` paper-belief benchmark comparison uses a different configuration.

Table III of the supplied report gives the following rounded historical values. The completed full reproduction now matches these theory values and mean objectives at the displayed three-decimal precision:

| Initial inventory | Theory | A mean | B mean |
|---|---:|---:|---:|
| -3 | -50.594 | -50.577 | -50.566 |
| 0 | 9.535 | 9.549 | 9.570 |
| +3 | 69.406 | 69.419 | 69.437 |

The reported standard errors are approximately 0.009 for A and 0.013 for B, also consistent with the new full run. The instrumented run completed successfully in 34.8961312 seconds; this is a measured runtime for the validation setup, not a historical runtime claim. The command, environment, source hashes, and full-precision outputs are retained in [the full-run manifest](../results/full/manifest.json) and [summary](../results/full/summary.json).

For reference inventory zero, the new run gives theory 9.535126740363182, A mean 9.548654249564093 with standard error 0.009316322497497, and B mean 9.569540813820524 with standard error 0.013362646474508. B's gap is +0.034414073457341, about 2.575 standard errors. This supports the report's rounded baseline comparison while leaving the residual unresolved.

The report describes belief total-variation distances of approximately 0.03, 0.10, and 0.05 at times 0, 0.5, and 0.9. The completed full run instead records:

| Time | Full-run total-variation distance | Retained ask samples | No-ask exclusions |
|---|---:|---:|---:|
| 0.0 | 0.004161700717 | 20,000 | 0 |
| 0.5 | 0.097911600933 | 19,999 | 1 |
| 0.9 | 0.055443365060 | 20,000 | 0 |

The initial value **approximately 0.03 does not reproduce** under the documented full configuration; use approximately 0.00416 when describing this new run. The mid-horizon and late values are of the reported scale, with the late value approximately 0.0554. No claim is made about which earlier run produced the report's initial number. The source report remains unchanged.

The 50-to-1,600-step refinement sequence, refined simulation means, `k=0` machine-precision comparison, `Q=10` benchmark table, rival-count sweep, and Bayesian error-reduction percentages are auxiliary historical claims. The baseline quick/full command does not reproduce them automatically. Consult [the results index](../results/README.md) for any corresponding evidence recovered or generated during preparation.

## Wording and interpretation findings

| Report location | Finding | Accurate repository interpretation |
|---|---|---|
| TeX line 146; PDF page 3 | B rates are described as recomputed after every event. | The implementation recomputes after each substep; simultaneous bid/ask hits use pre-substep rates. |
| TeX line 190; PDF pages 3-4 | A long maker is described as selling cheaper and buying dearer when ask distance falls and bid distance rises. | Since bid price is `S - bid_distance`, a larger bid distance lowers the bid price. The maker lowers the ask to sell more readily and lowers the bid to discourage further purchases. |
| TeX line 127; PDF page 3 | A generalized static N-maker formula is presented without the N-player intensity/game needed to support it. | The three supplied scripts do not implement that static game. The previously withdrawn shortcut is not presented as a valid repository result. |
| TeX lines 241 and 245; PDF page 5 | Initial belief consistency is called exact. | Use approximate initial agreement, with finite-sample uncertainty and the difference between joint-both-sides and ask-only availability conditioning stated. |
| Discussion and conclusion | Belief drift is described as having a small payoff cost. | The experiments observe distribution differences and an unresolved B objective gap; they do not isolate the causal cost of drift. |
| TeX line 248; PDF page 5 | Bayesian performance percentages are supporting results. | These concern a separate model-based inference experiment, not posterior updating in the explicit-game belief figure. Its oracle is a fixed-belief construction. |
| TeX line 266; PDF page 6 | The repository citation contains year and URL placeholders. | Replace with the real repository URL and fixed submission reference after publication; report edits require separate authorization. |

The zero-shift deviation point is zero by construction. Empirical findings concern the tested six nonzero constant shifts under Experiment A's fixed-belief environment; they do not establish optimality against every possible policy or within B.

## Caveats already acknowledged by the report

Preserve the report's stated limitations: restricted deviations, synthetic data, an unresolved B payoff residual, absent empirical calibration, and an unresolved absolute-scale mismatch with the published paper's numerical figures. The adaptation need not reproduce the source paper's absolute scale to support conclusions at its own documented parameters, but it must not claim that this mismatch was resolved.

The supplied report uses `IEEEtran` in conference mode and names Prashant Vijaykumar Sharma, Shlok Khandelwal, and Khyati Srivastava, with the shared SVNIT affiliation. Those supplied academic identities are credited in the README. Publication ownership, team authorization, and license decisions remain distinct from authorship in the report.
