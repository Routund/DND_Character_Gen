from flask import Flask, render_template, redirect, jsonify
from flask import request, url_for, make_response
import sqlite3
import math

app = Flask(__name__)
db = 'main.db'


# 2d array of skills, ordered by their stat
skills = [
    ["Athletics"],
    ["Acrobatics", "Sleight of hand", "Stealth"],
    ["Arcana", "History", "Investigation", "Nature", "Religion"],
    ["Animal Handling", "Insight", "Medicine", "Perception", "Survival"],
    ["Deception", "Intimidation", "Performance", "Persuasion"],
    []]

stat_names = ["Strength","Dexterity","Intelligence","Wisdom","Charisma","Constitution"]
# Return creatuib
@app.route('/')
def home():
    return redirect('/create/1')


def get_options(table):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(f"SELECT Name,{table}_Id FROM {table}")
    options = cur.fetchall()
    return options


# Cookie Setter
def setCookies(resp, keys, values):
    for i in range(len(keys)):
        resp.set_cookie(keys[i], values[i])


@app.route('/create/1')
def create():
    # Render the form template with initial options
    cClass = get_options("Class")
    races = get_options("Race")
    background = get_options("Background")
    return render_template('CharacterCreation1.html', hClass=cClass, raceData=races, backgroundData=background)


@app.route('/create/2')
def create2():
    # Check if previous form has been filled
    if (request.cookies.get('name') is None):
        return redirect('/create/1')

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Get the choices left to make for the character, then check if the user has any more choices to make
    choices_left = request.cookies.get('choices_to_make').split(',')
    if (choices_left[0] != ''):
        current_choice = choices_left[0]
        cur.execute(F'SELECT Profs,MaxAllowed FROM ProfChoice WHERE Choice_Id = {current_choice}')
        data = cur.fetchone()
        maxA = int(data[1])

        return render_template('ChooseProf.html', options=data[0].split(','), max_selections=maxA)
    else:
        return redirect('/create/3')


@app.route('/create/3')
def create3():
    # Check if previous form has been filled
    if (request.cookies.get('name') is None):
        return redirect('/create/1')

    ASI = list(map(int, request.cookies.get('ASI').split(',')))

    # Compose a message on which stats the player will get
    stat_list = ["Strength", "Dexterity", "Intelligence", "Wisdom", "Charisma", "Constitution"]
    added = []
    for i in range(6):
        if (ASI[i] > 0):
            added.append(f"+{ASI[i]} {stat_list[i]}")
        elif (ASI[i] < 0):
            added.append(f"{ASI[i]} {stat_list[i]}")

    # Check if added message is needed
    if (added != []):
        added2 = ', '.join(added)
        return render_template("CharacterCreation2.html", added_message=f"Your race also gives {added2}")
    else:
        return render_template("CharacterCreation2.html", added_message=" ")


@app.route('/submit1', methods=['POST'])
def submit1():
    if request.method == 'POST':
        conn = sqlite3.connect(db)
        cur = conn.cursor()

        # Get all options for each attribute
        cClass = request.form.get('cClass')
        name = request.form.get('name')
        race = request.form.get('race')
        background = request.form.get('background')

        ProficiencyList = []
        cur.execute(F'SELECT ASI,Proficiencies FROM Race WHERE Race_Id = {race}')
        data = cur.fetchone()
        ASI = data[0]
        if (data[1] is not None):
            ProficiencyList = data[1].split(",")

        cur.execute(F'SELECT Proficiencies FROM Background WHERE Background_Id = {background}')
        data = cur.fetchone()
        if (data[0] is not None):
            ProficiencyList += data[0].split(",")

        cur.execute(F'SELECT Proficiencies FROM Class WHERE Class_Id = {cClass}')
        data = cur.fetchone()
        if (data[0] is not None):
            ProficiencyList += data[0].split(",")

        cur.execute(f'Select Choice_Id FROM ProfChoice WHERE Race_Id = {race} OR Class_Id = {cClass}')
        choices = [y[0] for y in cur.fetchall()]

        resp = make_response(redirect(url_for('create2')))
        setCookies(resp, ['chosen_options', 'name', 'ASI', 'proficiencies', 'choices_to_make'], [','.join([cClass, race, background]), name, ASI, ','.join(set(ProficiencyList)), ','.join(list(map(str, choices)))])
        return resp


@app.route('/submit2', methods=['POST'])
def submit2():
    if request.method == 'POST':
        profs_chosen = request.form.getlist('choices')
        all_profs = request.cookies.get('proficiencies').split(',')
        resp = make_response(redirect(url_for('create2')))
        cookies_to_set = request.cookies.get('choices_to_make').split(',')
        cookies_to_set.pop(0)
        setCookies(resp, ['proficiencies', 'choices_to_make'], [','.join(all_profs + profs_chosen), ','.join(cookies_to_set)])
        return resp


@app.route('/submit3', methods=['POST'])
def submit3():
    if request.method == 'POST':
        # Calculate total ability scores for each stat based off race ASI and form results
        ASI = request.cookies.get('ASI').split(',')
        for i in range(6):
            stat = request.form.get(f'{i}')
            ASI[i] = str(min(20, int(ASI[i])+int(stat)))
        resp = make_response(redirect(url_for('insert')))
        setCookies(resp, ['ASI'], [','.join(ASI)])
        return resp


@app.route('/insert', methods=['GET', 'POST'])
def insert():
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Get all values that need to be inserted
    name = request.cookies.get('name')
    cClass, race, background = request.cookies.get('chosen_options').split(',')
    stats = request.cookies.get('ASI')
    statsSplit = stats.split(',')
    cur.execute(f'SELECT HpDie FROM Class WHERE Class_Id = {cClass}')
    hp = int(cur.fetchone()[0].split('d')[1])+(int(statsSplit[5])-10)//2
    ac=10+(int(statsSplit[1])-10)//2
    proficiencies = request.cookies.get('proficiencies')

    cur.execute('INSERT INTO Character (Name,Race,Class,Level,Background,HP,AC,Stats,Proficiencies,Current_HP) VALUES (?,?,?,?,?,?,?,?,?,?)',(name,race,cClass,1,background,hp,ac,stats,proficiencies,hp))
    conn.commit()
    return redirect(f'/character/{cur.lastrowid}')


@app.route('/character/<id>')
def character_main(id):

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Check if character exists (ADD KICK FUNCTIONALITY)
    cur.execute('SELECT * FROM Character WHERE Character_Id = ?', (id,))
    character_data = cur.fetchone()
    if character_data is None:
        return redirect("/")

    # Get Race, Class, Proficiencies, Prof Bonus, and Stats. classC is just player class, but avoiding python class keyword
    cur.execute('SELECT Name FROM Race WHERE Race_Id = ?', (character_data[2],))
    race = cur.fetchone()
    cur.execute(f'SELECT Name FROM Class WHERE Class_Id = ?', (character_data[3],))
    classC = cur.fetchone()
    proficiencies = character_data[9].split(',')
    stats = list(map(int, character_data[8].split(',')))
    prof_bonus = ((character_data[4]-1)//4)+2

    # Calculate ability score for each ability by checking proficiencies list for given ability, then -10 and /2 plus any profs to get score
    # Also calculate each stat modifier in the same loop
    i = 0
    skillBonus = []
    stat_data = []
    
    while (i < 6):
        stat_abilities = skills[i]
        mod=math.floor((stats[i]-10)//2)
    
        if(proficiencies.count(stat_names[i])!=0):
            stat_data.append([stat_names[i],mod,mod+prof_bonus])
        else:
            stat_data.append([stat_names[i],mod,mod])

        for ability in stat_abilities:
            count = proficiencies.count(ability)
            if (count == 2):
                skillBonus.append((ability, mod+2*prof_bonus))
            elif (count == 1):
                skillBonus.append((ability, mod+prof_bonus))
            else:
                skillBonus.append((ability, mod))
        i += 1

    values_to_list = [character_data[1], race[0], classC[0]]
    other_values = [id,character_data[6],character_data[12],character_data[7],prof_bonus]
    return render_template('CharacterMain.html', character=values_to_list, skillData=skillBonus, other_values=other_values,statData=stat_data)


@app.route('/character_abilities/<id>')
def character_abilities(id):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    # Check if character exists (ADD KICK FUNCTIONALITY)
    cur.execute('SELECT * FROM Character WHERE Character_Id = ?', (id,))
    character_data = cur.fetchone()
    if character_data is None:
        return redirect("/")

    # Get all abilities (feats) by their type, race, class or background, and add them to a list for insertion into html
    feat_names = []
    feat_descriptions = []
    feat_types = ["Race","Class","Background"]
    feat_types_parameters = [character_data[2],character_data[3],character_data[5]]
    for i in range(3):
        cur.execute(f'SELECT Name,Description FROM Ability WHERE Ability_Id IN (SELECT Ability_Id FROM Ability{feat_types[i]} WHERE {feat_types[i]}_Id = ?)', (feat_types_parameters[i],))
        data = cur.fetchall()

        # List comprehension from Stack Overflow
        feat_names.append([i[0] for i in data])
        feat_descriptions.append([i[1] for i in data]) 

    other_values = [id,character_data[6],character_data[12],character_data[7],((character_data[4]-1)//4)+2]
    return render_template('CharacterAbility.html',other_values=other_values,names=feat_names,descs=feat_descriptions)


@app.route('/updateHP', methods=['POST'])
def updateHP():
    data = request.get_json()
    HP = data.get('HP')
    AC = data.get('AC')
    id = data.get('id')

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    cur.execute(f"UPDATE Character SET Current_HP = '{HP}', AC = {AC} WHERE Character_Id = {id}")
    conn.commit()
    return jsonify({'status': 'success', 'received_value': AC})


@app.route('/triangles/<size>')
def triangles(size):
    return render_template('triangles.html', size=int(size), reversed=False)


@app.route('/trianglesr/<size>')
def trianglesR(size):
    return render_template('triangles.html', size=int(size), reversed=True)


@app.route('/trianglesf/<size>')
def trianglesF(size):
    return render_template('triangles.html', size=int(size), flipped=True)


@app.route('/trianglesrf/<size>')
def trianglesRF(size):
    return render_template('triangles.html', size=int(size), reversed=True, flipped=True)


if __name__ == "__main__":
    app.run(debug=True)


# Unfnished Table querying code
def getFromTable(table, toGet, Parameter):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    toGetString = ','.join(toGet)
    cur.execute(f'SELECT {toGetString} FROM LevelInfo WHERE Level = ? AND Class = ?')
