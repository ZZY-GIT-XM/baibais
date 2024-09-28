import random
import os


def read_random_entry_from_file(sex=None):
    """从指定文件中随机读取一行，并返回名字和性别"""
    file_path = 'names.txt'
    current_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(current_dir, file_path)

    try:
        with open(full_path, 'r', encoding='utf-8') as file:
            entries = [tuple(line.strip().split(',')) for line in file if sex is None or line.strip().split(',')[1] == sex]

        if not entries:
            raise ValueError("文件为空，无法选取条目。")

        random_entry = random.choice(entries)
        return random_entry[0], random_entry[1]  # 直接返回名字和性别

    except FileNotFoundError:
        raise FileNotFoundError(f"文件 {full_path} 不存在。")

# 使用示例
if __name__ == '__main__':
    try:
        random_name, random_sex = read_random_entry_from_file()
        print(f"随机选取的名字是: {random_name}，性别是: {random_sex}")
    except FileNotFoundError as e:
        print(e)
    except ValueError as e:
        print(e)