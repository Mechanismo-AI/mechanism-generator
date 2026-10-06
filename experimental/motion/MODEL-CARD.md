# Experimental six-bar motion assets

All three inference assets and the included synthetic regression fixtures are Apache-2.0. Hashes are recorded in the packaged assets/manifest.json. This is a local CPU, float64 research pipeline for twelve fixed crank phases, known assembly branches and normalized pose plus crank-angle derivative targets. It is not a general mechanism generator or a hardware qualification system.

## Proposal network

The proposal has 122 inputs, two 128-unit SiLU hidden layers and 16 geometry outputs. Fixed phase parameters complete the solver's raw vector. Training compared pose-only and derivative-conditioned models across seeds 101, 202 and 303, with paired identical initialization per seed. The exported derivative checkpoint is seed 101, best epoch 2980, not the final stopping epoch 3580. The architecture was initialized afresh; published earlier weights were not used.

Recorded configuration: 256 fresh synthetic training cases per epoch, batch size 64, 128 fixed validation cases, 256 statistics cases, learning rate 0.001, validation every ten epochs and plateau patience sixty checks with minimum relative improvement 0.001. Training used supervised geometry and motion losses. The original fixed-data checksum was 4faabc33c7900ead08b0d903a7f2efee68a50866d796c34831d0e760c22c64a3. Original training-source hashes are recorded in extraction.json and evidence/training-provenance.json.

The saved checkpoint explicitly marked itself not release qualified: its unrefined proposals achieved **0/128 strict pose-and-derivative passes**, mean normalized error 8.603412453009074, with no nonfinite cases. This asset is an initializer for numerical refinement. It must not be presented as a qualified end-to-end predictor.

## Continuation selector

A frozen 17-feature model uses diagnostics at refinement evaluations 50 and 100 to choose continuation versus restart. Fitting used 358 development decision pairs, including 64 continue-only and 171 restart-only successes. Leave-development-cycle-out normalization and cross-validation selected ridge penalty 1.0; the decision threshold is 0.5. On 81 reserved pairs it achieved 70 successes versus 68 for the previous fixed policy, with two gains and no losses. This evidence is specific to the synthetic development distribution.

## Candidate chooser

The frozen 22-feature candidate model ranks the original random fallback and eight orientation-shifted learned proposals using initial geometry and mismatch diagnostics. Its outputs are ranking scores, not validated success probabilities. Labels came from independently refining all nine candidates for each of sixty fresh synthetic targets across five groups: control, long tool, large crank, mounting offset and extreme mounting offset. Entire targets were separated into thirty fitting, fifteen selection and fifteen reserved targets: 270/135/135 candidate labels. Fitting labels contained 119 successes and 151 failures. Standardization used fitting data only.

Selection compared ridge penalties 0.1, 1, 10 and 100. Selection achieved fourteen successes versus thirteen baseline; the tie rule selected penalty 100. The frozen model was then evaluated on the reserved fifteen targets, where both policies achieved fifteen successes. That pilot did not establish independent improvement. No reserved-data retuning followed.

## Refined pipeline evidence and limitations

A subsequent frozen paired synthetic screen achieved **78/80** qualified results versus **74/80** for the private experimental six-bar derivative baseline, with four gains and no losses. This result includes numerical refinement and strict qualification; it is not the proposal network's standalone accuracy. Both policies were capped at 200 refinement objective/gradient evaluations, excluding proposal and qualification overhead. The baseline is distinct from the publicly released four-bar engine. The eight bundled regression fixtures were selected after this screen and cannot establish new generalization evidence.

The remaining screen failures were one long-tool and one extreme-mounting task. Evidence covers the same synthetic mechanism family only. Payload capacity, operating speed, motor requirements, collision clearance and manufactured tolerances are unrated. Arbitrary phases and unknown branches are unsupported. Checksum verification detects corruption, not authenticity against malicious replacement of both manifest and assets.

## Reproducibility scope

The source distribution includes inference code, frozen assets, portable regression fixtures and test/build instructions. These reproduce solver behavior without private study imports. It does **not** include the complete original training generators, fixed training data or training runner, so exact retraining of these checkpoints is not reproducible from this distribution. The recorded training configuration and splits describe provenance, not a promise of a runnable training recipe. A separately reviewed training-source release would be needed for that claim.
