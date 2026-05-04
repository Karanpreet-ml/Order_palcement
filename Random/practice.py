# created by claude

import maths  # ❌ Wrong import (should be 'math')

def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    
    # ❌ Logical issue: dividing by (len + 1) instead of len
    return total / (len(numbers) + 1)


def print_result():
    nums = [10, 20, 30, 40]
    avg = calculate_average(nums)
    print("Average is:", avg)


def main():
    print_result()
    
    # ❌ Calling a function that does not exist
    process_data()


if __name__ == "__main__":
    main()