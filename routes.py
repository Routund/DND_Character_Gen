from flask import Flask, render_template
import sqlite3
import math

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

    # Check if character exists (ADD KICK FUNCTIONALITY)
    cur.execute('SELECT * FROM Character WHERE Character_Id = ?',(id))
    character_data=cur.fetchone()
    if character_data==None:
        return "INVALID CHARACTER"

    # Get Race, Class, Proficiencies, Prof Bonus, and Stats. ClassC is just player class, but avoiding class keyword
    cur.execute('SELECT Name FROM Race WHERE Race_Id = ?',(character_data[2]))
    race=cur.fetchone()
    cur.execute('SELECT Name FROM Class WHERE Class_Id = ?',(str(character_data[3])))
    classC=cur.fetchone()
    proficiencies=character_data[9].split(',')
    stats=list(map(int,character_data[8].split(',')))
    cur.execute('SELECT ProfBonus FROM LevelInfo WHERE Level = ? AND Class = ?',(character_data[4],character_data[3]))
    profBonus=cur.fetchone()[0]

    # Calculate ability score for each ability by checking proficiencies list for given ability, then -10 and /2 plus any profs to get score
    i=0
    skillBonus=[]
    while (i<5):
        stat = skills[i]
        for s in stat:
            count=proficiencies.count(s)
            if(count==2):
                skillBonus.append((s,math.floor((stats[i]-10)/2)+2*profBonus))
            elif(count==1):
                skillBonus.append((s,math.floor((stats[i]-10)/2)+profBonus))
            else:
                skillBonus.append((s,math.floor((stats[i]-10)/2)))
        i+=1

    return render_template('CharacterMain.html',character=[character_data[1],race[0],classC[0]], skillData = skillBonus)


if __name__ == "__main__":
    app.run(debug=True)