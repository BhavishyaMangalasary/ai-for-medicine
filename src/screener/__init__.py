"""NHANES screener for undiagnosed diabetes: reassure vs finger-stick."""
import numpy as np

# The single global seed. Every random operation in this repo derives from it.
SEED = 20261204


def make_rng(stream: int = 0) -> np.random.Generator:
    """Return a reproducible generator. Use a different `stream` per independent use
    (for example one per bootstrap, per CV fold) so streams never share draws."""
    return np.random.default_rng([SEED, stream])
