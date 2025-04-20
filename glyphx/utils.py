def normalize(data):
    import numpy as np
    arr = np.array(data)
    return (arr - arr.min()) / (arr.max() - arr.min())