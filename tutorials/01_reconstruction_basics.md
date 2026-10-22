---
 title: From points to particles to interactions
 jupytext:
   text_representation:
     extension: .md
     format_name: myst
     format_version: '0.13'
 kernelspec:
   display_name: Python 3
   language: python
   name: python3
---

# From points to particles to interactions

**A first SPINE analysis · 20 minutes · Python and NumPy basics**

Explore a reconstructed simulation event, inspect its particles, and build a
small interaction selection. You will learn to distinguish points, particles,
and interactions, and to interpret SPINE's particle labels and primary flags.

[Report a problem](https://github.com/DeepLearnPhysics/spine-learn/issues/new?template=problem.yml) or [suggest an improvement](https://github.com/DeepLearnPhysics/spine-learn/issues/new?template=suggestion.yml) · GitHub account required.

## Before you begin

To run the notebook in your usual Jupyter or VS Code environment, install SPINE
with its visualization tools:

```bash
pip install "spine[viz]"
```

The examples are tested with **SPINE 1.4.1**. Use the notebook download at the top
of this page to run them yourself. The website shows the executed results.
For environment setup or the full reconstruction runtime in Docker, see the
[SPINE installation guide](https://spine.readthedocs.io/en/latest/installation.html).
No GPU or model weights are needed here: reconstruction has already been run.

We use a [small generic-simulation sample](https://s3df.slac.stanford.edu/data/neutrino/spine/workshop/reco/generic_small_spine.h5)
hosted by S3DF. It contains six entries and is about 1.6 MB. This setup cell
downloads it once and reuses the local copy on subsequent runs. The checksum
checks that we are all working with the same sample.

```{code-cell} python
import hashlib
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import spine
from spine.constants import MUON_PID, PID_LABELS
from spine.construct import BuildManager
from spine.io.read import HDF5Reader
from spine.vis import Drawer

sample_url = (
    "https://s3df.slac.stanford.edu/data/neutrino/spine/"
    "workshop/reco/generic_small_spine.h5"
)
sample_path = Path(".cache/data/generic_small_spine.h5")
sample_sha256 = "979035067ba49962a7c403d1d41822e04192ec87a5b3f1df65280e8a23e56969"

# Download to a temporary file so an interrupted transfer is never reused.
if not sample_path.exists():
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = sample_path.with_suffix(".download")
    urlretrieve(sample_url, temporary_path)
    temporary_path.replace(sample_path)

if hashlib.sha256(sample_path.read_bytes()).hexdigest() != sample_sha256:
    raise ValueError(f"Sample differs from the lesson version: {sample_path}")

print(f"SPINE {spine.__version__}; sample ready")
```

(orientation)=
## 1. Read an event: what are you looking at?

An **entry** is one recorded example in this file. Its **points** describe the
spatial activity supplied to reconstruction. Reconstructed **particles** group
points into candidates; reconstructed **interactions** associate those candidates.
One entry can contain more than one reconstructed interaction.

The reader loads the stored objects. `BuildManager` then restores their links
to the shared point arrays and to each other. Here it is loading existing
reconstruction output, not running a neural network or finding new clusters.

(orientation-activity)=
### Pause and inspect

**Predict:** does one entry necessarily mean one interaction?

Run the next cell in your notebook, or inspect its saved output here. Identify
the number of entries in the file and the number of reconstructed interactions
in entry 0. Explain to yourself why those are different counts.

```{code-cell} python
reader = HDF5Reader(str(sample_path))
event = reader[0]

# Restore point arrays and particle-to-interaction links from the stored output.
builder = BuildManager(
    fragments=False,
    particles=True,
    interactions=True,
    mode="reco",
)
builder(event)

points = event["points"]
particles = event["reco_particles"]
interactions = event["reco_interactions"]

print("Entries in file:", len(reader))
print("Points in entry 0:", len(points))
print("Reconstructed particles:", len(particles))
print("Reconstructed interactions:", len(interactions))
assert (len(points), len(particles), len(interactions)) == (2228, 9, 3)
```

(orientation-explanation)=
### What those counts mean

The file contains **six entries**. We opened only entry 0: **2,228 points,
nine reconstructed particles, and three reconstructed interactions**.
The three interactions are associations made by reconstruction within this
entry; they are not the number of entries in the file.

Being reconstructed does not make an object a ground-truth statement. The file
also contains simulation truth, but this lesson starts with the reconstructed
objects. We will use their labels as candidate classifications, not as proof of
particle identity or interaction type.

**Check your understanding:** if you wanted the points belonging to just one
particle, would you inspect the whole event array or that particle's membership?
Continue when you can explain the distinction. You can also read on without audio.

(inspect-particles)=
## 2. Inspect one particle, including its units

Choose particle ID 4, a primary muon candidate in this entry. Its `index`
selects rows from the event's point array. Its `points` holds those coordinates.
Its `size` counts points; it does not measure physical length.

```{code-cell} python
particle = next(candidate for candidate in particles if candidate.id == 4)
print(
    {
        "id": particle.id,
        "label": PID_LABELS[particle.pid],
        "size": particle.size,
        "units": particle.units,
        "primary": particle.is_primary,
        "interaction_id": particle.interaction_id,
    }
)

# Verify the connection between the event-level array and this particle.
np.testing.assert_array_equal(particle.points, points[particle.index])
assert particle.size == len(particle.points)
assert particle.units == "cm"
```

SPINE's `pid` is a **class index**, not a PDG code. Use `MUON_PID` and
`PID_LABELS` instead of assuming that a muon is stored as `13`.
The `is_primary` flag is a reconstructed classification, not a certification
of the particle's generator history.

The coordinates in this sample are in centimeters. We will plot positions;
interpreting deposited energy requires additional knowledge of the simulation
and reconstruction configuration. SPINE's `Drawer` builds an interactive Plotly
figure directly from the event objects. Drag to rotate, scroll to zoom, and hover
over a particle to inspect its properties. Click a legend entry to hide it;
double-click one to isolate that particle. This view shows points assigned to
reconstructed particles, which need not include every point in the event.

```{code-cell} python
# Draw the reconstructed objects already restored by BuildManager.
# Each particle gets its own trace, so the legend can hide or isolate it.
drawer = Drawer(event, draw_mode="reco", height=550)
figure = drawer.get(
    "particles",
    attr=["id", "pid", "size", "is_primary", "interaction_id"],
    split_traces=True,
    title="Entry 0: reconstructed particle candidates",
)
figure.show(renderer="plotly_mimetype")
```

**Try:** choose a different particle ID in the previous cell. Compare its size
and label with particle 4. Does the plotted geometry alone establish its species?
The labels are reconstruction outputs, even when a shape looks familiar.

(inspect-interactions)=
## 3. Follow the particle to its interaction

Find the interaction associated with particle 4. Its `particles` collection
contains all its reconstructed constituents, not only its primary particles.

```{code-cell} python
interaction = next(
    candidate for candidate in interactions if candidate.id == particle.interaction_id
)

print("Interaction ID:", interaction.id)
print("Particle IDs:", interaction.particle_ids.tolist())
print("Primary IDs:", interaction.primary_particle_ids.tolist())
print("Particle count:", interaction.num_particles)
print("Primary topology:", interaction.topology)

for constituent in interaction.particles:
    print(
        f"Particle {constituent.id}: {PID_LABELS[constituent.pid]}, "
        f"{constituent.size} points, primary={constituent.is_primary}"
    )
```

With particle 4 selected, this is interaction 1: six particles, three of them
primary. Its `1mu1pi1p` topology describes valid primary candidates classified
as one muon, one pion, and one proton. It does not describe every constituent
and is not an interaction-mode classification.

**Try:** identify the three non-primary particles in the output. Predict how
counting every constituent instead of only primaries would change your summary.

(selection)=
## 4. Turn inspection into a small selection

Now select interactions containing exactly one **valid primary muon candidate**.
State each condition explicitly so the selection says what you intend.

```{code-cell} python
def primary_muon_count(candidate):
    """Count valid reconstructed primary muons in one interaction."""
    return sum(
        constituent.is_valid and constituent.is_primary and constituent.pid == MUON_PID
        for constituent in candidate.particles
    )


selected = [
    candidate for candidate in interactions if primary_muon_count(candidate) == 1
]
print("Selected interaction IDs:", [candidate.id for candidate in selected])
assert [candidate.id for candidate in selected] == [1]
```

**Exercise:** remove only the primary requirement. Predict which additional
interaction will pass, then check. Explain what changed in your selection:
the stored points, labels, and associations have not changed.

You have followed points into particles, particles into interactions, and
interaction properties into a selection. This is a reconstructed selection;
checking its relationship to simulation truth is a separate analysis step.

### References and next steps

- [SPINE documentation](https://spine.readthedocs.io/)
- [Particle API](https://spine.readthedocs.io/en/latest/api/generated/spine.data.out.particle.html)
- [Interaction API](https://spine.readthedocs.io/en/latest/api/generated/spine.data.out.interaction.html)
