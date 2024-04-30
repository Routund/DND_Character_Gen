from flask import Flask, render_template
import sqlite3

app=Flask(__name__)

@app.route('/')
def home():
    return "home"

@app.route('/character/<id>')
def characterMain(id):
    conn=sqlite3.connect('main.db')
    cur=conn.cursor()
    cur.execute(f'SELECT * FROM Character WHERE Character_Id = {id}')
    characterData=cur.fetchone()
    if characterData==None:
        return "INVALID CHARACTER"
    print(characterData[1])
    return render_template('CharacterMain.html',CharacterData=characterData)


if __name__ == "__main__":
    app.run(debug=True)

