---
title: About SPINE Learn
site:
  hide_title_block: true
---

# About SPINE Learn

::::{div}
:class: spine-banner

:::{image} brand/spine-logo-dark.png
:alt: SPINE — Scalable Particle Imaging with Neural Embeddings
:class: spine-banner-logo spine-logo-for-light
:width: 280px
:align: left
:::

:::{image} brand/spine-logo-light.png
:alt: SPINE — Scalable Particle Imaging with Neural Embeddings
:class: spine-banner-logo spine-logo-for-dark
:width: 280px
:align: left
:::

**Read it. Run it. Ask about it. Reason about it.**

Living tutorials for particle reconstruction and analysis.
::::

SPINE Learn helps you understand how particle-detector data becomes reconstructed
particles and interactions, and how to use those objects in an analysis.
It connects the ideas behind SPINE with code you can inspect, run, and adapt
to your own questions.

## Understand what you are working with

A reconstruction is more than a collection of labels. What does a particle
object represent? How are particles grouped into an interaction? Which
properties come from the detector, which are inferred, and which assumptions
enter an analysis selection?

The goal of SPINE Learn is to make those connections explicit, so you can
reason about the objects and decisions in your analysis.

## Learn by exploring

Each lesson develops one idea through a worked example. Read the explanation,
inspect the result, then change something and predict what will happen.
Exercises invite you to test your understanding and explain what you observe.

Follow the lessons at your own pace. Optional narration offers spoken guidance,
pauses for reflection, and prompts to explore; the written material provides the
full explanation. Each lesson includes its own
runnable notebook, so you can try the examples and explore your own variations.

On the full SPINE Learn site, **Ask SPINE** helps explain the current lesson and
offers hints when you get stuck. Use its answers alongside the written material
and executable examples; the companion does not run your notebook.

## Built to grow with SPINE

The collection begins with one complete lesson on reconstructed particles and
interactions. Further lessons will extend this foundation to more reconstruction
and analysis tasks.

Each lesson's code and explanations are maintained together in version control.
Automated checks execute the examples before publication, and the same source
produces the website and downloadable notebook. Narration is maintained alongside
the written material, so both can evolve with the software. The goal is a shared
learning resource that improves over time, informed by the questions and needs
of its users.

## Start learning

[**From points to particles to interactions →**](lesson.ipynb)

20 minutes · Python and NumPy basics · CPU only

Begin with SPINE's particle and interaction objects. Use a small simulated event
to explore their properties, see how they relate to one another, and build your
first selection. The notebook downloads a small reconstructed sample; no trained
models or GPU are needed.

[Download all notebooks (.zip)](downloads/spine-learn-notebooks.zip)

For installation instructions and ways to contribute, visit the
[SPINE Learn repository](https://github.com/DeepLearnPhysics/spine-learn).

## Help improve SPINE Learn

Something not working, an explanation missing a step, or a topic you would like
to learn? [Report a problem](https://github.com/DeepLearnPhysics/spine-learn/issues/new?template=problem.yml) or [suggest an improvement](https://github.com/DeepLearnPhysics/spine-learn/issues/new?template=suggestion.yml).
You do not need to diagnose the cause: tell us which lesson you are using and
where you got stuck. You can also [browse existing reports](https://github.com/DeepLearnPhysics/spine-learn/issues).

Reports are public and require a GitHub account. Leave out credentials and
private data. The lesson companion helps with questions, but it does not send
reports to the maintainers.
