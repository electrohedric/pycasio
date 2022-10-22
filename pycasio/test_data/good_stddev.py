
from pycasio import casio


numbers = []
NUM = 3

for i in range(NUM):
    userin = casio.input.number_input(f"Number {i}")
    numbers.append(userin)

sq_diff_sum = 0
mean = sum(numbers) / NUM
for num in numbers:
    sq_diff_sum += (num - mean) ** 2
sigma = (sq_diff_sum / NUM) ** 0.5
print(sigma)
