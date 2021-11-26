import matplotlib.pyplot as plt

fig = plt.figure(figsize=(10, 13))
# ax = plt.axes()

for i in range(40):
    fig=plt.gcf()
    ax=plt.gca()
    ax.plot(range(i, i+10))
    # fig.savefig(f"./tests/test_{i}.png")
    # fig.clf()
    ax.cla()


def test_function(fig, ax, i):
    ax.plot(range(i, i+10))
    fig.savefig(f"./tests/test_{i}.png")
    ax.cla()


for i in range(5):
    fig=plt.gcf()
    ax=plt.gca()
    test_function(fig, ax, i)
    # fig.clf()
    # ax.cla()
