import numpy as np
np.set_printoptions(linewidth=200)
import matplotlib.pyplot as plt
import time

plt.ion()

fig = plt.figure()
ax = fig.gca()
ax.plot([0,1],[0,1])
plt.show()

time.sleep(1)
