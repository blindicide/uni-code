import time


def iterate_sum(n):
    result = 0.0
    for i in range(1, n+1):
        result += 1.0 / i
    return result

def recursive_sum(n):
    if n == 1:
        return 1.0
    else:
        return 1.0 / n + recursive_sum(n - 1)

n = 26
start_time = time.time()
result_iterative = iterate_sum(n)
end_time = time.time()
print(f"Результат (итерация): {result_iterative}")
print(f"Время выполнения итеративной функции: {end_time - start_time} секунд")

start_time = time.time()
result_recursive = recursive_sum(n)
end_time = time.time()
print(f"Результат (рекурсия): {result_recursive}")
print(f"Время выполнения рекурсивной функции: {end_time - start_time} секунд")
