from flask import Flask, render_template, request, send_from_directory

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        selected_image = request.form.get('image-selector')

        text_top = request.form.get('textTop')
        text_bottom = request.form.get('textBottom')
        

        text_top_y = request.form.get('text_top_y')
        text_bottom_y = request.form.get('text_bottom_y')
        selected_color = request.form.get('selected_color')

        if not selected_color:
            selected_color = 'white'
        if text_top_y and not text_top_y.endswith('px'):
            text_top_y += 'px'
        if text_bottom_y and not text_bottom_y.endswith('px'):
            text_bottom_y += 'px'
        if not text_top_y:
            text_top_y = '20%'
        if not text_bottom_y:
            text_bottom_y = '20%'

        return render_template('index.html', 
                                selected_image=selected_image, 

                                text_top = text_top,
                                text_bottom = text_bottom,
                                text_top_y = text_top_y,
                                text_bottom_y = text_bottom_y,
                                selected_color = selected_color
                              )
    else:
        return render_template('index.html', selected_image='logo.svg')


@app.route('/static/img/<path:path>')
def serve_images(path: str):
    return send_from_directory('static/img', path)

app.run(debug=True)
