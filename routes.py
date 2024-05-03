from flask import Flask, render_template
import sqlite3

app=Flask(__name__)
db='main.db'

@app.route('/')
def home():
    return "home"

@app.route('/character/<id>')
def character_main(id):
    conn=sqlite3.connect(db)
    cur=conn.cursor()
    cur.execute(f'SELECT * FROM Character WHERE Character_Id = {id}')
    character_data=cur.fetchone()
    if character_data==None:
        return "INVALID CHARACTER"
    print(character_data[1])
    return render_template('CharacterMain.html',character=[character_data[1],character_data[0],character_data[10]])


if __name__ == "__main__":
    app.run(debug=True)

