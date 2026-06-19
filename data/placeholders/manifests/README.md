# Manifests

Place empirical-run manifests in `data/manifests/` following `schemas/experiment_manifest.schema.json`. Templates are in `configs/experiments/`.

- Replace `device_profile_file` with the path to the processed calibration artifact generated from real measurements.
- Edit only the protocol or workload knobs described in the specification; leave the calibration artifacts unchanged.
