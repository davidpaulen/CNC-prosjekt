from .config import *
from .geometry import *


def prepare_dragknife_paths(paths):
    return [{"compensated": p, "info": {"is_small": False}} for p in paths]