import pytest
from ..figures.figure import Triangle, Rectangle, Square, Circle
import math

def test_triangle_creation():
    t = Triangle(3, 4, 5)
    assert t.name == "Triangle"
    assert t.area == 6.0
    assert t.perimeter == 12

def test_invalid_triangle():
    with pytest.raises(ValueError):
        Triangle(1, 2, 3)

def test_rectangle_creation():
    r = Rectangle(4, 5)
    assert r.name == "Rectangle"
    assert r.area == 20
    assert r.perimeter == 18

def test_invalid_rectangle():
    with pytest.raises(ValueError):
        Rectangle(-1, 5)
    with pytest.raises(ValueError):
        Rectangle(0, 5)

def test_square_creation():
    s = Square(5)
    assert s.name == "Square"
    assert s.area == 25
    assert s.perimeter == 20

def test_circle_creation():
    c = Circle(3)
    assert c.name == "Circle"
    assert math.isclose(c.area, 28.2743, rel_tol=1e-4)
    assert math.isclose(c.perimeter, 18.8496, rel_tol=1e-4)

def test_invalid_circle():
    with pytest.raises(ValueError):
        Circle(-1)
    with pytest.raises(ValueError):
        Circle(0)

def test_add_area():
    t = Triangle(3, 4, 5)
    r = Rectangle(2, 3)
    assert math.isclose(t.add_area(r), 12, rel_tol=1e-4)

def test_add_area_invalid():
    t = Triangle(3, 4, 5)
    with pytest.raises(ValueError):
        t.add_area("not a figure")
