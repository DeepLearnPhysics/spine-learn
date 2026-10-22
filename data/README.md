# First lesson sample

- Source: https://s3df.slac.stanford.edu/data/neutrino/spine/workshop/reco/generic_small_spine.h5
- Selected by the maintainer for the public tutorial.
- Size: 1,603,240 bytes; six entries.
- SHA-256: `979035067ba49962a7c403d1d41822e04192ec87a5b3f1df65280e8a23e56969`
- Stored producer version: SPINE 0.9.5 (`info.attrs["version"]`).
- Reader used to verify all six entries: SPINE 1.4.1.
- Lesson entry: 0; 2,228 points, nine reconstructed particles, three interactions.
- Coordinates: centimeters. No deposited-energy interpretation is taught here.

The notebook downloads the file into `.cache/data/` relative to its working
folder and verifies its checksum before opening it. This ignored cache is not
committed or copied to the website. A pre-populated copy works offline; the
first download requires network access. The public URL also works without an
S3DF login or mounted filesystem.

To replace the sample, update the notebook URL/checksum and this provenance
record together. Re-execute every cell, review the saved counts, figure and
exercise, and update affected narration. Do not silently accept a changed file
at the same URL. The stored reconstruction configuration is available in the
file's `info` attributes; it should not be confused with the reader version.
