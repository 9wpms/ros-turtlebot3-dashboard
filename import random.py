import random

# Generate three random integers between 1 and 3
random_numbers = [random.randint(0, 9) for _ in range(3)]

# Convert integers to string and concatenate them
random_numbers_concatenated = ''.join(map(str, random_numbers))

print("Three random numbers concatenated:", random_numbers_concatenated)
