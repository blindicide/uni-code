import socket
import json
from tabulate import tabulate # Для красивого вывода таблиц

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 65432

def send_request(request_data):
    """Отправляет запрос на сервер и возвращает ответ."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SERVER_HOST, SERVER_PORT))
            # Кодируем и отправляем JSON запрос
            s.sendall(json.dumps(request_data).encode('utf-8'))

            # Получаем ответ (буфер может потребоваться увеличить для больших ответов)
            response_data = s.recv(16384) # Увеличенный буфер
            if not response_data:
                return {'status': 'ошибка', 'message': 'Сервер не ответил.'}

            # Декодируем и парсим JSON ответ
            response = json.loads(response_data.decode('utf-8'))
            return response
    except ConnectionRefusedError:
        return {'status': 'ошибка', 'message': 'Статическая ошибка С-1: Соединение отклонено. Проверьте, запущен ли сервер.'}
    except ConnectionResetError:
         return {'status': 'ошибка', 'message': 'Статическая ошибка С-3: Соединение сброшено сервером.'}
    except json.JSONDecodeError:
         return {'status': 'ошибка', 'message': 'Статическая ошибка С-5: Не удалось понять ответ сервера.'}
    except Exception as e:
        return {'status': 'ошибка', 'message': f'Произошла ошибка: {e}'}

def print_table(data_list, headers="keys"):
    """Печатает список словарей в виде таблицы."""
    if not data_list:
        print("Нет данных для отображения.")
        return
    # tabulate ожидает список списков или список словарей
    if isinstance(data_list, dict): # Если пришел один объект, обернуть в список
        data_list = [data_list]
    print(tabulate(data_list, headers=headers, tablefmt="grid"))


def get_input(prompt, required_type=str, allow_empty=False):
    """Запрашивает ввод у пользователя с проверкой типа и возможностью пропуска."""
    while True:
        value_str = input(prompt).strip()
        if not value_str and allow_empty:
            return None
        if not value_str and not allow_empty:
             print("Ввод не может быть пустым.")
             continue
        try:
            return required_type(value_str)
        except ValueError:
            print(f"Неверный ввод. Пожалуйста, введите значение типа {required_type.__name__}.")


def main_menu():
    """Отображает главное меню и обрабатывает выбор пользователя."""
    while True:
        print('\n--- Клиент БД АСУО "Пергамент". Лицензия: БЕССРОЧНАЯ за номером 394604 ---')
        print('--- Лицензия на использование АСУО принадлежит техническому университету им. Прометея ---')
        print('\n--- Действия: ---')
        print("Студенты:")
        print("  1. Добавить студента")
        print("  2. Удалить студента")
        print("  3. Обновить студента")
        print("  4. Показать всех студентов")
        print("  5. Найти студента по имени")
        print("Предметы:")
        print("  6. Добавить предмет")
        print("  7. Назначить предмет студенту")
        print("  8. Отменить назначение предмета студенту")
        print("  9. Показать студентов и их предметы")
        print(" 10. Найти студентов по предмету")
        print(" 11. Найти предметы по студенту")
        print("Оценки:")
        print(" 12. Добавить/Обновить оценку")
        print(" 13. Удалить оценку")
        print(" 14. Получить средний балл студента")
        print(" 15. Получить средний балл по предмету")
        print(" 16. Найти студентов с баллом ниже порогового значения")
        print("  0. Выход")
        print("-----------------------------")

        choice = input("Введите ваш выбор: ")

        if choice == '1':
            # Добавить студента
            print("\n-- Добавить нового студента --")
            full_name = get_input("Полное имя: ")
            age = get_input("Возраст: ", required_type=int)
            group_name = get_input("Название группы: ")
            course = get_input("Курс: ", required_type=int)
            average_grade = get_input("Начальный средний балл: ", required_type=float) # Используем начальный
            payload = {'full_name': full_name, 'age': age, 'group_name': group_name, 'course': course, 'average_grade': average_grade}
            response = send_request({'command': 'add_student', 'payload': payload})
            print(f"Ответ сервера: {response.get('message', 'Сообщение не получено')}")

        elif choice == '2':
            # Удалить студента
            print("\n-- Удалить студента --")
            full_name = get_input("Введите полное имя студента для удаления: ")
            response = send_request({'command': 'delete_student', 'payload': {'full_name': full_name}})
            print(f"Ответ сервера: {response.get('message', 'Сообщение не получено')}")

        elif choice == '3':
            # Обновить студента
            print("\n-- Обновить студента --")
            full_name_to_update = get_input("Введите полное имя студента для обновления: ")
            print("Введите новые значения (оставьте пустым, чтобы сохранить текущее значение):")
            new_full_name = get_input("Новое полное имя: ", allow_empty=True)
            new_age = get_input("Новый возраст: ", required_type=int, allow_empty=True)
            new_group_name = get_input("Новое название группы: ", allow_empty=True)
            new_course = get_input("Новый курс: ", required_type=int, allow_empty=True)
            new_average_grade = get_input("Новый начальный средний балл: ", required_type=float, allow_empty=True)

            payload = {'full_name_to_update': full_name_to_update}
            if new_full_name: payload['full_name'] = new_full_name
            if new_age is not None: payload['age'] = new_age
            if new_group_name: payload['group_name'] = new_group_name
            if new_course is not None: payload['course'] = new_course
            if new_average_grade is not None: payload['average_grade'] = new_average_grade

            if len(payload) > 1: # Убедимся, что есть что обновлять кроме имени для поиска
                response = send_request({'command': 'update_student', 'payload': payload})
                print(f"Ответ сервера: {response.get('message', 'Сообщение не получено')}")
            else:
                 print("Новая информация для обновления не предоставлена.")


        elif choice == '4':
            # Список всех студентов
            print("\n-- Список всех студентов --")
            response = send_request({'command': 'list_students'})
            if response.get('status') == 'успех':
                print_table(response.get('data', []))
            else:
                print(f"Ошибка: {response.get('message', 'Неизвестная ошибка')}")

        elif choice == '5':
             # Найти студента по имени
             print("\n-- Найти студента по имени --")
             full_name = get_input("Введите полное имя для поиска: ")
             response = send_request({'command': 'find_student', 'payload': {'full_name': full_name}})
             if response.get('status') == 'успех':
                 print_table(response.get('data', {}))
             else:
                 print(f"Ошибка: {response.get('message', 'Неизвестная ошибка')}")

        elif choice == '6':
             # Добавить предмет
             print("\n-- Добавить новый предмет --")
             subject_name = get_input("Название предмета: ")
             teacher = get_input("Имя преподавателя: ")
             response = send_request({'command': 'add_subject', 'payload': {'subject_name': subject_name, 'teacher': teacher}})
             print(f"Ответ сервера: {response.get('message', 'Сообщение не получено')}")

        elif choice == '7':
             # Назначить предмет студенту
             print("\n-- Назначить предмет студенту --")
             student_id = get_input("Введите ID студента: ", required_type=int)
             subject_id = get_input("Введите ID предмета: ", required_type=int)
             response = send_request({'command': 'assign_subject', 'payload': {'student_id': student_id, 'subject_id': subject_id}})
             print(f"Ответ сервера: {response.get('message', 'Сообщение не получено')}")

        elif choice == '8':
             # Отменить назначение предмета студенту
             print("\n-- Отменить назначение предмета студенту --")
             student_id = get_input("Введите ID студента: ", required_type=int)
             subject_id = get_input("Введите ID предмета: ", required_type=int)
             response = send_request({'command': 'unassign_subject', 'payload': {'student_id': student_id, 'subject_id': subject_id}})
             print(f"Ответ сервера: {response.get('message', 'Сообщение не получено')}")

        elif choice == '9':
             # Список студентов и их предметов
             print("\n-- Список студентов и их предметов --")
             response = send_request({'command': 'list_students_subjects'})
             if response.get('status') == 'успех':
                 print_table(response.get('data', []))
             else:
                 print(f"Ошибка: {response.get('message', 'Неизвестная ошибка')}")

        elif choice == '10':
             # Найти студентов по предмету
             print("\n-- Найти студентов по предмету --")
             subject_identifier = get_input("Введите ID или название предмета: ")
             payload = {}
             try:
                 payload['subject_id'] = int(subject_identifier)
             except ValueError:
                 payload['subject_name'] = subject_identifier
             response = send_request({'command': 'find_students_by_subject', 'payload': payload})
             if response.get('status') == 'успех':
                 print("Студенты, изучающие этот предмет:")
                 print_table(response.get('data', []))
             else:
                 print(f"Ошибка: {response.get('message', 'Неизвестная ошибка')}")

        elif choice == '11':
             # Найти предметы по студенту
             print("\n-- Найти предметы по студенту --")
             student_identifier = get_input("Введите ID или имя студента: ")
             payload = {}
             try:
                 payload['student_id'] = int(student_identifier)
             except ValueError:
                 payload['student_name'] = student_identifier
             response = send_request({'command': 'find_subjects_by_student', 'payload': payload})
             if response.get('status') == 'успех':
                 print("Предметы, изучаемые этим студентом:")
                 print_table(response.get('data', []))
             else:
                 print(f"Ошибка: {response.get('message', 'Неизвестная ошибка')}")

        elif choice == '12':
             # Добавить/Обновить оценку
             print("\n-- Добавить/Обновить оценку --")
             student_id = get_input("Введите ID студента: ", required_type=int)
             subject_id = get_input("Введите ID предмета: ", required_type=int)
             grade = get_input("Введите оценку: ", required_type=float)
             response = send_request({'command': 'add_grade', 'payload': {'student_id': student_id, 'subject_id': subject_id, 'grade': grade}})
             print(f"Ответ сервера: {response.get('message', 'Сообщение не получено')}")
             # Примечание: команда update_grade также существует, но add_grade с INSERT OR REPLACE охватывает оба случая

        elif choice == '13':
             # Удалить оценку
             print("\n-- Удалить оценку --")
             student_id = get_input("Введите ID студента: ", required_type=int)
             subject_id = get_input("Введите ID предмета: ", required_type=int)
             response = send_request({'command': 'delete_grade', 'payload': {'student_id': student_id, 'subject_id': subject_id}})
             print(f"Ответ сервера: {response.get('message', 'Сообщение не получено')}")

        elif choice == '14':
             # Получить средний балл студента (Расчетный)
             print("\n-- Получить средний балл студента --")
             student_identifier = get_input("Введите ID или имя студента: ")
             payload = {}
             try:
                 payload['student_id'] = int(student_identifier)
             except ValueError:
                 payload['student_name'] = student_identifier
             response = send_request({'command': 'get_student_average_grade', 'payload': payload})
             if response.get('status') == 'успех':
                 print_table(response.get('data', {}))
             else:
                 print(f"Ошибка: {response.get('message', 'Неизвестная ошибка')}")

        elif choice == '15':
             # Получить средний балл по предмету
             print("\n-- Получить средний балл по предмету --")
             subject_identifier = get_input("Введите ID или название предмета: ")
             payload = {}
             try:
                 payload['subject_id'] = int(subject_identifier)
             except ValueError:
                 payload['subject_name'] = subject_identifier
             response = send_request({'command': 'get_subject_average_grade', 'payload': payload})
             if response.get('status') == 'успех':
                 print_table(response.get('data', {}))
             else:
                 print(f"Ошибка: {response.get('message', 'Неизвестная ошибка')}")

        elif choice == '16':
             # Найти студентов с баллом ниже порогового значения
             print("\n-- Найти студентов с баллом ниже порогового значения --")
             threshold = get_input("Введите пороговое значение среднего балла: ", required_type=float)
             response = send_request({'command': 'get_students_below_avg', 'payload': {'threshold': threshold}})
             if response.get('status') == 'успех':
                 print(f"Студенты со средним баллом ниже {threshold}:")
                 print_table(response.get('data', []))
             else:
                 print(f"Ошибка: {response.get('message', 'Неизвестная ошибка')}")

        elif choice == '0':
            print("Завершение работы клиента.")
            break

        else:
            print("Неверный выбор. Пожалуйста, попробуйте снова.")

if __name__ == "__main__":
    main_menu()
