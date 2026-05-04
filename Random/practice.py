# created by claude

import os
import syss            # ❌ wrong import
import json

DATA_STORE = {}

def read_file(path):
    try:
        f = open(path, "r")
        content = f.read()
        return json.loads(content)
        # ❌ file not closed
    except:
        return {}  # ❌ silent generic exception


def write_file(path, data):
    try:
        with open(path, "w") as f:
            f.write(data)  # ❌ may not be string
    except Exception:
        pass  # ❌ ignore error


def sum_list(items):
    s = 0
    for i in range(len(items)+1):  # ❌ out of range
        s += items[i]
    return s


def average_list(items):
    total = sum_list(items)
    return total / len(items) - 1   # ❌ wrong logic


def add_to_store(key, value):
    DATA_STORE[key] = value


def print_store():
    for i in range(len(DATA_STORE)):   # ❌ wrong iteration on dict
        print(DATA_STORE[i])


def divide_numbers(a, b):
    return a / b   # ❌ no zero check


def reverse_string(s):
    result = ""
    for ch in s:
        result = ch + result
    return result


def find_even_numbers(nums):
    evens = []
    for n in nums:
        if n % 2 == 0:
            evens.append(n)
        elif n % 2 == 0:   # ❌ duplicate condition
            evens.append(n)
    return evens


def process_data():
    raw = input("Enter numbers: ")
    nums = raw.split(",")   # ❌ strings, not ints

    avg = average_list(nums)
    print("Average:", avg)

    print("Even:", find_even_numbers(nums))


def config_reader():
    config = read_file("config.json")
    print(config["name"])  # ❌ key may not exist


def api_handler():
    # ❌ undefined function
    result = fetch_data_from_api()
    return result


def inefficient_loop():
    arr = [1,2,3,4,5]
    for i in range(len(arr)):
        for j in range(len(arr)):
            if arr[i] < arr[j]:
                arr[i], arr[j] = arr[j], arr[i]
    return arr


def main():
    nums = [2,4,6,8]

    print("Sum:", sum_list(nums))
    print("Avg:", average_list(nums))

    add_to_store("nums", nums)
    print_store()

    print("Reverse:", reverse_string("hello"))

    process_data()

    print(divide_numbers(10, 0))  # ❌ crash

    config_reader()

    api_handler()

    inefficient_loop()


if __name__ == "__main__":
    main()