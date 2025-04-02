def read_from_file(path):
    with open(path, "r") as f:
        return f.readlines()


print(read_from_file('file.txt'))