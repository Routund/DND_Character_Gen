from flask import Flask, render_template
import sqlite3

app=Flask(__name__)
db='main.db'

skills = [
    ["Athletics"],
    ["Acrobatics","Sleight of hand","Stealth"],
    ["Arcana","History","Investigation","Nature","Religion"],
    ["Animal Handling","Insight","Medicine","Perception","Survival"],
    ["Deception","Intimidation","Performance","Persuasion"]]

@app.route('/')
def home():
    return "home"

# STATS GO STR, DEX, INT, WIS, CHA, CON

@app.route('/character/<id>')
def character_main(id):
    conn=sqlite3.connect(db)
    cur=conn.cursor()
    cur.execute(f'SELECT * FROM Character WHERE Character_Id = {id}')
    character_data=cur.fetchone()
    if character_data==None:
        return "INVALID CHARACTER"
    cur.execute(f'SELECT Name FROM Race WHERE Race_Id = {character_data[2]}')
    race=cur.fetchone()
    cur.execute(f'SELECT Name FROM Class WHERE Class_Id = {character_data[3]}')
    classC=cur.fetchone()
    proficiencies=character_data[9].split(',')
    stats=character_data[8].split(',')

    i=0
    skillBonus=[]
    while (i<5):
        for skill in skills:
            print("TO DO")

    return render_template('CharacterMain.html',character=[character_data[1],race[0],classC[0]])


if __name__ == "__main__":
    app.run(debug=True)

