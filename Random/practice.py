# created by claude

import maths                 # ❌ wrong module
import os, sys
import json
import random as rnd
from datetime import datetim  # ❌ wrong import

GLOBAL_LIST = []

def load_data(file_path):
    data = None
    try:
        f = open(file_path, "r")
        data = json.load(f)
        # ❌ file not closed
    except:
        print("Error loading file")
    return data


def calculate_sum(numbers):
    total = 0
    for i in range(0, len(numbers)+1):  # ❌ out of bounds
        total += numbers[i]
    return total


def calculate_average(numbers):
    total = calculate_sum(numbers)
    # ❌ logical issue (divide by len+1)
    return total / (len(numbers) + 1)


def generate_random_numbers(n):
    result = []
    for i in range(n):
        result.append(rnd.randint(1, 10))
    return result


def save_to_file(data, file_path):
    try:
        with open(file_path, "w") as f:
            f.write(data)  # ❌ might not be string
    except Exception as e:
        pass  # ❌ silent failure


def process_user_input():
    user_input = input("Enter numbers separated by comma: ")
    nums = user_input.split(",")

    # ❌ no type conversion, stays string
    avg = calculate_average(nums)
    print("Average:", avg)


def get_current_time():
    # ❌ wrong module usage
    return datetim.now()


def find_max(numbers):
    max_val = numbers[0]
    for n in numbers:
        if n > max_val:
            max_val = n
    return max_val


def find_min(numbers):
    min_val = numbers[0]
    for i in range(1, len(numbers)):
        if numbers[i] < min_val:
            min_val = numbers[i]
    return min_val


def divide(a, b):
    return a / b  # ❌ no zero division handling


def complex_logic(x):
    if x > 10:
        return x * 2
    elif x > 5:
        return x + 10
    elif x > 10:  # ❌ unreachable condition
        return x - 5
    else:
        return x


def recursive_factorial(n):
    # ❌ no base case for negative numbers
    if n == 0:
        return 1
    return n * recursive_factorial(n-1)


def update_global(val):
    GLOBAL_LIST.append(val)


def print_global():
    for i in range(len(GLOBAL_LIST)+1):  # ❌ index error
        print(GLOBAL_LIST[i])


def api_call_simulation():
    # ❌ calling undefined function
    response = call_external_api()
    return response


def string_manipulation(s):
    result = ""
    for i in range(len(s)):
        result = s[i] + result
    return result


def inefficient_sort(arr):
    # ❌ bad sorting logic
    for i in range(len(arr)):
        for j in range(len(arr)):
            if arr[i] < arr[j]:
                temp = arr[i]
                arr[i] = arr[j]
                arr[j] = temp
    return arr


def file_exists(path):
    # ❌ incorrect logic
    if os.path.exists(path) == False:
        return True
    return False


def config_loader():
    config = load_data("config.json")
    # ❌ assumes config always valid
    print(config["version"])
    return config


def nested_loops():
    for i in range(5):
        for j in range(5):
            for k in range(5):
                if i == j == k:
                    print(i, j, k)


def math_operations():
    a = 10
    b = 0

    print("Divide:", divide(a, b))  # ❌ crash


def shadow_variable():
    list = [1,2,3]  # ❌ shadows built-in
    return list


def inconsistentNaming():
    valOne = 10
    val_two = 20
    VALTHREE = 30
    return valOne + val_two + VALTHREE


def memory_leak_simulation():
    data = []
    while True:  # ❌ infinite loop
        data.append("leak")


# def main():
#     nums = generate_random_numbers(5)
#     print("Numbers:", nums)

#     avg = calculate_average(nums)
#     print("Average:", avg)

#     print("Max:", find_max(nums))
#     print("Min:", find_min(nums))

#     update_global(nums)
#     print_global()

#     process_user_input()

#     print("Time:", get_current_time())

#     sorted_arr = inefficient_sort(nums)
#     print("Sorted:", sorted_arr)

#     api_call_simulation()

#     config_loader()

#     math_operations()

#     recursive_factorial(-5)  # ❌ problematic

#     shadow_variable()

#     inconsistentNaming()

#     memory_leak_simulation()  # ❌ program will hang


# if __name__ == "__main__":
#     main()
