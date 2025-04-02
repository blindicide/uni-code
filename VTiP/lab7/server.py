import socket
import threading
import sqlite3
import json
import logging
import os # Добавлен импорт

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Построение пути относительно файла скрипта
SCRIPT_DIR = os.path.dirname(__file__)
DATABASE = os.path.join(SCRIPT_DIR, 'student_database.db') # БД будет в той же папке, что и скрипт
HOST = '127.0.0.1'  # Локалхост
PORT = 65432 # Убедитесь, что этот порт свободен

# --- Инициализация и работа с БД ---

def get_db_connection():
    """Создает соединение с БД."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # Возвращать строки как объекты, похожие на словари
    conn.execute("PRAGMA foreign_keys = ON;") # Включить поддержку внешних ключей для целостности данных
    return conn

def init_db():
    """Инициализирует структуру БД и добавляет тестовые данные."""
    logging.info("Инициализация базы данных...")
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL UNIQUE,
        age INTEGER,
        group_name TEXT,
        course INTEGER,
        average_grade REAL
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT NOT NULL UNIQUE,
        teacher TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Student_Subjects (
        student_id INTEGER,
        subject_id INTEGER,
        PRIMARY KEY (student_id, subject_id),
        FOREIGN KEY (student_id) REFERENCES Students(id) ON DELETE CASCADE, -- При удалении студента удаляются и его связи с предметами
        FOREIGN KEY (subject_id) REFERENCES Subjects(id) ON DELETE CASCADE -- При удалении предмета удаляются и его связи со студентами
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        subject_id INTEGER,
        grade REAL NOT NULL,
        FOREIGN KEY (student_id) REFERENCES Students(id) ON DELETE CASCADE, -- При удалении студента удаляются и его оценки
        FOREIGN KEY (subject_id) REFERENCES Subjects(id) ON DELETE CASCADE, -- При удалении предмета удаляются и оценки по нему
        UNIQUE(student_id, subject_id) -- Обычно одна оценка на студента по предмету, если нет - убрать ограничение UNIQUE
    )''')

    # Добавление тестовых данных (если таблицы пусты)
    cursor.execute("SELECT COUNT(*) FROM Students")
    if cursor.fetchone()['COUNT(*)'] == 0:
        logging.info("Заполнение начальными данными...")
        students_data = [
            ('Иванов Иван Иванович', 20, 'ИС-21', 3, 4.5),
            ('Петров Петр Петрович', 21, 'ИС-21', 3, 4.8),
            ('Сидорова Анна Васильевна', 19, 'ПИ-22', 2, 4.9),
            ('Козлов Дмитрий Сергеевич', 22, 'ВМ-20', 4, 3.9)
        ]
        cursor.executemany('INSERT INTO Students (full_name, age, group_name, course, average_grade) VALUES (?, ?, ?, ?, ?)', students_data)

        subjects_data = [
            ('Математический анализ', 'Профессор Смирнов'),
            ('Базы данных', 'Доцент Кузнецова'),
            ('Программирование Python', 'Старший преподаватель Новиков'),
            ('Физика', 'Профессор Волков')
        ]
        cursor.executemany('INSERT INTO Subjects (subject_name, teacher) VALUES (?, ?)', subjects_data)

        # Назначим предметы (пример)
        # Иванов изучает Матанализ и БД
        cursor.execute("INSERT INTO Student_Subjects (student_id, subject_id) VALUES (1, 1)")
        cursor.execute("INSERT INTO Student_Subjects (student_id, subject_id) VALUES (1, 2)")
        # Петров изучает БД и Python
        cursor.execute("INSERT INTO Student_Subjects (student_id, subject_id) VALUES (2, 2)")
        cursor.execute("INSERT INTO Student_Subjects (student_id, subject_id) VALUES (2, 3)")
        # Сидорова изучает Python
        cursor.execute("INSERT INTO Student_Subjects (student_id, subject_id) VALUES (3, 3)")

        # Добавим оценки (пример)
        # Иванов: Матанализ=4, БД=5
        cursor.execute("INSERT INTO Grades (student_id, subject_id, grade) VALUES (1, 1, 4.0)")
        cursor.execute("INSERT INTO Grades (student_id, subject_id, grade) VALUES (1, 2, 5.0)")
        # Петров: БД=5, Python=5
        cursor.execute("INSERT INTO Grades (student_id, subject_id, grade) VALUES (2, 2, 5.0)")
        cursor.execute("INSERT INTO Grades (student_id, subject_id, grade) VALUES (2, 3, 5.0)")
        # Сидорова: Python=5
        cursor.execute("INSERT INTO Grades (student_id, subject_id, grade) VALUES (3, 3, 5.0)")
        # Козлов: пока нет предметов/оценок


    conn.commit()
    conn.close()
    logging.info("База данных успешно инициализирована.")

# --- Функции обработки запросов ---

def handle_request(data):
    """Обрабатывает запрос от клиента и вызывает соответствующую функцию БД."""
    command = data.get('command')
    payload = data.get('payload', {})
    conn = None # Инициализация переменной соединения

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if command == 'add_student':
            cursor.execute(
                'INSERT INTO Students (full_name, age, group_name, course, average_grade) VALUES (?, ?, ?, ?, ?)',
                (payload['full_name'], payload['age'], payload['group_name'], payload['course'], payload['average_grade'])
            )
            conn.commit()
            return {'status': 'успех', 'message': 'Студент успешно добавлен.'}

        elif command == 'delete_student':
            cursor.execute('DELETE FROM Students WHERE full_name = ?', (payload['full_name'],))
            if cursor.rowcount > 0:
                conn.commit()
                return {'status': 'успех', 'message': f'Студент {payload["full_name"]} удален.'}
            else:
                return {'status': 'ошибка', 'message': f'Студент {payload["full_name"]} не найден.'}

        elif command == 'update_student':
            # Собираем поля для обновления
            fields_to_update = []
            values = []
            for key, value in payload.items():
                if key != 'full_name_to_update' and value is not None:
                    fields_to_update.append(f"{key} = ?")
                    values.append(value)

            if not fields_to_update:
                 return {'status': 'ошибка', 'message': 'Не указаны поля для обновления.'}

            values.append(payload['full_name_to_update']) # Добавляем имя студента в конец списка значений для условия WHERE
            sql = f"UPDATE Students SET {', '.join(fields_to_update)} WHERE full_name = ?"
            cursor.execute(sql, tuple(values))

            if cursor.rowcount > 0: # Проверяем, была ли обновлена хотя бы одна строка
                conn.commit()
                return {'status': 'успех', 'message': f'Студент {payload["full_name_to_update"]} обновлен.'}
            else:
                return {'status': 'ошибка', 'message': f'Студент {payload["full_name_to_update"]} не найден или изменения не были внесены.'}


        elif command == 'list_students':
            cursor.execute('SELECT id, full_name, age, group_name, course, average_grade FROM Students ORDER BY full_name')
            students = [dict(row) for row in cursor.fetchall()]
            return {'status': 'успех', 'data': students}

        elif command == 'find_student':
            cursor.execute('SELECT id, full_name, age, group_name, course, average_grade FROM Students WHERE full_name = ?', (payload['full_name'],))
            student = cursor.fetchone()
            if student:
                return {'status': 'успех', 'data': dict(student)}
            else:
                return {'status': 'ошибка', 'message': f'Студент {payload["full_name"]} не найден.'}

        elif command == 'add_subject':
             cursor.execute(
                 'INSERT INTO Subjects (subject_name, teacher) VALUES (?, ?)',
                 (payload['subject_name'], payload['teacher'])
             )
             conn.commit()
             return {'status': 'успех', 'message': 'Предмет успешно добавлен.'}

        elif command == 'assign_subject':
            try:
                cursor.execute('INSERT INTO Student_Subjects (student_id, subject_id) VALUES (?, ?)',
                               (payload['student_id'], payload['subject_id']))
                conn.commit()
                return {'status': 'успех', 'message': 'Предмет успешно назначен.'}
            except sqlite3.IntegrityError as e:
                 # Проверяем тип ошибки целостности
                 if 'FOREIGN KEY constraint failed' in str(e): # Ошибка внешнего ключа (несуществующий студент или предмет)
                     return {'status': 'ошибка', 'message': 'ID студента или ID предмета не найден.'}
                 elif 'UNIQUE constraint failed' in str(e): # Ошибка уникальности (попытка добавить существующую связь)
                     return {'status': 'ошибка', 'message': 'Этот предмет уже назначен этому студенту.'}
                 else:
                     raise # Перебросить другие (неожиданные) ошибки целостности

        elif command == 'unassign_subject':
             cursor.execute('DELETE FROM Student_Subjects WHERE student_id = ? AND subject_id = ?',
                            (payload['student_id'], payload['subject_id']))
             if cursor.rowcount > 0:
                 conn.commit()
                 return {'status': 'успех', 'message': 'Предмет успешно отменен.'}
             else:
                 return {'status': 'ошибка', 'message': 'Назначение не найдено (проверьте ID студента/предмета).'}

        elif command == 'list_students_subjects':
            sql = """
            SELECT s.full_name, sub.subject_name, sub.teacher
            FROM Students s
            JOIN Student_Subjects ss ON s.id = ss.student_id
            JOIN Subjects sub ON ss.subject_id = sub.id
            ORDER BY s.full_name, sub.subject_name;
            """
            cursor.execute(sql)
            results = [dict(row) for row in cursor.fetchall()]
            return {'status': 'успех', 'data': results}

        elif command == 'find_students_by_subject':
             sql = """
             SELECT s.full_name, s.group_name, s.course
             FROM Students s
             JOIN Student_Subjects ss ON s.id = ss.student_id
             JOIN Subjects sub ON ss.subject_id = sub.id
             WHERE sub.id = ? OR sub.subject_name = ?
             ORDER BY s.full_name;
             """
             cursor.execute(sql, (payload.get('subject_id'), payload.get('subject_name')))
             results = [dict(row) for row in cursor.fetchall()]
             return {'status': 'успех', 'data': results}

        elif command == 'find_subjects_by_student':
             sql = """
             SELECT sub.subject_name, sub.teacher
             FROM Subjects sub
             JOIN Student_Subjects ss ON sub.id = ss.subject_id
             JOIN Students s ON ss.student_id = s.id
             WHERE s.id = ? OR s.full_name = ?
             ORDER BY sub.subject_name;
             """
             cursor.execute(sql, (payload.get('student_id'), payload.get('student_name')))
             results = [dict(row) for row in cursor.fetchall()]
             return {'status': 'успех', 'data': results}

        elif command == 'add_grade':
            try:
                 # Проверим, изучает ли студент этот предмет
                 cursor.execute("SELECT 1 FROM Student_Subjects WHERE student_id = ? AND subject_id = ?",
                                (payload['student_id'], payload['subject_id']))
                 if not cursor.fetchone(): # Если запрос ничего не вернул, значит студент не изучает этот предмет
                     return {'status': 'ошибка', 'message': 'Невозможно добавить оценку. Студент не назначен на этот предмет.'}

                 # Добавляем или обновляем оценку (используем INSERT OR REPLACE для простоты: если запись существует, она заменяется)
                 cursor.execute(
                     'INSERT OR REPLACE INTO Grades (student_id, subject_id, grade) VALUES (?, ?, ?)',
                     (payload['student_id'], payload['subject_id'], payload['grade'])
                 )
                 conn.commit()
                 return {'status': 'успех', 'message': 'Оценка успешно добавлена/обновлена.'}
            except sqlite3.IntegrityError as e:
                 if 'FOREIGN KEY constraint failed' in str(e):
                      return {'status': 'ошибка', 'message': 'ID студента или ID предмета не найден.'}
                 else:
                      raise # Перебросить другие ошибки целостности

        elif command == 'update_grade': # Явное обновление оценки (в отличие от add_grade, не создаст запись, если ее нет)
             cursor.execute(
                 'UPDATE Grades SET grade = ? WHERE student_id = ? AND subject_id = ?',
                 (payload['grade'], payload['student_id'], payload['subject_id'])
             )
             if cursor.rowcount > 0:
                 conn.commit()
                 return {'status': 'успех', 'message': 'Оценка успешно обновлена.'}
             else:
                 return {'status': 'ошибка', 'message': 'Оценка для этого студента/предмета не найдена.'}

        elif command == 'delete_grade':
             cursor.execute(
                 'DELETE FROM Grades WHERE student_id = ? AND subject_id = ?',
                 (payload['student_id'], payload['subject_id'])
             )
             if cursor.rowcount > 0:
                 conn.commit()
                 return {'status': 'успех', 'message': 'Оценка успешно удалена.'}
             else:
                 return {'status': 'ошибка', 'message': 'Оценка для этого студента/предмета не найдена.'}

        elif command == 'get_student_average_grade':
             # Расчет среднего балла студента по оценкам в таблице Grades
             sql = """
             SELECT s.full_name, AVG(g.grade) as calculated_average
             FROM Students s
             LEFT JOIN Grades g ON s.id = g.student_id
             WHERE s.id = ? OR s.full_name = ?
             GROUP BY s.id;
             """
             cursor.execute(sql, (payload.get('student_id'), payload.get('student_name')))
             result = cursor.fetchone()
             if result:
                # Обработка случая, когда у студента нет оценок (функция AVG вернет NULL)
                avg_grade = result['calculated_average'] if result['calculated_average'] is not None else 'Оценок пока нет'
                return {'status': 'успех', 'data': {'полное_имя': result['full_name'], 'средний_балл': avg_grade}}
             else:
                return {'status': 'ошибка', 'message': 'Студент не найден.'}


        elif command == 'get_subject_average_grade':
             sql = """
             SELECT sub.subject_name, AVG(g.grade) as average_grade_for_subject
             FROM Subjects sub
             LEFT JOIN Grades g ON sub.id = g.subject_id
             WHERE sub.id = ? OR sub.subject_name = ?
             GROUP BY sub.id;
             """
             cursor.execute(sql, (payload.get('subject_id'), payload.get('subject_name')))
             result = cursor.fetchone()
             if result:
                 # Обработка случая, когда по предмету нет оценок (AVG вернет NULL)
                 avg_grade = result['average_grade_for_subject'] if result['average_grade_for_subject'] is not None else 'Оценок пока нет'
                 return {'status': 'успех', 'data': {'название_предмета': result['subject_name'], 'средний_балл': avg_grade}}
             else:
                 return {'status': 'ошибка', 'message': 'Предмет не найден.'}

        elif command == 'get_students_below_avg':
            try:
                threshold = float(payload['threshold'])
            except ValueError:
                return {'status': 'ошибка', 'message': 'Недопустимое значение порога.'}

            sql = """
             SELECT s.full_name, s.group_name, s.course, AVG(g.grade) as calculated_average
             FROM Students s
             JOIN Grades g ON s.id = g.student_id
             GROUP BY s.id
             HAVING calculated_average < ?
             ORDER BY calculated_average;
             """
            cursor.execute(sql, (threshold,))
            results = [dict(row) for row in cursor.fetchall()]
            return {'status': 'успех', 'data': results}

        else:
            return {'status': 'ошибка', 'message': 'Неизвестная команда'}

    except sqlite3.Error as e:
        logging.error(f"Ошибка базы данных: {e}")
        if conn:
            conn.rollback() # Откатить транзакцию в случае ошибки БД
        return {'status': 'ошибка', 'message': f'Ошибка базы данных: {e}'}
    except KeyError as e: # Если в payload отсутствует ожидаемый ключ
        logging.warning(f"Отсутствует ключ в данных: {e}")
        return {'status': 'ошибка', 'message': f'Отсутствует обязательное поле: {e}'}
    except Exception as e:
        logging.exception("Произошла непредвиденная ошибка") # Залогировать полную трассировку стека
        return {'status': 'ошибка', 'message': f'Произошла непредвиденная ошибка сервера: {e}'}
    finally:
        if conn: # Убедиться, что соединение с БД всегда закрывается
            conn.close()

# --- Сетевая часть ---

def handle_client(conn, addr):
    """Обрабатывает соединение с одним клиентом."""
    logging.info(f"Подключен {addr}")
    try:
        while True:
            # Получаем данные от клиента (до 4096 байт)
            data = conn.recv(4096)
            if not data: # Если recv вернул пустые байты, клиент закрыл соединение
                logging.info(f"Клиент {addr} отключился штатно.")
                break # Выход из цикла обработки этого клиента

            try:
                # Декодируем (UTF-8 по умолчанию) и парсим JSON запрос
                request = json.loads(data.decode('utf-8'))
                logging.info(f"Получено от {addr}: {request}")

                # Обрабатываем запрос
                response = handle_request(request)

                # Отправляем JSON ответ клиенту (кодируем в UTF-8)
                conn.sendall(json.dumps(response).encode('utf-8'))
                logging.info(f"Отправлено {addr}: {response}")

            except json.JSONDecodeError: # Если клиент прислал невалидный JSON
                logging.error(f"От {addr} получен неверный JSON")
                error_response = {'status': 'ошибка', 'message': 'Неверный формат JSON'}
                conn.sendall(json.dumps(error_response).encode('utf-8'))
            except Exception as e: # Обработка других ошибок при обработке запроса
                 logging.exception(f"Ошибка обработки запроса от {addr}")
                 error_response = {'status': 'ошибка', 'message': f'Ошибка обработки на сервере: {e}'}
                 conn.sendall(json.dumps(error_response).encode('utf-8'))


    except ConnectionResetError: # Если клиент разорвал соединение неожиданно
         logging.warning(f"Соединение с клиентом {addr} сброшено.")
    except Exception as e: # Другие возможные ошибки на уровне сокета/потока
         logging.exception(f"Ошибка обработки клиента {addr}")
    finally:
        logging.info(f"Закрытие соединения с {addr}")
        conn.close() # Закрыть сокет клиента

def start_server():
    """Запускает TCP сервер."""
    init_db() # Инициализировать/проверить БД при старте сервера

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # Создание TCP сокета
        s.bind((HOST, PORT)) # Привязка к адресу и порту
        s.listen() # Начало прослушивания входящих соединений
        logging.info(f"Сервер слушает на {HOST}:{PORT}")
        while True: # Бесконечный цикл для приема новых клиентов
            conn, addr = s.accept() # Принять новое соединение (блокирующая операция)
            # Создаем новый поток для обработки каждого клиента, чтобы сервер не блокировался
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True # Устанавливаем поток как демон, чтобы он завершился при выходе основного потока
            client_thread.start() # Запускаем поток

if __name__ == "__main__": # Точка входа при запуске скрипта напрямую
    start_server()
