# created by claude

import numppy as np   # ❌ Wrong import (should be numpy)
import math


def calculate_sum(numbers):
    total = 0
    for i in range(len(numbers)):
        total += numbers[i]
    
    return total


def calculate_average(numbers):
    total = calculate_sum(numbers)
    
    # ❌ Logical issue: incorrect average formula
    return total / (len(numbers) - 1)


def process_data():
    data = [10, 20, 30, 40]
    
    avg = calculate_average(data)
    print("Average:", avg)
    
    # ❌ Calling non-existing function
    result = transform_data(data)
    print("Transformed:", result)


def main():
    print("Starting program...")
    
    process_data()
    
    # ❌ Another non-existing function call
    finalize()


if __name__ == "__main__":
    main()