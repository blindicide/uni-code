class MyCustomError(Exception):
    def __init__(self, message="Это пользовательское исключение"):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"MyCustomError: {self.message}"

# Пример использования
def risky_function(value):
    if value < 0:
        raise MyCustomError("Значение не может быть отрицательным!")
    return value * 2

# Тестирование
try:
    result = risky_function(-5)
except MyCustomError as e:
    print(e)  # MyCustomError: Значение не может быть отрицательным!
else:
    print("Результат:", result)
