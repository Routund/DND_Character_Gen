from flask import Flask, render_template, redirect, jsonify,session
from flask import request, url_for, make_response
import sqlite3
import math
import key

app = Flask(__name__)
db = 'main.db'

app.secret_key=key.key
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
def setSession(keys, values):
    for i in range(len(keys)):
        session[keys[i]] = values[i]


@app.route('/create/1')
def create():
    # Render the form template with initial options
    cClass = get_options("Class")
    races = get_options("Race")
    background = get_options("Background")
    session.clear()
    return render_template('CharacterCreation1.html', hClass=cClass, raceData=races, backgroundData=background)


@app.route('/create/2')
def create2():
    # Check if previous form has been filled
    if ('name' not in session):
        return redirect('/create/1')

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Get the choices left to make for the character, then check if the user has any more choices to make
    choices_left = session['choices_to_make']
    if (len(choices_left)>0):
        current_choice = choices_left[0]
        cur.execute(F'SELECT Choices,MaxAllowed,Type FROM ProfChoice WHERE Choice_Id = {current_choice}')
        data = cur.fetchone()
        maxA = int(data[1])
        session['currentChoiceType']=data[2]
        options = data[0].split(',')
        option_values=[]
        if(data[2]=="Proficiency"):
            allProfs = session["proficiencies"]
            for option in options:
                if option in allProfs:
                    options.pop(options.index(option))
            option_values=options
        elif(data[2]=="Ability"):
            # Get ability id for each ability
            for option in options:
                cur.execute(F'SELECT Ability_Id FROM Ability WHERE Name = \'{option}\'')
                option_values.append(cur.fetchone()[0])
        elif(data[2]=="Subclass"):
            for option in options:
                cur.execute(F'SELECT Name FROM Subclass WHERE Subclass_Id = {int(option)}')
                option_values.append(cur.fetchone()[0])
            option_values, options = options,option_values
        return render_template('ChooseProf.html', options=options, option_values=option_values, max_selections=maxA)
    else:
        return redirect('/create/3')


@app.route('/create/3')
def create3():
    # Check if previous form     has been filled
    if ('name' not in session):
        return redirect('/create/1')

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    race = session['chosen_options'][1]
    cur.execute(f'SELECT ASI FROM Race WHERE Race_Id = {race}')
    ASI = []
    if('ASI' not in session):
        ASI = list(map(int,cur.fetchone()[0].split(',')))
    else:
        ASI =session['ASI']
        raceASI = list(map(int,cur.fetchone()[0].split(',')))
        for i in range(6):
            ASI[i]+=raceASI[i]

    session['FinalASI']=ASI

    # Compose a message on which stats the player will get
    added = []
    for i in range(6):
        if (ASI[i] > 0):
            added.append(f"+{ASI[i]} {stat_names[i]}")
        elif (ASI[i] < 0):
            added.append(f"{ASI[i]} {stat_names[i]}")

    # Check if added message is needed
    if (added != []):
        added2 = ', '.join(added)
        return render_template("CharacterCreation2.html", added_message=f"Your race also gives {added2}",destination='submit3',base='8')
    else:
        return render_template("CharacterCreation2.html", added_message=" ",destination='submit3',base="8")


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

        proficiency_list = []
        characteristics = [cClass, race, background]
        table_names = ["Class","Race","Background"]
        for i in range(3):     
            cur.execute(F'SELECT Proficiencies FROM {table_names[i]} WHERE {table_names[i]}_Id = {characteristics[i]}')
            data = cur.fetchone()
            if (data[0] is not None):
                proficiency_list = data[0].split(",")
        
        cur.execute(f'Select Choice_Id FROM ProfChoice WHERE (Race_Id = {race} OR Class_Id = {cClass}) AND Level = 1')
        choices = [y[0] for y in cur.fetchall()]

        setSession(['chosen_options', 'name', 'proficiencies', 'choices_to_make'], [characteristics, name, list(set(proficiency_list)), choices])
        return redirect(url_for('create2'))


@app.route('/submit2', methods=['POST'])
def submit2():
    if request.method == 'POST':
        if(len(session['choices_to_make']))==0:
            return redirect(url_for('create3'))
        else:
            print(session['currentChoiceType'])
            if(session['currentChoiceType']=="Proficiency"):
                # Get the proficiencies so far, and add the proficiencies chosen to the form, then set
                profs_chosen = request.form.getlist('choices')
                all_profs = session['proficiencies']
                setSession(['proficiencies'], [all_profs + profs_chosen])
            elif(session['currentChoiceType']=="Stat"):
                stats_chosen = request.form.getlist('choices')
                ASI = [0,0,0,0,0,0]
                for stat in stats_chosen:
                    ASI[stat_names.index(stat)]+=1
                session['ASI']=ASI
            elif(session['currentChoiceType']=="Ability"):
                chosen_abilities=list(map(int,request.form.getlist('choices')))
                if 'ability' in session:
                    session['ability']+=chosen_abilities
                else:
                    session['ability']=chosen_abilities
            elif(session['currentChoiceType']=="Subclass"):
                session['subclass']=request.form.getlist('choices')[0]
            session['choices_to_make'].pop(0)
            if('id' not in session):
                return redirect(url_for('create2'))
            print(session['choices_to_make'])
            return redirect(url_for('level',id=session['id']))

@app.route('/submit3', methods=['POST'])
def submit3():
    if request.method == 'POST':
        if('id' not in session):
            ASI = session['FinalASI']
            # Calculate total ability scores for each stat based off race ASI and form results
            for i in range(6):
                stat = request.form.get(f'{i}')
                ASI[i] = str(min(20, int(ASI[i])+int(stat)))
            setSession(['AbilitySpread'], [ASI])
            return redirect(url_for('insert'))
        else:
            ASI = [0]*6
            for i in range(6):
                ASI[i]=int(request.form.get(f'{i}'))
                if(ASI[i]<0):
                    return redirect(url_for('level',id=session['id']))
            if(sum(ASI)>2):
                return redirect(url_for('level',id=session['id']))
            session['choices_to_make'].pop(0)
            session['ASI']=ASI
            print(session['ASI'])
            return redirect(url_for('level',id=session['id']))

@app.route('/insert', methods=['GET', 'POST'])
def insert():
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Get all values that need to be inserted
    name = session['name']
    cClass, race, background = session['chosen_options']
    stats = session['AbilitySpread']
    statsJoined = ','.join(stats)
    cur.execute(f'SELECT HpDie FROM Class WHERE Class_Id = {cClass}')
    hp = int(cur.fetchone()[0].split('d')[1])+(int(stats[5])-10)//2
    ac=10+(int(stats[1])-10)//2
    proficiencies = ','.join(session['proficiencies'])

    subclass = 1
    if ('subclass' in session):
        subclass=session['subclass']

    cur.execute('INSERT INTO Character (Name,Race,Class,Level,Background,HP,AC,Stats,Proficiencies,Current_HP,Subclass) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                (name,race,cClass,1,background,hp,ac,statsJoined,proficiencies,hp,subclass,)
                )
    conn.commit()

    last_row= cur.lastrowid
    if('ability' in session):
        for ability in session['ability']:
            abilityType = "'Race'"
            if (ability>=57 and ability<=61):
                abilityType = "Class"
            cur.execute('INSERT INTO AbilityCharacter (Ability_Id,Character_Id,Type) VALUES (?,?,?)',
                        (ability,last_row,abilityType,))
            conn.commit()
    session.clear()
    return redirect(f'/character/{last_row}')


@app.route('/character/<id>')
def character_main(id):
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Check if character exists (ADD KICK FUNCTIONALITY)
    cur.execute('SELECT * FROM Character WHERE Character_Id = ?', (id,))
    character_data = cur.fetchone()
    if character_data is None:
        return redirect("/")

    session.clear()

    # Get Race, Class, Subclassm Proficiencies, Prof Bonus, and Stats. classC is just player class, but avoiding python class keyword
    cur.execute('SELECT Name FROM Race WHERE Race_Id = ?', (character_data[2],))
    race = cur.fetchone()
    cur.execute('SELECT Name FROM Class WHERE Class_Id = ?', (character_data[3],))
    classC = cur.fetchone()
    cur.execute('SELECT Name FROM Subclass WHERE Subclass_Id = ?', (character_data[13],))
    subclass = cur.fetchone()
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

        # Add the profBonus depending on how many times the ability shows up in the proficiencies
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

    # Avoid listing the default of no subclass
    if (character_data[13]!=1):
        values_to_list.append(subclass[0])

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

    session.clear()

    # Get all abilities (feats) by their type, race, class or background, and add them to a list for insertion into html
    feat_names = []
    feat_descriptions = []
    feat_types = ["Race","Class","Background"]
    feat_types_parameters = [character_data[2],character_data[3],character_data[5]]
    for i in range(3):
        added=""
        # Account for class abilities being locked by levels
        if i==1:
            added = f" AND Level <= {character_data[4]}"
        cur.execute(f'SELECT Name,Description FROM Ability WHERE Ability_Id IN (SELECT Ability_Id FROM Ability{feat_types[i]} WHERE {feat_types[i]}_Id = {feat_types_parameters[i]}{added})')
        data = cur.fetchall()
        
        # List comprehension from Stack Overflow
        feat_names.append([i[0] for i in data])
        feat_descriptions.append([i[1] for i in data]) 


    # Add all abilities that are chosen by the user and stored in characterAbility
    cur.execute(f'SELECT Ability_Id,Type FROM AbilityCharacter WHERE Character_Id = ?', (id,))
    data = cur.fetchall()
    for ability in data:
        cur.execute(f'SELECT Name,Description FROM Ability WHERE Ability_Id = {ability[0]}')
        character_ability = cur.fetchone()
        # Check whether if the ability is a racial or class ability
        if(ability[1]=="Race"):
            feat_names[0].append(character_ability[0])
            feat_descriptions[0].append(character_ability[1])
        else:
            feat_names[1].append(character_ability[0])
            feat_descriptions[1].append(character_ability[1])

    other_values = [id,character_data[6],character_data[12],character_data[7],((character_data[4]-1)//4)+2]
    return render_template('CharacterAbility.html',other_values=other_values,names=feat_names,descs=feat_descriptions)

@app.route('/levelUp/<id>')
def level(id):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    # Check if character exists (ADD KICK FUNCTIONALITY)
    cur.execute('SELECT Character_Id,Race,Class,Level,Stats,Proficiencies FROM Character WHERE Character_Id = ?', (id,))
    character_data = cur.fetchone()
    if character_data is None:
        return redirect("/")

    # Get all choices to make if entered loop for first time
    if 'choices_to_make' not in session:
        session.clear()
        cur.execute(f'Select Choice_Id FROM ProfChoice WHERE (Class_Id = {character_data[2]}) AND Level = {character_data[3]+1}')
        session['choices_to_make'] = [y[0] for y in cur.fetchall()]
        # Add Ability score improvements at certain levels
        if (character_data[3]+1 in [4,8,12,16,19]):
            session['choices_to_make'].append(17)
        session['id']=id

    if len(session['choices_to_make'])==0:
        stats = list(map(int,character_data[4].split(',')))
        newLevel=character_data[3]+1
        con=(stats[5]-10)//2

        # Account for hill dwarfs having 1 extra hp per level
        if(character_data[1]==2):
            con+=1  

        # Process the ability score increase if its in the session
        if 'ASI' in session:
            for i in range(6):
                stats[i]=min(20,stats[i]+session['ASI'][i])
        
        if 'subclass' in session:
            # Python throws a fit when session is used in the string
            subclass = session['subclass']
            cur.execute(f'UPDATE Character SET Subclass = {subclass} WHERE Character_Id ={id}')

        statsToCommit=','.join(list(map(str,stats)))
        cur.execute(f'SELECT HpDie FROM Class WHERE Class_Id = {character_data[2]}')
        diceValue = int(cur.fetchone()[0].split('d')[1])
        hp = diceValue + (diceValue//2+1+con)*(newLevel-1)
        cur.execute(f'UPDATE Character SET level = {newLevel},HP={hp},Stats = "{statsToCommit}" WHERE Character_Id ={id}')
        conn.commit()
        session.clear()
        return redirect(f'/character/{id}')
    else:
        choice = session['choices_to_make'][0]
        cur.execute(f'Select Type,Choices,MaxAllowed FROM ProfChoice WHERE Choice_Id={choice}')
        choiceData=cur.fetchone()
        if(choiceData[0]=='ASI'):
            return render_template("CharacterCreation2.html", added_message="Distribute 2 points across your stats.",destination='submit3',base='0')
        maxA = int(choiceData[2])
        session['currentChoiceType']=choiceData[0]
        options = choiceData[1].split(',')
        option_values=[]
        if(choiceData[0]=="Proficiency"):
            allProfs = character_data[5].split(',')
            for option in options:
                if option in allProfs:
                    options.pop(options.index(option))
            option_values=options
        elif(choiceData[0]=="Ability"):
            # Get ability id for each ability and store it in session for when submitted
            ability_ids = {}
            for option in options:
                cur.execute(F'SELECT Ability_Id FROM Ability WHERE Name = \'{option}\'')
                option_values.append(cur.fetchone()[0])
            session['ability_ids']=ability_ids
        elif(choiceData[0]=="Subclass"):
            for option in options:
                cur.execute(F'SELECT Name FROM Subclass WHERE Subclass_Id = {int(option)}')
                option_values.append(cur.fetchone()[0])
            option_values, options = options,option_values
        session['currentChoiceType']=choiceData[0]
        return render_template('ChooseProf.html', options=options,option_values=option_values, max_selections=maxA)


@app.route('/updateHP', methods=['POST'])
def updateHP():
    data = request.get_json()
    HP = int(data.get('HP'))
    AC = int(data.get('AC'))
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
