import math


def distance(a, b):
    """
    Calculates the distance between two coordinates
    :param a: n-dimensional coordinate
    :param b: n-dimensional coordinate
    :type a: [float, float, ...]
    :type b: [float, float, ...]
    :return: the distance
    :rtype: float
    """
    return math.sqrt(sum((a - b)**2 for a, b in zip(a, b)))


def vector_from_axis(axis='x'):
    """ Convert x, -x, y, -y, z, -z to the according vector, e.g. (1, 0, 0), (-1, 0, 0), ... """
    return [int(a == axis[-1]) * (-1 if axis.startswith('-') else 1) for a in 'xyz']


def axis_from_vector(vec=(1, 0, 0), upper_case=False):
    """ Convert a vector to an axis letter. Vector must have two zero values. """
    for ax, i in zip('xyz', vec):
        if i:
            if upper_case:
                return ax.upper()
            else:
                return ax


def rgb_int_to_float(rgb=(255, 0, 255)):
    """ Convert an 8 bot rgb color code to float. """
    return [a/255.0 for a in rgb]


def position_between(a=(0, 0, 0), b=(1, 1, 1), weight=0.5):
    a_ = [x * (1 - weight) for x in a]
    b_ = [y * weight for y in b]
    return [x + y for x, y in zip(a_, b_)]
