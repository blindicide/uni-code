import csv
import argparse
from collections import defaultdict
import chardet

def create_password_dict(csv_file, sort_desc=False, sort_asc=False):
    password_count = defaultdict(int)
    with open(csv_file, 'rb') as f:
        result = chardet.detect(f.read())
        print(result)
    with open(csv_file, mode='r', encoding=result) as file:
        reader = csv.reader(file)
        for row in reader:
            password = row[0]  # Предполагаем, что пароль находится в первой колонке
            password_count[password] += 1
    
    if sort_desc:
        return dict(sorted(password_count.items(), key=lambda item: item[1], reverse=True))
    elif sort_asc:
        return dict(sorted(password_count.items(), key=lambda item: item[1]))
    
    return password_count

def main():
    parser = argparse.ArgumentParser(description="Создание словаря паролей из CSV")
    parser.add_argument("csv_file", type=str, help="Путь до CSV файла")
    parser.add_argument("-l", "--sort_desc", action="store_true", help="Сортировать по убыванию вхождений")
    parser.add_argument("-s", "--sort_asc", action="store_true", help="Сортировать по возрастанию вхождений")
    
    args = parser.parse_args()
    
    password_dict = create_password_dict(args.csv_file, args.sort_desc, args.sort_asc)
    
    for password, count in password_dict.items():
        print(f"Пароль: {password}, Вхождений: {count}")

if __name__ == "__main__":
    main()
