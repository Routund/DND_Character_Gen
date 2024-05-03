from flask import Flask, render_template
import sqlite3

app=Flask(__name__)
db='main.db'

@app.route('/')
def home():
    return "home"

# STATS GO STR, DEX, WIS, INT, CHA, CON

@app.route('/character/<id>')
def character_main(id):
    conn=sqlite3.connect(db)
    cur=conn.cursor()
    cur.execute(f'SELECT * FROM Character WHERE Character_Id = {id}')
    character_data=cur.fetchone()
    if character_data==None:
        return "INVALID CHARACTER"
    print(character_data[1])
    cur.execute(f'SELECT Name FROM Race WHERE Race_Id = {character_data[2]}')
    race=cur.fetchone()
    cur.execute(f'SELECT Name FROM Class WHERE Class_Id = {character_data[3]}')
    classC=cur.fetchone()
    return render_template('CharacterMain.html',character=[character_data[1],race[0],classC[0]])


if __name__ == "__main__":
    app.run(debug=True)

