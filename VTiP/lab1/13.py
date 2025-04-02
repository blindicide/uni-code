def selection_sort(arr):
    n = len(arr)
    for i in range(n):
        # Индекс минимального элемента
        min_idx = i
        for j in range(i + 1, n):
            if arr[j] < arr[min_idx]:
                min_idx = j

        # Замена
        arr[i], arr[min_idx] = arr[min_idx], arr[i]

        # Выводим промежуточный результат
        print(f"Шаг {i + 1}: {arr}")

    return arr

# Пример
lst = [64, 25, 12, 22, 11, 73]
print("Исходный массив:", lst)
sorted_lst = selection_sort(lst)
print("Отсортированный массив:", sorted_lst)
