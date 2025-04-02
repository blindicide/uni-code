import os
import argparse

def find_by_size(directory, size, recursive=False, greater=False, less=False, sort=False):
    files_found = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            
            if greater and file_size > size:
                files_found.append((file_path, file_size))
            elif less and file_size < size:
                files_found.append((file_path, file_size))
            elif not greater and not less and file_size == size:
                files_found.append((file_path, file_size))
        
        if not recursive:
            break
    
    if sort:
        files_found.sort(key=lambda x: x[1])
    
    return files_found

def main():
    parser = argparse.ArgumentParser(description="Поиск файлов по размеру")
    parser.add_argument("size", type=int, help="Размер файла в байтах")
    parser.add_argument("directory", type=str, help="Путь до директории")
    parser.add_argument("-r", "--recursive", action="store_true", help="Рекурсивный поиск")
    parser.add_argument("-g", "--greater", action="store_true", help="Искать файлы с большим размером")
    parser.add_argument("-l", "--less", action="store_true", help="Искать файлы с меньшим размером")
    parser.add_argument("-s", "--sort", action="store_true", help="Сортировать файлы по размеру")
    
    args = parser.parse_args()
    
    files = find_by_size(args.directory, args.size, args.recursive, args.greater, args.less, args.sort)
    
    for file_path, file_size in files:
        print(f"Файл: {file_path}, Размер: {file_size} байт")

if __name__ == "__main__":
    main()
