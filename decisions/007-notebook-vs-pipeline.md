# 007: What stays in the notebook

Stage: S2 · Date: 2026-11-21 · Author: CosmicMagnetar · Drafted by agent: yes

## Choice

The notebook is for exploration only: looking at distributions, comparing models on a 5% sample, and logging comparisons to the separate `trip-duration-notebook` experiment. The pipeline owns everything that must repeat without a person: building features, the training set, fitting, evaluation, registration, the gate, and the `challenger` alias.

## Rejected alternative

Training in the notebook and registering the best model from there. It is quicker to try, but the result depends on who ran which cells in what order, and it would bypass the feature contract and the gate.

## Why

<!-- Replace with your own reasoning before you submit. -->

The pipeline's run records which data, code and window produced a version, and a model can only become `challenger` through the blocking `beats_champion` check. A notebook has none of those guarantees.

## What would show this was wrong

<!-- Add what you would act on. -->

Useful analysis keeps being repeated by hand in the notebook for every new month, or a pipeline result can't be explained without rerunning notebook cells.
