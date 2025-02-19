from StaticAnalysis.lib.Common import add_map
import matplotlib.pyplot as plt
import numpy as np

# For 7.32 map
tower_coordinates = [
    ('0', 0.254395, 0.125977),  # RT3 Bot
    ('1', 0.209961, 0.240723),  # RT3 Mid
    ('2', 0.095703, 0.286621),  # RT3 Top
    ('3', 0.473389, 0.113770),  # RT2 Bot
    ('4', 0.798706, 0.125488),  # RT1 Bot
    ('5', 0.288811, 0.328864),  # RT2 Mid
    ('6', 0.112793, 0.442139),  # RT2 Top
    ('7', 0.113770, 0.613281),  # RT1 Top
    ('8', 0.145996, 0.203125),  # RT4 Top (only two of these)
    ('9', 0.799316, 0.786377),  # DT4 Top
    ('10', 0.488280, 0.875000),  # DT2 Top
    ('11', 0.208983, 0.863281),  # DT1 Top
    ('12', 0.646483, 0.626952),  # DT2 Mid
    ('13', 0.531615, 0.535522),  # DT1 Mid
    ('14', 0.890625, 0.519530),  # DT2 Bot
    ('15', 0.880859, 0.678466),  # DT3 Bot
    ('16', 0.709960, 0.848145),  # DT3 Top
    ('17', 0.755371, 0.724090),  # DT3 Mid
    ('18', 0.817382, 0.768066),  # DT4 Bot
    ('19', 0.163574, 0.177490),  # RT4 Bot
    ('20', 0.398193, 0.410156),  # RT1 Mid
    ('21', 0.878824, 0.361327),  # DT1 Bot
]

fig = plt.figure(figsize=(7, 7))
axis = fig.subplots()
add_map(axis)

unzipped = list(zip(*tower_coordinates))
name = unzipped[0]
x = unzipped[1]
y = unzipped[2]


x1 = np.array([3208/4000,  863/4000,])
x2 = np.array([0.798706, 0.208983,])

y1 = np.array([(4000-3498)/4000, (4000-530)/4000])
y2 = np.array([0.125488, 0.863281])

m1, c1 = np.polyfit(x2, x1, 1)
m2, c2 = np.polyfit(y2, y1, 1)

xscale = list(map(lambda l: m1*l + c1, x))
yscale = list(map(lambda l: m2*l + c2, y))


axis.scatter(x, y)

for i, txt in enumerate(name):
    axis.annotate(txt, (x[i], y[i]))

plt.show()