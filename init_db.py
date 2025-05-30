import sqlite3

conn = sqlite3.connect('/var/www/laboratoria.ru/database.db')
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS files (
    filename TEXT PRIMARY KEY,
    filetype TEXT,
    content BLOB
)
''')


c.execute('''
INSERT INTO files (filename, filetype, content)
VALUES (?, ?, ?)
''', ('test.txt', 'text/plain', b'Hello, world!'))

conn.commit()
conn.close()

print("Inserted test record.")
