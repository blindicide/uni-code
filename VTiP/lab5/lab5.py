import time
import base64
import random
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2 # Для генерации ключа из пароля
from Crypto.Random import get_random_bytes # Для генерации соли и IV
from Crypto.Util.Padding import pad, unpad # Для добавления и удаления выравнивания

# --- Параметры шифрования ---
# Размер соли (рекомендуется 16 байт)
SALT_SIZE = 16
# Размер ключа AES (16 байт = AES-128, 24 = AES-192, 32 = AES-256)
KEY_SIZE = 16 # Используем AES-128
# Количество итераций для PBKDF2 (чем больше, тем безопаснее, но медленнее)
# Для демонстрации можно взять меньше, для реальных задач - 100,000 и больше
ITERATIONS = 10000 # Уменьшено для ускорения демонстрации брутфорса
# Размер блока AES (всегда 16 байт)
BLOCK_SIZE = AES.block_size

# --- Функция для шифрования текста ---
def encrypt_text(plaintext, password):
    """
    Шифрует переданный текст с использованием AES-CBC.
    Генерирует ключ из пароля с помощью PBKDF2.
    Возвращает зашифрованные данные (соль + IV + шифротекст).
    """
    try:
        # 1. Генерируем случайную соль
        salt = get_random_bytes(SALT_SIZE)
        print(f"[Шифрование] Сгенерирована соль: {salt.hex()}")

        # 2. Генерируем ключ шифрования из пароля и соли с помощью PBKDF2
        # Это стандартный и безопасный способ получения ключа фиксированной длины из пароля
        key = PBKDF2(password.encode('utf-8'), salt, dkLen=KEY_SIZE, count=ITERATIONS)
        print(f"[Шифрование] Сгенерирован ключ (первые 8 байт): {key[:8].hex()}...")

        # 3. Подготавливаем данные: кодируем в байты и добавляем выравнивание (padding)
        # AES работает с блоками фиксированного размера (16 байт)
        plaintext_bytes = plaintext.encode('utf-8')
        padded_data = pad(plaintext_bytes, BLOCK_SIZE)

        # 4. Генерируем случайный вектор инициализации (IV)
        # IV нужен для режима CBC, делает шифротекст разным даже при одинаковом тексте и ключе
        iv = get_random_bytes(BLOCK_SIZE)
        print(f"[Шифрование] Сгенерирован IV: {iv.hex()}")

        # 5. Создаем объект шифра AES в режиме CBC
        cipher = AES.new(key, AES.MODE_CBC, iv)

        # 6. Шифруем данные
        ciphertext = cipher.encrypt(padded_data)
        print(f"[Шифрование] Данные успешно зашифрованы.")

        # 7. Сохраняем соль и IV вместе с шифротекстом
        # Стандартная практика - сохранить их в начале зашифрованных данных
        # Формат: salt (16 байт) + iv (16 байт) + ciphertext
        encrypted_data = salt + iv + ciphertext
        print(f"[Шифрование] Общий размер зашифрованных данных: {len(encrypted_data)} байт")

        return encrypted_data

    except Exception as e:
        print(f"[Шифрование] Ошибка при шифровании: {e}")
        return None

# --- Функция для попытки дешифрования ---
def try_decrypt(encrypted_data, password_candidate):
    """
    Пытается расшифровать данные с использованием предполагаемого пароля.
    Возвращает расшифрованный текст в случае успеха, иначе None.
    Успех определяется по корректности снятия выравнивания (unpad).
    """
    try:
        # 1. Извлекаем соль, IV и шифротекст из полученных данных
        salt = encrypted_data[:SALT_SIZE]
        iv = encrypted_data[SALT_SIZE:SALT_SIZE + BLOCK_SIZE]
        ciphertext = encrypted_data[SALT_SIZE + BLOCK_SIZE:]

        # 2. Генерируем ключ из предполагаемого пароля и извлеченной соли
        # Используем те же параметры PBKDF2, что и при шифровании
        key = PBKDF2(password_candidate.encode('utf-8'), salt, dkLen=KEY_SIZE, count=ITERATIONS)

        # 3. Создаем объект шифра AES
        cipher = AES.new(key, AES.MODE_CBC, iv)

        # 4. Пытаемся расшифровать данные
        decrypted_padded_data = cipher.decrypt(ciphertext)

        # 5. Пытаемся убрать выравнивание (padding)
        # Если ключ был неверным, данные будут "мусором", и unpad вызовет ValueError
        original_data_bytes = unpad(decrypted_padded_data, BLOCK_SIZE)

        # 6. Если unpad прошел успешно, декодируем байты в строку
        original_plaintext = original_data_bytes.decode('utf-8')
        return original_plaintext # Успех! Ключ (пароль) верный.

    except ValueError:
        # Ошибка ValueError при unpad - самый частый индикатор неверного ключа
        return None # Пароль не подошел
    except Exception as e:
        # Ловим другие возможные ошибки (хотя в контексте брутфорса они редки)
        # print(f"[Дешифрование] Ошибка с паролем '{password_candidate}': {e}") # Можно раскомментировать для отладки
        return None # Пароль не подошел

# --- Функция атаки грубой силой ---
def brute_force_attack(encrypted_data):
    """
    Перебирает все трехзначные числа (000-999) в качестве пароля.
    """
    print("\n--- Начало атаки грубой силой (пароль = 3-значное число) ---")
    start_time = time.time()

    # Перебираем все числа от 0 до 999
    for i in range(1000):
        # Форматируем число в строку из 3 цифр (с ведущими нулями: "000", "001", ..., "042", ..., "999")
        password_candidate = f"{i:03d}"

        # Выводим прогресс каждые 50 попыток для наглядности
        if i % 50 == 0:
            print(f"Пробуем пароль: {password_candidate} ...")

        # Пытаемся расшифровать с текущим кандидатом
        decrypted_text = try_decrypt(encrypted_data, password_candidate)

        # Проверяем результат
        if decrypted_text is not None:
            # Если try_decrypt вернул не None, значит пароль найден!
            end_time = time.time()
            print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(f"УСПЕХ! Пароль найден!")
            print(f"Найденный пароль: {password_candidate}")
            print(f"Расшифрованный текст: {decrypted_text}")
            print(f"Время выполнения атаки: {end_time - start_time:.2f} секунд")
            print(f"Количество перебранных паролей: {i + 1}")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            return password_candidate, decrypted_text

    # Если цикл завершился, а пароль не найден
    end_time = time.time()
    print("\n--- Атака завершена ---")
    print("Пароль не найден в диапазоне 000-999.")
    print(f"Время выполнения атаки: {end_time - start_time:.2f} секунд")
    return None, None

# --- Основной блок программы ---
if __name__ == "__main__":
    # 1. Определяем исходный текст и "секретный" пароль (трехзначное число)
    # Можете изменить пароль на любое другое трехзначное число
    plaintext_to_encrypt = input("Введите текст для шифрования: ")
    actual_password = str(random.randint(1,1000)) # Наш "секретный" пароль (должен быть строкой)

    print(f"Исходный текст: \"{plaintext_to_encrypt}\"")
    print(f"Пароль для шифрования: \"{actual_password}\"")

    # Проверка, что пароль действительно трехзначное число
    if not (actual_password.isdigit() and len(actual_password) == 3):
        print("\nПРЕДУПРЕЖДЕНИЕ: Заданный пароль не является трехзначным числом!")
        print("Атака будет искать пароль в диапазоне 000-999 и может не найти ваш пароль.")
        # Вы можете прервать выполнение или продолжить с предупреждением
        # import sys
        # sys.exit("Исправьте пароль и запустите снова.")

    print("\n--- Шаг 1: Шифрование текста ---")
    # 2. Шифруем текст с использованием выбранного пароля
    encrypted_data_blob = encrypt_text(plaintext_to_encrypt, actual_password)

    if encrypted_data_blob:
        # Выводим зашифрованные данные в формате Base64 (удобно для копирования/передачи)
        encrypted_base64 = base64.b64encode(encrypted_data_blob).decode('utf-8')
        print(f"\nЗашифрованные данные (Base64):\n{encrypted_base64}")
        print(f"(Длина исходных байт: {len(encrypted_data_blob)})")

        # 3. Запускаем атаку грубой силой на полученные зашифрованные данные
        print("\n--- Шаг 2: Атака грубой силой ---")
        brute_force_attack(encrypted_data_blob)
    else:
        print("\nНе удалось зашифровать текст. Атака невозможна.")