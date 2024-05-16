from flask import Flask, render_template,redirect,request,url_for,make_response
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
    return redirect('/create/1')

# STATS GO STR, DEX, INT, WIS, CHA, CON

def get_options(table):
    conn=sqlite3.connect(db)
    cur=conn.cursor()
    cur.execute(f"SELECT Name,{table}_Id FROM {table}")
    options=cur.fetchall()
    return options

@app.route('/create/1')
def create():
    # Render the form template with initial options
    cClass = get_options("Class")
    races = get_options("Race")
    background = get_options("Background")
    return render_template('CharacterCreation1.html', hClass=cClass,raceData=races, backgroundData=background)

@app.route('/create2')
def create2():
    return render_template("CharacterCreation2.html")

@app.route('/submit1', methods=['POST'])
def submit1():
    if request.method == 'POST':
        # Get all options for each attribute
        cClass = request.form.get('cClass')
        name = request.form.get('name')
        race=request.form.get('race')
        background=request.form.get('background')

        resp = make_response(redirect(url_for('create2')))
        resp.set_cookie('cClass', cClass)
        resp.set_cookie('name', name)
        resp.set_cookie('race', race)
        resp.set_cookie('background', background)
        return redirect(url_for('create2'))


@app.route('/character/<id>')
def character_main(id):
    
    conn=sqlite3.connect(db)
    cur=conn.cursor()

    # Check if character exists (ADD KICK FUNCTIONALITY)
    cur.execute('SELECT * FROM Character WHERE Character_Id = ?',(id))
    character_data=cur.fetchone()
    if character_data==None:
        return redirect("/")

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

    return render_template('CharacterMain.html',character=[character_data[1],race[0],classC[0]], skillData = skillBonus,HP = character_data[6])


if __name__ == "__main__":
    app.run(debug=True)