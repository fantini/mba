# %% Imports
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from collections import deque
import random

# MAX NO. OF POINTS TO STORE
que = deque(maxlen = 40)

fig, ax = plt.subplots()  # Create figure and axes outside the loop
line, = ax.plot([], []) # Initialize line object
scatter = ax.scatter([], [],)

ax.set_xlim(0, que.maxlen) # Set x-axis limits
ax.set_ylim(-20, 20) # Set y-axis limits


def animate(i):
    perc = random.random()
    que.append(perc)
    
    x = range(len(que))
    y = list(que) # Convert deque to list for plotting

    line.set_data(x, y)  # Update line data
    scatter.set_offsets(np.c_[x,y])

    return line, scatter,


ani = animation.FuncAnimation(fig, animate, interval=1000, blit=True) # increased interval for slower animation

plt.show()

# while True:

# 	# GENERATING THE POINTS - FOR DEMO
# 	perc = random.random()
# 	que.append(perc)
	
# 	# PLOTTING THE POINTS
# 	plt.plot(que)
# 	plt.scatter(range(len(que)),que)

# 	# SET Y AXIS RANGE
# 	plt.ylim(-1,4)
	
# 	# DRAW, PAUSE AND CLEAR
# 	plt.draw()
# 	plt.pause(0.1)
# 	plt.clf()
# %%
