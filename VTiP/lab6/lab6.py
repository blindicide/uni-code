# -*- coding: utf-8 -*-

import psutil
import logging
import schedule
import time
import datetime
import os
import sys
import ctypes

# --- Конфигурация ---

# 1. Мониторинг CPU
CPU_THRESHOLD_PERCENT = 80.0  # Порог использования CPU в %

# 2. Мониторинг Диска (Вариант 1)
DISK_PATH = 'C:\\'  # Путь для проверки (можно изменить на 'D:\\', '/', и т.д.)
DISK_THRESHOLD_PERCENT = 10.0 # Порог свободного места в % (предупреждение, если СВОБОДНО МЕНЬШЕ этого значения)

# 3. Планировщик
MONITORING_INTERVAL_SECONDS = 60 # Интервал запуска проверок CPU и Диска в секундах

# 4. Мониторинг Приложений
APP_LOG_FILE = 'application_monitor.log' # Файл для логов запуска/остановки приложений
APP_MONITOR_INTERVAL_SECONDS = 5 # Интервал проверки процессов
# "Черный" список приложений (имена процессов в нижнем регистре),
# чьи запуск и остановка НЕ будут регистрироваться
APP_BLACKLIST = {
    "svchost.exe",
    "runtimebroker.exe",
    "explorer.exe",
    "conhost.exe",
    "taskhostw.exe",
    "system idle process",
    "system",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "winlogon.exe",
    "fontdrvhost.exe",
    "dwm.exe",
    "sihost.exe",
    "ctfmon.exe",
    "memory compression", # Имя процесса в Диспетчере задач может отличаться
    "python.exe",         # Исключаем сам скрипт
    "pythonw.exe",        # Исключаем сам скрипт (при запуске в скрытом режиме)
    # Добавьте другие системные или нежелательные процессы
}
# Список приложений для автоматического завершения (имена процессов в нижнем регистре)
APPS_TO_TERMINATE = {
    "notepad.exe",
    "calc.exe",
    # Добавьте другие приложения для завершения
}

# Настройка основного логгера (для CPU и Диска)
LOG_FILE_GENERAL = 'system_monitor.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_GENERAL, encoding='utf-8'),
        logging.StreamHandler(sys.stdout) # Вывод также в консоль
    ]
)

# --- Глобальные переменные для мониторинга приложений ---
# Словарь для хранения информации о запущенных процессах {pid: {"name": name, "start_time": start_time}}
running_processes = {}

# --- Функции Мониторинга ---

# 1. Проверка использования CPU
def check_cpu_usage(threshold):
    """
    Проверяет текущее использование CPU и логирует/выводит предупреждение при превышении порога.
    """
    try:
        # interval=1 позволяет получить более сглаженное значение за последнюю секунду
        cpu_usage = psutil.cpu_percent(interval=1)
        logging.info(f"Текущее использование CPU: {cpu_usage}%")
        if cpu_usage > threshold:
            warning_message = f"ПРЕДУПРЕЖДЕНИЕ: Высокое использование CPU! Текущее значение: {cpu_usage}%, Порог: {threshold}%"
            logging.warning(warning_message)
            print(warning_message) # Дополнительный вывод в консоль для наглядности
    except Exception as e:
        logging.error(f"Ошибка при проверке CPU: {e}")

# 2. Проверка использования диска (Вариант 1)
def check_disk_usage(path, threshold_percent):
    """
    Проверяет использование дискового пространства по заданному пути.
    Логирует и выводит предупреждение, если СВОБОДНОЕ пространство ниже порога.
    """
    try:
        disk_usage = psutil.disk_usage(path)
        total_gb = disk_usage.total / (1024**3)
        used_gb = disk_usage.used / (1024**3)
        free_gb = disk_usage.free / (1024**3)
        free_percent = (disk_usage.free / disk_usage.total) * 100

        logging.info(f"Диск {path}: Всего: {total_gb:.2f} GB, Использовано: {used_gb:.2f} GB ({disk_usage.percent}%), Свободно: {free_gb:.2f} GB ({free_percent:.2f}%)")

        if free_percent < threshold_percent:
            warning_message = (f"ПРЕДУПРЕЖДЕНИЕ: Низкий уровень свободного места на диске {path}! "
                               f"Свободно: {free_percent:.2f}%, Порог: {threshold_percent}%")
            logging.warning(warning_message)
            print(warning_message) # Дополнительный вывод в консоль
    except FileNotFoundError:
        logging.error(f"Ошибка при проверке диска: Путь '{path}' не найден.")
    except Exception as e:
        logging.error(f"Ошибка при проверке диска {path}: {e}")

# 4. Мониторинг Приложений
def log_app_event(event_type, process, log_file=APP_LOG_FILE):
    """
    Записывает событие запуска или остановки приложения в лог-файл.
    """
    try:
        pid = process.pid
        name = process.name()
        mem_rss = process.memory_info().rss / (1024 * 1024) # Память в МБ
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_entry = f'"{name}" "{pid}" "{mem_rss:.2f} MB" "{timestamp}" "{event_type}"\n'

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        # print(f"Залогировано событие: {log_entry.strip()}") # Для отладки

    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        # Процесс мог завершиться между проверками
        pass
    except Exception as e:
        print(f"Ошибка записи лога приложения: {e}") # Выводим ошибку логгирования в консоль


def monitor_applications():
    """
    Основная функция мониторинга запуска и остановки приложений.
    Обновляет глобальный словарь running_processes.
    Завершает приложения из списка APPS_TO_TERMINATE.
    """
    global running_processes
    current_pids = set(psutil.pids())
    known_pids = set(running_processes.keys())

    # 1. Обнаружение новых процессов
    new_pids = current_pids - known_pids
    for pid in new_pids:
        try:
            process = psutil.Process(pid)
            p_name_lower = process.name().lower()

            # Добавляем в словарь отслеживаемых, если не в черном списке
            if p_name_lower not in APP_BLACKLIST:
                start_time = datetime.datetime.fromtimestamp(process.create_time())
                running_processes[pid] = {"name": process.name(), "start_time": start_time}
                log_app_event("ЗАПУСК", process)
                print(f"Обнаружен запуск: {process.name()} (PID: {pid})")

                # Проверка на авто-завершение
                if p_name_lower in APPS_TO_TERMINATE:
                    try:
                        print(f"Попытка автоматического завершения процесса: {process.name()} (PID: {pid})")
                        process.terminate() # Мягкое завершение
                        # Можно подождать и использовать kill(), если terminate не сработал
                        # time.sleep(1)
                        # if process.is_running(): process.kill()
                        logging.info(f"Автоматически завершен процесс: {process.name()} (PID: {pid})")
                        # Логируем остановку сразу после попытки завершения
                        # Примечание: фактическое время остановки может быть чуть позже,
                        # но для лога фиксируем момент команды на завершение.
                        # Пересоздаем объект process, т.к. старый может быть невалидным после terminate
                        try:
                            terminated_process = psutil.Process(pid)
                            log_app_event("ОСТАНОВКА (Авто)", terminated_process)
                        except psutil.NoSuchProcess: # Процесс уже завершился
                             # Создаем "фейковый" объект с нужными данными для лога, если нужно
                             # Но проще пропустить лог остановки в этом сценарии,
                             # т.к. точное время и память уже неизвестны.
                             pass
                        # Удаляем из running_processes, т.к. мы его завершили
                        if pid in running_processes:
                             del running_processes[pid]


                    except (psutil.NoSuchProcess, psutil.AccessDenied) as term_err:
                        logging.error(f"Не удалось автоматически завершить процесс {p_name_lower} (PID: {pid}): {term_err}")
                    except Exception as e:
                         logging.error(f"Неизвестная ошибка при завершении процесса {p_name_lower} (PID: {pid}): {e}")


        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Процесс мог появиться и исчезнуть между psutil.pids() и psutil.Process(pid)
            continue
        except Exception as e:
            logging.error(f"Ошибка при обработке нового процесса PID {pid}: {e}")

    # 2. Обнаружение завершенных процессов
    terminated_pids = known_pids - current_pids
    for pid in terminated_pids:
        if pid in running_processes: # Убедимся, что процесс был в нашем списке отслеживаемых
            # Получаем имя из сохраненных данных, т.к. process = psutil.Process(pid) уже вызовет ошибку
            terminated_process_info = running_processes[pid]
            p_name_lower = terminated_process_info["name"].lower()

            if p_name_lower not in APP_BLACKLIST:
                 # Создаем "заглушку" Process объекта для функции логирования,
                 # если она требует объект Process. Либо передаем данные напрямую.
                 # Здесь проще передать данные, но для унификации создадим mock-объект.
                 class MockProcess:
                     def __init__(self, pid, name):
                         self.pid = pid
                         self._name = name
                     def name(self): return self._name
                     def memory_info(self): # Возвращаем "пустые" данные о памяти
                         class MockMemInfo: rss = 0
                         return MockMemInfo()

                 mock_proc = MockProcess(pid, terminated_process_info["name"])
                 log_app_event("ОСТАНОВКА", mock_proc)
                 print(f"Обнаружена остановка: {terminated_process_info['name']} (PID: {pid})")


            # Удаляем из словаря отслеживаемых
            del running_processes[pid]


# Функция для скрытия консольного окна (только для Windows)
def hide_console():
    """Скрывает консольное окно, если скрипт запущен через pythonw.exe"""
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd != 0:
            ctypes.windll.user32.ShowWindow(hwnd, 0) # 0 = SW_HIDE
            ctypes.windll.kernel32.CloseHandle(hwnd)
            print("Консольное окно скрыто (если запущено через pythonw.exe).")
    except Exception as e:
        print(f"Не удалось скрыть консольное окно: {e}")


# --- Основной блок ---
if __name__ == "__main__":
    print("Запуск скрипта мониторинга...")
    logging.info("Скрипт мониторинга запущен.")

    # Попытка скрыть консоль ( сработает только при запуске через pythonw.exe )
    # hide_console() # Раскомментируйте, если хотите попробовать скрыть окно

    # 3. Настройка расписания для CPU и Диска
    schedule.every(MONITORING_INTERVAL_SECONDS).seconds.do(check_cpu_usage, threshold=CPU_THRESHOLD_PERCENT)
    schedule.every(MONITORING_INTERVAL_SECONDS).seconds.do(check_disk_usage, path=DISK_PATH, threshold_percent=DISK_THRESHOLD_PERCENT)

    # Инициализация списка процессов перед основным циклом
    print("Первоначальное сканирование процессов...")
    try:
        initial_pids = psutil.pids()
        for pid in initial_pids:
            try:
                p = psutil.Process(pid)
                p_name_lower = p.name().lower()
                if p_name_lower not in APP_BLACKLIST:
                    running_processes[pid] = {"name": p.name(), "start_time": datetime.datetime.fromtimestamp(p.create_time())}
                    # Начальные процессы не логируем как "ЗАПУСК", чтобы лог не засорялся при старте
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue # Игнорируем процессы, которые исчезли или недоступны
        print(f"Инициализация завершена. Отслеживается {len(running_processes)} процессов (не из черного списка).")
    except Exception as e:
        logging.error(f"Ошибка при инициализации списка процессов: {e}")
        print(f"Критическая ошибка при инициализации: {e}. Скрипт может работать некорректно.")


    # Основной цикл
    print(f"Начало основного цикла мониторинга. Интервал проверок CPU/Диска: {MONITORING_INTERVAL_SECONDS} сек. Интервал проверки приложений: {APP_MONITOR_INTERVAL_SECONDS} сек.")
    last_app_check_time = time.time()

    try:
        while True:
            # Запуск запланированных задач (CPU, Диск)
            schedule.run_pending()

            # Запуск мониторинга приложений с его собственным интервалом
            current_time = time.time()
            if current_time - last_app_check_time >= APP_MONITOR_INTERVAL_SECONDS:
                 # print("Выполняется проверка приложений...") # Для отладки
                 monitor_applications()
                 last_app_check_time = current_time

            # Пауза на 1 секунду, чтобы не загружать CPU на 100%
            # и дать возможность сработать другим интервалам
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nЗавершение работы скрипта по команде пользователя (Ctrl+C).")
        logging.info("Скрипт остановлен вручную.")
    except Exception as e:
        logging.critical(f"Критическая ошибка в основном цикле: {e}", exc_info=True)
        print(f"Критическая ошибка: {e}")