"""
A geometry module for the SymPy library. This module contains all of the
entities and functions needed to construct basic geometrical data and to
perform simple informational queries.

Usage:
======

Examples
========

"""
from solving.geometry.point import Point, Point2D, Point3D
from solving.geometry.line import Line, Ray, Segment, Line2D, Segment2D, Ray2D, \
    Line3D, Segment3D, Ray3D
from solving.geometry.plane import Plane
from solving.geometry.ellipse import Ellipse, Circle
from solving.geometry.polygon import Polygon, RegularPolygon, Triangle, rad, deg
from solving.geometry.util import are_similar, centroid, convex_hull, idiff, \
    intersection, closest_points, farthest_points
from solving.geometry.exceptions import GeometryError
from solving.geometry.curve import Curve
from solving.geometry.parabola import Parabola

__all__ = [
    'Point', 'Point2D', 'Point3D',

    'Line', 'Ray', 'Segment', 'Line2D', 'Segment2D', 'Ray2D', 'Line3D',
    'Segment3D', 'Ray3D',

    'Plane',

    'Ellipse', 'Circle',

    'Polygon', 'RegularPolygon', 'Triangle', 'rad', 'deg',

    'are_similar', 'centroid', 'convex_hull', 'idiff', 'intersection',
    'closest_points', 'farthest_points',

    'GeometryError',

    'Curve',

    'Parabola',
]
