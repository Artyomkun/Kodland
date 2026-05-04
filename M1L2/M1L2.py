import random

characters = "+-/*!&$#?=@abcdefghijklnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"

password_length = int(input("Введите длину пароля: "))

generated_password = ""

for i in range(password_length):
    generated_password += random.choice(characters)

print("Сгенерированный пароль:", generated_password)

for i in range(1, 6): print('*' * i)

name = input("Введите имя: ")
print('*' * (len(name) + 2))
print('*' + name + '*')
print('*' * (len(name) + 2))

n = int(input("Введите число n: "))
sum_numbers = sum(range(1, n + 1))
print(f"Сумма всех чисел от 1 до {n}: {sum_numbers}")

n = int(input("Введите число n: "))
sum_numbers = 0
for i in range(1, n + 1):
    sum_numbers += i
print(f"Сумма всех чисел от 1 до {n}: {sum_numbers}")


secret_number = random.randint(1, 20)
attempts = 5

print("Я загадал число от 1 до 20. У тебя 5 попыток!")

for attempt in range(1, attempts + 1):
    guess = int(input(f"Попытка {attempt}. Введи число: "))
    
    if guess == secret_number:
        print("Поздравляю! Ты угадал!")
        break
    elif guess < secret_number:
        print("Загаданное число БОЛЬШЕ")
    else:
        print("Загаданное число МЕНЬШЕ")
    
    if attempt == attempts:
        print(f"Попытки закончились! Я загадал число {secret_number}")