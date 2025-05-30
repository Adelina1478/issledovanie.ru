from flask import Flask, render_template, send_file, redirect, url_for, Response
import subprocess, sqlite3, io, os
from time import time

app = Flask(__name__)

DB_PATH = '/var/www/laboratoria.ru/database.db'

@app.route('/')
def index():
    return render_template('pusto.html', timestamp=int(time()))

@app.route('/pusto')
def pusto():
    return render_template('pusto.html', timestamp=int(time()))

@app.route('/index')
def index_page():
    return render_template('index.html', timestamp=int(time()))

@app.route('/run')
def run_main():
    try:
        result = subprocess.run(
            ['python3', '/var/www/laboratoria.ru/main.py'],
            capture_output=True,
            text=True
        )
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return redirect(url_for('index_page'))
    except Exception as e:
        return f"Ошибка: {str(e)}", 500

@app.route('/runrc')
def run_main1():
    try:
        result = subprocess.run(
            ['python3', '/var/www/laboratoria.ru/main1.py'],
            capture_output=True,
            text=True
        )
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return redirect(url_for('index_page'))
    except Exception as e:
        return f"Ошибка: {str(e)}", 500


@app.route('/clear')
def clear_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM files")
    conn.commit()
    conn.close()
    return redirect(url_for('pusto'))

@app.route('/file/<filename>')
def get_file(filename):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT filetype, content FROM files WHERE filename=?", (filename,))
    row = c.fetchone()
    conn.close()

    if row:
        filetype, content = row
        return Response(content, mimetype=filetype)
    else:
        return "Файл не найден", 404



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

