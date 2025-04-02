import socket
import os
import time
import json
import base64
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hmac
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Константы (должны совпадать с серверными)
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 62001
SALT = b'' # Соль будет получена от сервера (или должна быть предопределена и одинакова)
           # В текущей реализации сервера соль генерируется случайно и не передается.
           # Для корректной работы KDF соль ДОЛЖНА быть одинаковой.
           # Исправим это: будем использовать фиксированную соль.
           # ВАЖНО: В server.py тоже нужно заменить os.urandom(16) на эту же соль.
FIXED_SALT = b'some_fixed_salt_16_bytes' # 16 байт
HMAC_KEY_LEN = 32
ENC_KEY_LEN = 32
IV_LEN = 16

# Глобальные переменные для ключей
enc_key = None
hmac_key = None

def generate_keys(shared_secret):
    """Генерирует ключ шифрования и ключ HMAC из общего секрета с помощью PBKDF2HMAC."""
    global enc_key, hmac_key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA3_256(),
        length=ENC_KEY_LEN + HMAC_KEY_LEN,
        salt=FIXED_SALT, # Используем фиксированную соль
        iterations=100000,
        backend=default_backend()
    )
    derived_key = kdf.derive(shared_secret)
    enc_key = derived_key[:ENC_KEY_LEN]
    hmac_key = derived_key[ENC_KEY_LEN:]
    # print(f"Клиент: Сгенерирован ключ шифрования: {enc_key.hex()}") # Убрано для краткости
    # print(f"Клиент: Сгенерирован ключ HMAC: {hmac_key.hex()}") # Убрано для краткости
    print("Клиент: Ключи шифрования и HMAC сгенерированы.")

def encrypt_and_sign(data, current_enc_key, current_hmac_key):
    """Шифрует и подписывает сообщение."""
    if not current_enc_key or not current_hmac_key:
        raise ValueError("Ключи шифрования/HMAC не установлены.")

    timestamp = int(time.time())
    timestamp_bytes = timestamp.to_bytes(8, 'big')
    iv = os.urandom(IV_LEN)

    # Паддинг ANSIX923
    # ChaCha20 не требует выравнивания по блокам в традиционном смысле,
    # но API padding требует размер блока. Используем 16 (128 бит) как типичный размер.
    padder = padding.ANSIX923(128).padder() # Размер блока 128 бит
    padded_data = padder.update(data.encode('utf-8')) + padder.finalize()

    # Шифрование ChaCha20
    cipher = Cipher(algorithms.ChaCha20(current_enc_key, iv), mode=None, backend=default_backend())
    encryptor = cipher.encryptor()
    cipher_text = encryptor.update(padded_data) + encryptor.finalize()

    # Генерация HMAC
    h = hmac.HMAC(current_hmac_key, hashes.SHA3_256(), backend=default_backend())
    h.update(timestamp_bytes + iv + cipher_text)
    hmac_tag = h.finalize()

    # print("Клиент: Сообщение зашифровано и подписано.") # Убрано для краткости
    return timestamp_bytes + iv + cipher_text + hmac_tag

def decrypt_and_verify(data, current_enc_key, current_hmac_key):
    """Расшифровывает и проверяет сообщение."""
    if not current_enc_key or not current_hmac_key:
        raise ValueError("Ключи шифрования/HMAC не установлены.")

    try:
        timestamp_bytes = data[:8]
        iv = data[8:8 + IV_LEN]
        hmac_tag = data[-(HMAC_KEY_LEN):]
        cipher_text = data[8 + IV_LEN:-(HMAC_KEY_LEN)]

        # Проверка HMAC
        h = hmac.HMAC(current_hmac_key, hashes.SHA3_256(), backend=default_backend())
        h.update(timestamp_bytes + iv + cipher_text)
        h.verify(hmac_tag)
        # print("Клиент: HMAC верифицирован успешно.") # Убрано для краткости

        # Проверка временной метки (опционально, но полезно)
        timestamp = int.from_bytes(timestamp_bytes, 'big')
        current_time = int(time.time())
        if abs(current_time - timestamp) > 60:
            print(f"Клиент: Предупреждение: Большая разница во времени с сервером. Получено: {timestamp}, Текущее: {current_time}")
            # Не отклоняем, но предупреждаем

        # Расшифровка ChaCha20
        cipher = Cipher(algorithms.ChaCha20(current_enc_key, iv), mode=None, backend=default_backend())
        decryptor = cipher.decryptor()
        padded_plain_text = decryptor.update(cipher_text) + decryptor.finalize()

        # Удаление паддинга ANSIX923
        unpadder = padding.ANSIX923(128).unpadder() # Размер блока 128 бит
        plain_text = unpadder.update(padded_plain_text) + unpadder.finalize()

        # print("Клиент: Сообщение расшифровано успешно.") # Убрано для краткости
        return plain_text.decode('utf-8')
    except hmac.InvalidSignature:
        print("Клиент: Ошибка верификации HMAC!")
        return None
    except ValueError as e:
        print(f"Клиент: Ошибка расшифровки или удаления паддинга: {e}")
        return None
    except Exception as e:
        print(f"Клиент: Неизвестная ошибка при расшифровке: {e}")
        return None

def handle_response(response_data):
    """Обрабатывает расшифрованный ответ от сервера."""
    try:
        response_json = json.loads(response_data)
        status = response_json.get("status")
        print("-" * 30)
        if status == "success":
            if "message" in response_json:
                print("Ответ сервера:")
                print(response_json["message"])
            elif "filename" in response_json and "data" in response_json:
                filename = response_json["filename"]
                file_data_b64 = response_json["data"]
                try:
                    file_data = base64.b64decode(file_data_b64)
                    # Сохраняем в подпапку VTiP/lab4/downloads
                    save_dir = os.path.join("VTiP", "lab4", "downloads")
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, filename)
                    with open(save_path, 'wb') as f:
                        f.write(file_data)
                    print(f"Файл '{filename}' успешно скачан и сохранен как '{save_path}'")
                except (base64.binascii.Error, IOError) as e:
                    print(f"Ошибка при сохранении файла '{filename}': {e}")
            elif "image_data" in response_json:
                img_data_b64 = response_json["image_data"]
                try:
                    img_data = base64.b64decode(img_data_b64)
                    # Сохраняем в подпапку VTiP/lab4/screenshots
                    save_dir = os.path.join("VTiP", "lab4", "screenshots")
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, f"screenshot_{int(time.time())}.png")
                    with open(save_path, 'wb') as f:
                        f.write(img_data)
                    print(f"Снимок экрана сохранен как '{save_path}'")
                    # Опционально: попытка открыть изображение
                    try:
                        if os.name == 'nt': # Windows
                            os.startfile(save_path)
                        elif os.name == 'posix': # macOS, Linux
                            subprocess.call(('open', save_path) if sys.platform == 'darwin' else ('xdg-open', save_path))
                    except Exception as open_e:
                        print(f"(Не удалось автоматически открыть изображение: {open_e})")
                except (base64.binascii.Error, IOError) as e:
                    print(f"Ошибка при сохранении снимка экрана: {e}")
            else:
                print("Успешный ответ от сервера, но формат неизвестен.")
                print(response_data)

        elif status == "error":
            print("Ошибка от сервера:")
            print(response_json.get("message", "Нет деталей об ошибке."))
        else:
            print("Неизвестный статус ответа от сервера:")
            print(response_data)
        print("-" * 30)

    except json.JSONDecodeError:
        print("Ошибка: Не удалось декодировать JSON ответа от сервера.")
        print("Сырой ответ:")
        print(response_data)
        print("-" * 30)
    except Exception as e:
        print(f"Ошибка при обработке ответа: {e}")
        print("-" * 30)


def main():
    global enc_key, hmac_key
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print('Клиент системы дистанционного управления "Телескоп" включён.')
            print(f"Клиент: Подключение к {SERVER_HOST}:{SERVER_PORT}...")
            s.connect((SERVER_HOST, SERVER_PORT))
            print("Клиент: Соединение установлено.")

            # 1. Обмен ключами Диффи-Хеллмана
            # Получение публичного ключа сервера
            server_public_key_bytes = s.recv(2048) # Размер буфера
            if not server_public_key_bytes:
                print("Клиент: Сервер не отправил публичный ключ.")
                return
            server_public_key = serialization.load_pem_public_key(
                server_public_key_bytes,
                backend=default_backend()
            )
            print("Клиент: Публичный ключ сервера получен.")

            # Генерация пары ключей клиента на основе параметров сервера
            client_private_key = server_public_key.parameters().generate_private_key()
            client_public_key_bytes = client_private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            # Отправка публичного ключа клиента серверу
            s.sendall(client_public_key_bytes)
            # print("Клиент: Публичный ключ клиента отправлен.") # Убрано для краткости

            # Вычисление общего секрета
            shared_secret = client_private_key.exchange(server_public_key)
            # print(f"Клиент: Общий секрет вычислен (первые 16 байт): {shared_secret[:16].hex()}...") # Убрано для краткости

            # 2. Генерация ключей шифрования и HMAC
            generate_keys(shared_secret)

            # 3. Цикл взаимодействия с пользователем
            while True:
                print("\nДоступные команды:")
                print("  1 <команда> - Выполнить cmd-команду (например, 1 dir)")
                print("  2 <путь_к_файлу> - Скачать файл с сервера (например, 2 C:\\Users\\Public\\Documents\\example.txt)")
                print("  3 - Получить снимок экрана сервера")
                print("  exit - Выйти")

                user_input = input("Введите команду: ").strip()
                if not user_input:
                    continue
                if user_input.lower() == 'exit':
                    break

                parts = user_input.split(" ", 1)
                try:
                    command_number = int(parts[0])
                    command_body = parts[1] if len(parts) > 1 else None

                    if command_number not in [1, 2, 3]:
                        print("Неверный номер команды.")
                        continue
                    if command_number == 1 and not command_body:
                        print("Для команды 1 необходимо указать тело команды.")
                        continue
                    if command_number == 2 and not command_body:
                        print("Для команды 2 необходимо указать путь к файлу.")
                        continue
                    if command_number == 3 and command_body:
                        print("Для команды 3 тело команды не требуется.")
                        command_body = None # Игнорируем тело для команды 3

                except (ValueError, IndexError):
                    print("Неверный формат ввода. Используйте 'номер_команды [тело_команды]'")
                    continue

                # Формирование JSON
                command_json = {"command_number": command_number}
                if command_body:
                    command_json["command_body"] = command_body

                command_str = json.dumps(command_json)
                print(f"Клиент: Отправка команды: {command_str}")

                # Шифрование и подпись
                encrypted_command = encrypt_and_sign(command_str, enc_key, hmac_key)

                # Отправка размера и данных
                command_size_bytes = len(encrypted_command).to_bytes(4, 'big')
                s.sendall(command_size_bytes)
                s.sendall(encrypted_command)
                print(f"Клиент: Зашифрованная команда ({len(encrypted_command)} байт) отправлена: {encrypted_command.hex()}") # Выводим всю команду

                # Получение ответа
                # Сначала получаем размер ответа
                response_size_bytes = s.recv(4)
                if not response_size_bytes:
                    print("Клиент: Сервер разорвал соединение (не получен размер ответа).")
                    break
                response_size = int.from_bytes(response_size_bytes, 'big')
                print(f"Клиент: Ожидается ответ размером {response_size} байт.")

                # Получаем сам ответ
                encrypted_response = b''
                while len(encrypted_response) < response_size:
                    chunk = s.recv(min(4096, response_size - len(encrypted_response)))
                    if not chunk:
                        print("Клиент: Сервер разорвал соединение (не получен полный ответ).")
                        return # Выходим
                    encrypted_response += chunk

                print(f"Клиент: Получен зашифрованный ответ ({len(encrypted_response)} байт): {encrypted_response.hex()}") # Выводим весь ответ

                # Расшифровка и проверка
                response_data = decrypt_and_verify(encrypted_response, enc_key, hmac_key)

                if response_data:
                    handle_response(response_data)
                else:
                    print("Клиент: Не удалось обработать ответ от сервера.")

    except ConnectionRefusedError:
        print(f"Клиент: Ошибка подключения. Сервер {SERVER_HOST}:{SERVER_PORT} недоступен.")
    except ConnectionAbortedError:
         print("Клиент: Соединение было разорвано сервером.")
    except BrokenPipeError:
         print("Клиент: Соединение с сервером потеряно (Broken pipe).")
    except Exception as e:
        print(f"Клиент: Произошла непредвиденная ошибка: {e}")
    finally:
        print("Клиент: Завершение работы.")


if __name__ == "__main__":
     # Установка зависимостей (если нужно)
    try:
        import cryptography
        # mss не нужен клиенту напрямую, но нужен серверу
    except ImportError:
        print("Пожалуйста, установите необходимые библиотеки:")
        print("pip install cryptography")
        exit()
    main()
