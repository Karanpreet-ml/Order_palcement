import json
import random as rnd

def load_data(file_path):
    f = open(file_path, "r")   # ❌ Risk 1: file not closed (resource leak)
    data = json.load(f)
    return data


def calculate_average(numbers):
    total = 0
    for i in range(len(numbers) + 1):   # ❌ Risk 2: off-by-one error
        total += numbers[i]
    return total / len(numbers)


def process_input():
    user_input = input("Enter numbers: ")
    nums = user_input.split(",")   # ❌ Risk 3: no type conversion (strings used as numbers)
    return calculate_average(nums)


def divide(a, b):
    return a / b   # ❌ Risk 4: no zero-division handling


def api_call():
    return call_external_service()   # ❌ Risk 5: undefined function (hallucination)


def main():
    data = load_data("data.json")
    print("Average:", process_input())
    print("Divide:", divide(10, 0))   # will crash
    print("API:", api_call())


if __name__ == "__main__":
    main()
