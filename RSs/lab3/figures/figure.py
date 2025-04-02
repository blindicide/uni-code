from abc import ABC, abstractmethod
from math import pi, sqrt

class Figure(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod 
    def area(self) -> float:
        pass
    
    @property
    @abstractmethod
    def perimeter(self) -> float:
        pass
    
    def add_area(self, figure: 'Figure') -> float:
        if not isinstance(figure, Figure):
            raise ValueError("Не указан вид фигуры")
        return self.area + figure.area


class Triangle(Figure):
    def __init__(self, a: float, b: float, c: float):
        if not self._is_valid_triangle(a, b, c):
            raise ValueError("Неправильные стороны")
        self._a = a
        self._b = b 
        self._c = c
    
    @property
    def name(self) -> str:
        return "Triangle"
    
    @property
    def area(self) -> float:
        p = self.perimeter / 2
        return sqrt(p * (p - self._a) * (p - self._b) * (p - self._c))
    
    @property
    def perimeter(self) -> float:
        return self._a + self._b + self._c
    
    @staticmethod
    def _is_valid_triangle(a: float, b: float, c: float) -> bool:
        return (a + b > c) and (a + c > b) and (b + c > a)


class Rectangle(Figure):
    def __init__(self, width: float, height: float):
        if width <= 0 or height <= 0:
            raise ValueError("Ширина и высота должны быть положительными")
        self._width = width
        self._height = height
    
    @property
    def name(self) -> str:
        return "Rectangle"
    
    @property
    def area(self) -> float:
        return self._width * self._height
    
    @property
    def perimeter(self) -> float:
        return 2 * (self._width + self._height)


class Square(Rectangle):
    def __init__(self, side: float):
        super().__init__(side, side)
    
    @property
    def name(self) -> str:
        return "Square"


class Circle(Figure):
    def __init__(self, radius: float):
        if radius <= 0:
            raise ValueError("Радиус должен быть положительным")
        self._radius = radius
    
    @property
    def name(self) -> str:
        return "Circle"
    
    @property
    def area(self) -> float:
        return pi * self._radius ** 2
    
    @property
    def perimeter(self) -> float:
        return 2 * pi * self._radius
