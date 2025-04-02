from ..functions import read_file


def test_read():
    test_data = ['one\n', 'two three\n', 'four\n', 'five six seven\n']
    assert test_data == read_file.read_from_file('file.txt')