import os
import sys
from tkinter import Tk, filedialog

# Проверка установки Pillow, вывод инструкций при отсутствии
try:
    from PIL import Image, ImageFilter
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
        title="Выберите изображение для размытия",
        filetypes=[("Файлы изображений", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff"), ("Все файлы", "*.*")]
    )
    root.destroy() # Закрыть скрытое окно tkinter
    return file_path

def apply_blur(image_path):
    """Применяет выбранный тип размытия и радиус к изображению."""
    if not image_path:
        print("Файл не выбран.")
        return

    try:
        img = Image.open(image_path)
        img = img.convert("RGB") # Убедиться, что изображение в формате RGB

        # --- Выбор типа размытия ---
        blur_filter = None
        blur_name = ""
        while True:
            print("\nВыберите тип размытия:")
            print("1. Простое размытие (Box Blur)")
            print("2. Гауссово размытие (Gaussian Blur)")
            print("0. Отмена")
            choice = input("Ваш выбор: ").strip()

            if choice == '1':
                blur_filter = ImageFilter.BoxBlur
                blur_name = "box_blur"
                break
            elif choice == '2':
                blur_filter = ImageFilter.GaussianBlur
                blur_name = "gaussian_blur"
                break
            elif choice == '0':
                print("Операция отменена.")
                return
            else:
                print("Неверный выбор. Попробуйте снова.")

        # --- Выбор степени размытия ---
        radius = 0
        while True:
            try:
                radius_str = input(f"Введите степень размытия (целое число > 0, например, 2, 5, 10): ").strip()
                radius = int(radius_str)
                if radius > 0:
                    break
                else:
                    print("Степень размытия должна быть больше нуля.")
            except ValueError:
                print("Неверный ввод. Пожалуйста, введите целое число.")

        # --- Применение фильтра ---
        print(f"Применение {blur_name} с радиусом {radius}...")
        # BoxBlur принимает один аргумент radius
        # GaussianBlur может принимать один (radius) или два аргумента (x, y radii)
        if blur_filter == ImageFilter.BoxBlur:
             blurred_img = img.filter(blur_filter(radius))
        elif blur_filter == ImageFilter.GaussianBlur:
             blurred_img = img.filter(blur_filter(radius=radius))
        else:
             print("Неизвестный фильтр. Ошибка.") # Не должно произойти
             return


        # --- Сохранение результата ---
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        dir_name = os.path.dirname(image_path)
        output_filename = os.path.join(dir_name, f"{base_name}_{blur_name}_r{radius}.png")

        blurred_img.save(output_filename)
        print(f"\nРазмытое изображение успешно сохранено как: {output_filename}")

    except FileNotFoundError:
        print(f"Ошибка: Файл не найден по пути {image_path}")
    except Exception as e:
        print(f"Произошла ошибка при обработке изображения: {e}")

if __name__ == "__main__":
    image_file = select_image_file()
    apply_blur(image_file)
