from flask import Flask, render_template,redirect,request,url_for,make_response
import sqlite3
import math

app=Flask(__name__)
db='main.db'


# 2d array of skills, ordered by their stat
skills = [
    ["Athletics"],
    ["Acrobatics","Sleight of hand","Stealth"],
    ["Arcana","History","Investigation","Nature","Religion"],
    ["Animal Handling","Insight","Medicine","Perception","Survival"],
    ["Deception","Intimidation","Performance","Persuasion"]]

# Return creatuib
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

@app.route('/create/2')
def create2():
    # Check if previous form has been filled
    if(request.cookies.get('name')==None):
        return redirect('/create/1')

    ASI = list(map(int,request.cookies.get('ASI').split(',')))
    
    # Compose a message on which stats the player will get
    stat_list = ["Strength","Dexterity","Intelligence","Wisdom","Charisma","Constitution"]
    added = []
    for i in range(6):
        if(ASI[i]>0):
            added.append(f"+{ASI[i]} {stat_list[i]}")
        elif(ASI[i]<0):
            added.append(f"{ASI[i]} {stat_list[i]}")

    # Check if added message is needed
    if(added!=[]):
        added2=', '.join(added)
        return render_template("CharacterCreation2.html",added_message=f"Your race also gives {added2}")
    else:
        return render_template("CharacterCreation2.html",added_message=" ")

@app.route('/create/3')
def create3():
    # Check if previous form has been filled
    if(request.cookies.get('ASI')==None):
        return redirect('/create/2')
    
    conn=sqlite3.connect(db)
    cur=conn.cursor()

    choices_left = request.cookies.get('choices_to_make').split(',')
    if(len(choices_left)!=0):
        current_choice=choices_left[0]

        cur.execute(F'SELECT Profs,MaxAllowed FROM ProfChoice WHERE Choice_Id = {current_choice}')
        data=cur.fetchone()
        maxA=int(data[1])

        return render_template('ChooseProf.html',options=data[0].split(','),max_selections=maxA)
    else:
        return redirect('/create/1')

@app.route('/submit1', methods=['POST'])
def submit1():
    if request.method == 'POST':
        conn=sqlite3.connect(db)
        cur=conn.cursor()


        # Get all options for each attribute
        cClass = request.form.get('cClass')
        name = request.form.get('name')
        race=request.form.get('race')
        background=request.form.get('background')

        ProficiencyList=[]
        cur.execute(F'SELECT ASI,Proficiencies FROM Race WHERE Race_Id = {race}')
        data=cur.fetchone()
        ASI = data[0]
        if(data[1]!=None):
            ProficiencyList = data[1].split(",")

        cur.execute(F'SELECT Proficiencies FROM Background WHERE Background_Id = {background}')
        data=cur.fetchone()
        if(data[0]!=None):
            ProficiencyList += data[0].split(",")

        cur.execute(F'SELECT Proficiencies FROM Class WHERE Class_Id = {cClass}')
        data=cur.fetchone()
        if(data[0]!=None):
            ProficiencyList += data[0].split(",")

        cur.execute(f'Select Choice_Id FROM ProfChoice WHERE Race_Id = {race} OR Class_Id = {cClass}')
        choices = [y[0] for y in cur.fetchall()]

        resp = make_response(redirect(url_for('create2')))
        resp.set_cookie('chosen_options', ','.join([cClass,race,background]))
        resp.set_cookie('name', name)
        resp.set_cookie('ASI',ASI)
        resp.set_cookie('proficiencies', ','.join(set(ProficiencyList)))
        resp.set_cookie('choices_to_make',','.join(list(map(str,choices))))
        return resp
    
@app.route('/submit2', methods=['POST'])
def submit2():
    if request.method == 'POST':
        ASI = request.cookies.get('ASI').split(',')
        for i in range(6):
            stat = request.form.get(f'{i}')
            ASI[i]=str(min(20,int(ASI[i])+int(stat)))
        resp = make_response(redirect(url_for('create3')))
        resp.set_cookie('ASI',','.join(ASI))
        print(ASI)
        return resp

@app.route('/submit3', methods=['POST'])
def submit3():
    if request.method == 'POST':
        profs_chosen = request.form.getlist('proficiencies')
        all_profs = request.cookies.get('proficiencies').split(',')
        resp = make_response(redirect(url_for('create3')))
        resp.set_cookie('proficiencies',','.join(all_profs+profs_chosen))
        resp.set_cookie('choices_to_make',','.join(request.cookies.get('choices_to_make').split(',').pop(0)))
        return resp

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

@app.route('/triangles/<size>')
def triangles(size):
    return render_template('triangles.html',size=int(size),reversed=False)

@app.route('/trianglesr/<size>')
def trianglesR(size):
    return render_template('triangles.html',size=int(size),reversed=True)

@app.route('/trianglesf/<size>')
def trianglesF(size):
    return render_template('triangles.html',size=int(size),flipped=True)

@app.route('/trianglesrf/<size>')
def trianglesRF(size):
    return render_template('triangles.html',size=int(size),reversed=True,flipped=True)

if __name__ == "__main__":
    app.run(debug=True)