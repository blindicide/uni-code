import socket
import os
import time
import json
import base64
import subprocess
import sys # Добавлено для определения платформы
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hmac
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import mss # Для снимков экрана

# Параметры Диффи-Хеллмана (можно использовать стандартные группы)
# Используем предопределенные параметры группы 2048-бит MODP (RFC 3526)
parameters = dh.generate_parameters(generator=2, key_size=2048, backend=default_backend())

# Константы
HOST = '127.0.0.1'  # Слушаем на локальном хосте
PORT = 62001        # Порт для прослушивания
SALT = b'some_fixed_salt_16_bytes' # Фиксированная соль для KDF (16 байт)
HMAC_KEY_LEN = 32   # Длина ключа HMAC (SHA3_256 -> 32 байта)
ENC_KEY_LEN = 32    # Длина ключа шифрования (ChaCha20 -> 32 байта)
IV_LEN = 16         # Длина IV для ChaCha20 (рекомендуется 16 байт)

def generate_keys(shared_secret):
    """Генерирует ключ шифрования и ключ HMAC из общего секрета с помощью PBKDF2HMAC."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA3_256(),
        length=ENC_KEY_LEN + HMAC_KEY_LEN,
        salt=SALT,
        iterations=100000, # Рекомендуемое количество итераций
        backend=default_backend()
    )
    derived_key = kdf.derive(shared_secret)
    enc_key = derived_key[:ENC_KEY_LEN]
    hmac_key = derived_key[ENC_KEY_LEN:]
    # print(f"Сервер: Сгенерирован ключ шифрования: {enc_key.hex()}") # Убрано для краткости
    # print(f"Сервер: Сгенерирован ключ HMAC: {hmac_key.hex()}") # Убрано для краткости
    print("Сервер: Ключи шифрования и HMAC сгенерированы.")
    return enc_key, hmac_key

def decrypt_and_verify(data, enc_key, hmac_key):
    """Расшифровывает и проверяет сообщение."""
    try:
        timestamp_bytes = data[:8]
        iv = data[8:8 + IV_LEN]
        hmac_tag = data[-(HMAC_KEY_LEN):]
        cipher_text = data[8 + IV_LEN:-(HMAC_KEY_LEN)]

        # Проверка HMAC
        h = hmac.HMAC(hmac_key, hashes.SHA3_256(), backend=default_backend())
        h.update(timestamp_bytes + iv + cipher_text)
        h.verify(hmac_tag)
        # print("Сервер: HMAC верифицирован успешно.") # Убрано для краткости

        # Проверка временной метки (например, отклонение не более 60 секунд)
        timestamp = int.from_bytes(timestamp_bytes, 'big')
        current_time = int(time.time())
        if abs(current_time - timestamp) > 60:
            print(f"Сервер: Ошибка временной метки. Получено: {timestamp}, Текущее: {current_time}")
            return None # Отклоняем старые сообщения

        # Расшифровка ChaCha20
        cipher = Cipher(algorithms.ChaCha20(enc_key, iv), mode=None, backend=default_backend())
        decryptor = cipher.decryptor()
        padded_plain_text = decryptor.update(cipher_text) + decryptor.finalize()

        # Удаление паддинга ANSIX923
        unpadder = padding.ANSIX923(128).unpadder() # Используем 128 бит для согласованности с клиентом
        plain_text = unpadder.update(padded_plain_text) + unpadder.finalize()

        # print("Сервер: Сообщение расшифровано успешно.") # Убрано для краткости
        return plain_text.decode('utf-8')
    except hmac.InvalidSignature:
        print("Сервер: Ошибка верификации HMAC!")
        return None
    except ValueError as e:
        print(f"Сервер: Ошибка расшифровки или удаления паддинга: {e}")
        return None
    except Exception as e:
        print(f"Сервер: Неизвестная ошибка при расшифровке: {e}")
        return None

def encrypt_and_sign(data, enc_key, hmac_key):
    """Шифрует и подписывает сообщение."""
    timestamp = int(time.time())
    timestamp_bytes = timestamp.to_bytes(8, 'big')
    iv = os.urandom(IV_LEN)

    # Паддинг ANSIX923
    padder = padding.ANSIX923(128).padder() # Используем 128 бит для согласованности с клиентом
    padded_data = padder.update(data.encode('utf-8')) + padder.finalize()

    # Шифрование ChaCha20
    cipher = Cipher(algorithms.ChaCha20(enc_key, iv), mode=None, backend=default_backend())
    encryptor = cipher.encryptor()
    cipher_text = encryptor.update(padded_data) + encryptor.finalize()

    # Генерация HMAC
    h = hmac.HMAC(hmac_key, hashes.SHA3_256(), backend=default_backend())
    h.update(timestamp_bytes + iv + cipher_text)
    hmac_tag = h.finalize()

    # print("Сервер: Сообщение зашифровано и подписано.") # Убрано для краткости
    return timestamp_bytes + iv + cipher_text + hmac_tag

def execute_command(command_data):
    """Выполняет команду на сервере."""
    try:
        command_json = json.loads(command_data)
        command_number = command_json.get("command_number")
        command_body = command_json.get("command_body")

        print(f"Сервер: Получена команда {command_number} с телом: {command_body}")

        if command_number == 1: # Выполнить произвольную cmd-команду
            if not command_body:
                return json.dumps({"status": "error", "message": "Тело команды не может быть пустым для команды 1"})
            try:
                # Выполняем команду и получаем вывод
                # Используем 'cp866' для корректного декодирования вывода cmd в Windows (русская локаль)
                result = subprocess.run(command_body, shell=True, capture_output=True, text=True, encoding='cp866', errors='replace', check=False)
                output = result.stdout if result.stdout else ""
                error_output = result.stderr if result.stderr else ""
                response_message = f"Вывод команды:\n{output}\nОшибки:\n{error_output}"
                return json.dumps({"status": "success", "message": response_message})
            except Exception as e:
                return json.dumps({"status": "error", "message": f"Ошибка выполнения команды: {e}"})

        elif command_number == 2: # Скачать файл
            if not command_body:
                return json.dumps({"status": "error", "message": "Не указан путь к файлу для команды 2"})
            file_path = command_body
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                    # Кодируем файл в base64 для безопасной передачи
                    encoded_file_data = base64.b64encode(file_data).decode('utf-8')
                    return json.dumps({"status": "success", "filename": os.path.basename(file_path), "data": encoded_file_data})
                except Exception as e:
                    return json.dumps({"status": "error", "message": f"Ошибка чтения файла: {e}"})
            else:
                return json.dumps({"status": "error", "message": f"Файл не найден: {file_path}"})

        elif command_number == 3: # Получить снимок экрана
             try:
                 with mss.mss() as sct:
                     # Захватываем основной монитор
                     monitor = sct.monitors[1] # [0] - все мониторы, [1] - основной
                     sct_img = sct.grab(monitor)
                     # Конвертируем в PNG байты
                     img_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
                 # Кодируем в base64
                 encoded_img = base64.b64encode(img_bytes).decode('utf-8')
                 return json.dumps({"status": "success", "image_data": encoded_img})
             except Exception as e:
                 return json.dumps({"status": "error", "message": f"Ошибка получения снимка экрана: {e}"})

        else:
            return json.dumps({"status": "error", "message": f"Неизвестный номер команды: {command_number}"})

    except json.JSONDecodeError:
        return json.dumps({"status": "error", "message": "Ошибка декодирования JSON команды"})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Общая ошибка обработки команды: {e}"})


def handle_client(conn, addr):
    """Обрабатывает соединение с клиентом."""
    print(f"Сервер: Подключение от {addr}")
    try:
        # 1. Обмен ключами Диффи-Хеллмана
        # Генерация приватного ключа сервера
        server_private_key = parameters.generate_private_key()
        # Получение публичного ключа сервера в формате PEM
        server_public_key_bytes = server_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        # Отправка публичного ключа сервера клиенту
        conn.sendall(server_public_key_bytes)
        # print("Сервер: Публичный ключ отправлен клиенту.") # Убрано для краткости

        # Получение публичного ключа клиента
        client_public_key_bytes = conn.recv(2048) # Размер буфера может потребоваться увеличить
        if not client_public_key_bytes:
            print("Сервер: Клиент не отправил публичный ключ.")
            return
        client_public_key = serialization.load_pem_public_key(
            client_public_key_bytes,
            backend=default_backend()
        )
        # print("Сервер: Публичный ключ клиента получен.") # Убрано для краткости

        # Вычисление общего секрета
        shared_secret = server_private_key.exchange(client_public_key)
        # print(f"Сервер: Общий секрет вычислен (первые 16 байт): {shared_secret[:16].hex()}...") # Убрано для краткости

        # 2. Генерация ключей шифрования и HMAC
        enc_key, hmac_key = generate_keys(shared_secret)

        # 3. Цикл обработки команд
        while True:
            # Получение данных от клиента (размер может варьироваться)
            # Сначала получаем размер сообщения (например, 4 байта)
            size_bytes = conn.recv(4)
            if not size_bytes:
                print("Сервер: Клиент разорвал соединение (не получены данные о размере).")
                break
            message_size = int.from_bytes(size_bytes, 'big')

            # Получаем само сообщение
            encrypted_data = b''
            while len(encrypted_data) < message_size:
                chunk = conn.recv(min(4096, message_size - len(encrypted_data)))
                if not chunk:
                    print("Сервер: Клиент разорвал соединение (не получены полные данные).")
                    return # Выходим, если соединение разорвано во время чтения
                encrypted_data += chunk

            if not encrypted_data:
                print("Сервер: Клиент разорвал соединение.")
                break

            print(f"Сервер: Получено зашифрованное сообщение ({len(encrypted_data)} байт): {encrypted_data.hex()}") # Выводим все сообщение

            # Расшифровка и проверка
            command_data = decrypt_and_verify(encrypted_data, enc_key, hmac_key)

            if command_data:
                # Выполнение команды
                response_data = execute_command(command_data)
                # print(f"Сервер: Результат выполнения: {response_data[:200]}...") # Убрано для краткости

                # Шифрование и отправка ответа
                encrypted_response = encrypt_and_sign(response_data, enc_key, hmac_key)

                # Отправляем размер ответа, затем сам ответ
                response_size_bytes = len(encrypted_response).to_bytes(4, 'big')
                conn.sendall(response_size_bytes)
                conn.sendall(encrypted_response)
                print(f"Сервер: Зашифрованный ответ ({len(encrypted_response)} байт) отправлен: {encrypted_response.hex()}") # Выводим весь ответ
            else:
                # Отправляем сообщение об ошибке расшифровки/проверки
                error_message = json.dumps({"status": "error", "message": "Ошибка обработки входящего сообщения на сервере"})
                encrypted_error = encrypt_and_sign(error_message, enc_key, hmac_key)
                error_size_bytes = len(encrypted_error).to_bytes(4, 'big')
                conn.sendall(error_size_bytes)
                conn.sendall(encrypted_error)
                print(f"Сервер: Сообщение об ошибке отправлено клиенту: {encrypted_error.hex()}") # Выводим сообщение об ошибке
                # Можно разорвать соединение при серьезных ошибках
                # break

    except ConnectionResetError:
        print(f"Сервер: Соединение с {addr} сброшено клиентом.")
    except BrokenPipeError:
         print(f"Сервер: Соединение с {addr} разорвано (Broken pipe).")
    except Exception as e:
        print(f"Сервер: Произошла ошибка при обработке клиента {addr}: {e}")
    finally:
        print(f"Сервер: Закрытие соединения с {addr}")
        conn.close()

def start_server():
    """Запускает сервер."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f'Сервер системы "Телескоп" запущен и слушает на {HOST}:{PORT}')
        while True:
            try:
                conn, addr = s.accept()
                # Обработка клиента в отдельном потоке/процессе была бы лучше для >1 клиента,
                # но для простоты делаем последовательно.
                handle_client(conn, addr)
            except KeyboardInterrupt:
                print("\nСервер: Получен сигнал прерывания. Завершение работы...")
                break
            except Exception as e:
                print(f"Сервер: Ошибка при принятии соединения: {e}")

if __name__ == "__main__":
    # Установка зависимостей (если нужно)
    try:
        import cryptography
        import mss
    except ImportError:
        print("Пожалуйста, установите необходимые библиотеки:")
        print("pip install cryptography mss")
        # Используем sys.exit вместо exit() для большей стандартности
        sys.exit(1)
    start_server()
