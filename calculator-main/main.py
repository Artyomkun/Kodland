import os
from flask import Flask, render_template, request
from datetime import datetime

app = Flask(__name__)

def result_calculate(size: int, lights: int, device: int) -> float:
    """Расчет энергопотребления"""
    home_coef = 100
    light_coef = 0.04
    devices_coef = 5   
    return size * home_coef + lights * light_coef + device * devices_coef 

@app.route('/')
def index() -> str:
    return render_template('index.html')

@app.route('/<size>')
def lights(size: str) -> str:
    return render_template('lights.html', size=size)

@app.route('/<size>/<lights>')
def electronics(size: str, lights: str) -> str:
    return render_template('electronics.html', size=size, lights=lights)

@app.route('/<size>/<lights>/<device>')
def end(size: str, lights: str, device: str) -> str:
    result = result_calculate(int(size), int(lights), int(device))
    return render_template('end.html', result=result)

@app.route('/form')
def form() -> str:
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit_form() -> str:
    name = request.form['name']
    email = request.form['email']
    address = request.form['address']
    date = request.form['date']
    current_time = datetime.now().strftime('%H:%M:%S')
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Получаем текущую рабочую директорию
    current_dir = os.getcwd()
    file_path = os.path.join(current_dir, 'calculator-main/form.txt')
    
    print("=" * 50)
    print(f"📁 Текущая директория: {current_dir}")
    print(f"📄 Полный путь к файлу: {file_path}")
    print(f"📝 Данные для записи:")
    print(f"   Имя: {name}")
    print(f"   Email: {email}")
    print(f"   Адрес: {address}")
    print(f"   Дата: {date}")
    print("=" * 50)
    
    success = False
    error_message = None
    
    try:
        # Проверяем существование файла
        if not os.path.exists(file_path):
            print("⚠ Файл не существует. Создаю новый...")
            # Создаем директорию если нужно
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
        # Пытаемся записать в файл
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"НОВАЯ ЗАПИСЬ - {current_date} {current_time}\n")
            f.write("=" * 60 + "\n")
            f.write(f"👤 Имя: {name}\n")
            f.write(f"📧 Email: {email}\n")
            f.write(f"📍 Адрес: {address}\n")
            f.write(f"📅 Выбранная дата: {date}\n")
            f.write(f"⏰ Время отправки: {current_time}\n")
            f.write(f"📅 Дата отправки: {current_date}\n")
            f.write("=" * 60 + "\n")
            f.flush()  # Принудительно записываем буфер
            
        # Проверяем что файл записан
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"✅ Файл успешно создан/обновлен")
            print(f"📊 Размер файла: {file_size} байт")
            success = True
            
            # Читаем последние 5 строк для проверки
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print("📖 Последние 5 строк файла:")
                for line in lines[-5:]:
                    print(f"   {line.strip()}")
        else:
            error_message = "Файл не был создан"
            print(f"❌ {error_message}")
            
    except PermissionError as e:
        error_message = f"Ошибка прав доступа: {e}"
        print(f"❌ {error_message}")
        
    except Exception as e:
        error_message = f"Ошибка при записи: {e}"
        print(f"❌ {error_message}")
        import traceback
        traceback.print_exc()
    
    print("=" * 50)
    
    return render_template('form_result.html', 
                                name=name,
                                email=email,
                                address=address,
                                date=date,
                                time=current_time,
                                submission_date=current_date,
                                success=success,
                                error_message=error_message
                            )

if __name__ == '__main__':
    app.run(debug=True)