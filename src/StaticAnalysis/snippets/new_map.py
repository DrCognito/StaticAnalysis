from StaticAnalysis.lib.Common import add_map, EXTENT
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


# Extent calibration
# Bottom Right Twin gate 738
object_1_coords = (8896.000000, 23296.000000)
object_1_pixel = (58, 155) # From top left
# Top Left Twin Gate 738
object_2_coords = (23744.000000, 9856.000000)
object_2_pixel = (894, 910) # From top left
image_pixel_size = (1000, 1040)
image_pixel_size_738 = (1000, 1034)

def scale_axis(pmin, pmax, cmin, cmax, axis_length):
    p_diff = abs(pmax - pmin)
    c_diff = abs(cmax - cmin)
    
    # Coords per pixel
    c_per_p = c_diff / p_diff
    # Scaled full length
    scaled_axis = axis_length * c_per_p
    # Min axis
    axis_min = cmin - pmin*c_per_p
    axis_max = axis_min + scaled_axis
    
    return axis_min, axis_max

x0, x1 = scale_axis(
    object_1_pixel[0], object_2_pixel[0],
    object_1_coords[0], object_2_coords[0],
    image_pixel_size[0]
)
y0, y1 = scale_axis(
    object_2_pixel[1], object_1_pixel[1],
    object_1_coords[1], object_2_coords[1],
    image_pixel_size[1]
)
y_tweak_off = 550
x_tweak_off = 0
new_extent = [x0 + x_tweak_off, x1 + x_tweak_off, y0 + y_tweak_off, y1 + y_tweak_off]
print(f"Extents {new_extent}")

# 7.38 Map
tower_7_38 = [
    (9792.000000, 12976.000000), 
    (11744.000000, 12240.000000),
    (12432.000000, 10272.000000),
    (16024.000000, 10128.000000),
    (21308.000000, 10304.000000),
    (13047.750000, 13592.250000),
    (10096.000000, 15512.000000),
    (10048.000000, 18240.000000),
    (10672.000000, 11520.000000),
    (21328.000000, 21160.000000),
    (16256.000000, 22400.000000),
    (11712.000000, 22400.000000),
    (18880.000000, 18496.000000),
    (16908.000000, 17036.000000),
    (22784.000000, 16768.000000),
    (22720.000000, 19416.000000),
    (19936.000000, 22160.000000),
    (20656.000000, 20143.000000),
    (21664.000000, 20816.000000),
    (10992.000000, 11192.000000),
    (14840.000000, 14976.000000),
    (22653.343750, 14144.000000),
]

tower_7_39 = [
    (12432.000000, 10272.000000),
    (11744.000000, 12240.000000),
    (9792.000000, 12976.000000),
    (16024.000000, 10128.000000),
    (21308.000000, 10262.250000),
    (13193.656250, 13457.750000),
    (9920.000000, 15512.000000),
    (10048.000000, 18240.000000),
    (10672.000000, 11520.000000),
    (21328.000000, 21160.000000),
    (16256.000000, 22400.000000),
    (11108.937500, 22312.437500),
    (18880.000000, 18496.000000),
    (16908.000000, 17036.000000),
    (22784.000000, 16768.000000),
    (22720.000000, 19416.000000),
    (19936.000000, 22160.000000),
    (20656.000000, 20143.000000),
    (21664.000000, 20816.000000),
    (10992.000000, 11192.000000),
    (14840.000000, 14976.000000),
    (22653.343750, 14144.000000),
]

fig = plt.figure(figsize=(7, 7))
axis = fig.subplots()
add_map(axis, extent=new_extent)

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

x = [i[0] for i in tower_7_39]
y = [i[1] for i in tower_7_39]
axis.scatter(x, y)

# for i, txt in enumerate(name):
#     axis.annotate(txt, (x[i], y[i]))

plt.show()