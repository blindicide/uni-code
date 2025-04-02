import os
import sys
from tkinter import Tk, filedialog

# Проверка установки Pillow, вывод инструкций при отсутствии
try:
    from PIL import Image
except ImportError:
    print("Ошибка: Модуль 'Pillow' (PIL fork) не найден.")
    print("Пожалуйста, установите его, выполнив команду:")
    print("pip install Pillow")
    sys.exit(1) # Выход, если необходимая библиотека отсутствует

def select_image_file():
    """Открывает диалог для выбора файла изображения."""
    root = Tk()
    root.withdraw() # Скрыть главное окно tkinter
    root.attributes('-topmost', True) # Поместить диалог поверх других окон
    file_path = filedialog.askopenfilename(
        title="Выберите изображение",
        filetypes=[("Файлы изображений", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff"), ("Все файлы", "*.*")]
    )
    root.destroy() # Закрыть скрытое окно tkinter
    return file_path

def separate_channels(image_path):
    """Разделяет каналы R, G, B изображения и сохраняет их."""
    if not image_path:
        print("Файл не выбран.")
        return

    try:
        img = Image.open(image_path)
        img = img.convert("RGB") # Убедиться, что изображение в формате RGB
        r, g, b = img.split()

        base_name = os.path.splitext(os.path.basename(image_path))[0]
        dir_name = os.path.dirname(image_path)

        channels_to_save = {}
        while True:
            print("\nВыберите каналы для сохранения (можно несколько через пробел):")
            print("1. Красный (R)")
            print("2. Зеленый (G)")
            print("3. Синий (B)")
            print("0. Готово (или отмена, если ничего не выбрано)")
            choice = input("Ваш выбор: ").strip().lower().split()

            if '0' in choice:
                break

            valid_choice = False
            if '1' in choice or 'r' in choice or 'к' in choice:
                channels_to_save['red'] = r
                valid_choice = True
            if '2' in choice or 'g' in choice or 'з' in choice:
                channels_to_save['green'] = g
                valid_choice = True
            if '3' in choice or 'b' in choice or 'с' in choice:
                channels_to_save['blue'] = b
                valid_choice = True

            if not valid_choice and choice:
                print("Неверный выбор. Попробуйте снова.")
            elif valid_choice:
                print(f"Выбраны каналы: {', '.join(channels_to_save.keys())}")
                break # Выход из цикла после валидного выбора

        if not channels_to_save:
            print("Каналы не выбраны для сохранения.")
            return

        saved_files = []
        for name, channel_img in channels_to_save.items():
            # Создаем новое изображение, где виден только выбранный канал
            # Для отображения одного канала часто создают изображение в оттенках серого
            # или помещают данные канала во все три слота R,G,B для цветного представления
            # Здесь мы сохраняем представление канала в оттенках серого
            output_filename = os.path.join(dir_name, f"{base_name}_{name}.png")
            channel_img.save(output_filename)
            saved_files.append(output_filename)

        if saved_files:
            print("\nКаналы успешно сохранены:")
            for f in saved_files:
                print(f"- {f}")
        else:
            print("Не удалось сохранить каналы.")

    except FileNotFoundError:
        print(f"Ошибка: Файл не найден по пути {image_path}")
    except Exception as e:
        print(f"Произошла ошибка при обработке изображения: {e}")

if __name__ == "__main__":
    image_file = select_image_file()
    separate_channels(image_file)
