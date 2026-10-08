---
title: About SPINE Learn
site:
  hide_title_block: true
---

# About SPINE Learn

::::{div}
:class: spine-banner

:::{image} brand/spine-logo-light.png
:alt: SPINE — Scalable Particle Imaging with Neural Embeddings
:class: spine-banner-logo
:width: 280px
:align: left
:::

**Read it. Run it. Reason about it.**

Living tutorials for particle reconstruction and analysis.
::::

A living tutorial should evolve with the software it teaches. Start with one
small, executable lesson: move from points to particle candidates, then inspect
an interaction and build your first selection.

## Start with the objects

[**From points to particles to interactions →**](lesson.ipynb)

20 minutes · Python and NumPy basics · CPU only · No detector data required

You will work with real SPINE classes and a deliberately synthetic event.
Listen to a short introduction at each section, inspect the executed examples,
and use **Continue** when you are ready. Audio is optional; transcripts and the
written lesson carry the complete learning experience.

[Download the runnable notebook](downloads/reconstruction-basics.ipynb)

## A lesson you can maintain

One MyST Markdown source produces the website and notebook. Code executes at
build time. Separately versioned narration produces cached local speech.
The narration in this first prototype is **an AI-assisted draft awaiting expert
review**. This is an object-interface lesson, not a reconstruction benchmark.

The exported notebook runs locally after installing the repository requirements.
The website displays executed results; it does not connect to a live kernel.

[Setup and authoring guide](https://github.com/DeepLearnPhysics/spine-learn)
