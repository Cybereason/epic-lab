from pprint import pprint
from pdb import pm
from importlib import reload

try:
    import numpy as np
except ImportError:
    pass

try:
    import pandas as pd
except ImportError:
    pass
else:
    pd.Series.vc = pd.Series.value_counts
    pd.Index.vc = pd.Index.value_counts
    pd.vc = pd.value_counts
    pd.Series.sv = lambda self, ascending=False, **kwargs: self.sort_values(ascending=ascending, **kwargs)
    pd.DataFrame.sv = lambda self, by, ascending=False, **kwargs: self.sort_values(by, ascending=ascending, **kwargs)

try:
    import matplotlib.pyplot as plt
except ImportError:
    pass

try:
    import epic.common
except ImportError:
    pass
else:
    from epic.common.general import *
    from epic.common.io import *
    from epic.common.iteration import *
