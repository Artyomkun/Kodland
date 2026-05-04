#Импорт
from flask import Flask, render_template,request, redirect
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
#Задаем секретный ключ для работы session
app.secret_key = 'my_top_secret_123'
#Подключение SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diary.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#Создание db
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(40), nullable=False)
    text = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

#Запуск страницы с контентом
@app.route('/')
def index():
    return render_template('index.html')


#Динамичные скиллы
@app.route('/', methods=['POST'])
def process_form():
    button_python = request.form.get('button_python')
    button_discord = request.form.get('button_discord')
    button_html = request.form.get('button_html')
    return render_template('index.html', button_python=button_python, button_discord=button_discord, button_html=button_html)


@app.route('/', methods=['GET','POST'])
def form_create():
    if request.method == 'POST':
        email =  request.form['email']
        text =  request.form['text']

        #Задание №4. Сделай, чтобы создание карточки происходило от имени пользователя
        card = User(email=email, text=text)

        db.session.add(card)
        db.session.commit()
        return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)