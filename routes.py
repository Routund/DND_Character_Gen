from flask import Flask, render_template, redirect, jsonify, session
from hashlib import sha256
from flask import request, url_for, abort
import sqlite3
from math import floor
import key
from random import choice
from gc import collect

app = Flask(__name__)
db = 'main.db'

app.secret_key = key.key
# 2d array of skills, ordered by their stat
skills = [
    ["Athletics"],
    ["Acrobatics", "Sleight of hand", "Stealth"],
    ["Arcana", "History", "Investigation", "Nature", "Religion"],
    ["Animal Handling", "Insight", "Medicine", "Perception", "Survival"],
    ["Deception", "Intimidation", "Performance", "Persuasion"],
    []]

stat_names = ["Strength", "Dexterity", "Intelligence",
              "Wisdom", "Charisma", "Constitution"]


# Return create1
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/user')
    return render_template('HomePage.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('Errors.html',
                           Error='''Either we could not find the page,
                             or you do not have access to it'''), 404


@app.errorhandler(403)
def no_permission(error):
    return render_template('Errors.html',
                           Error='''Either we could not find the page,
                            or you do not have access to it'''), 403


@app.errorhandler(400)
def bad_request(error):
    return render_template('Errors.html',
                           Error='''Malformed request,
                           try logging out then logging back in'''), 400


@app.errorhandler(500)
def general_error(error):
    return render_template('Errors.html',
                           Error='''Something seemed to have gone wrong'''), 500


@app.errorhandler(KeyError)
def handle_key_error(e):
    # You can log the error if needed
    resetSession()
    return render_template('Errors.html',
                           Error='''There seems to have been a problem with our
                            forms, please try doing the
                            form again from the start'''), 655


def get_options(table):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(f"SELECT Name,{table}_Id FROM {table}")
    options = cur.fetchall()
    return options


# Query code.
# OneOrAll is meant to differentiate between fetchones and fetchalls
# True is one, False is all
def querydb(query, values, oneOrAll):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(query, values)
    if oneOrAll:
        return cur.fetchone()
    else:
        return cur.fetchall()
    # PyLance seems to think there needs to be a ) here.
    # No idea why, code does not break


# Cookie Setter
def setSession(keys, values):
    for i in range(len(keys)):
        session[keys[i]] = values[i]


# Set up information on the choice
def decompressChoice(current_choice):
    data = querydb(F'''SELECT Choices,MaxAllowed,Type FROM ProfChoice
                        WHERE Choice_Id = {current_choice}''', (), True)
    session['current_choice'] = current_choice
    if (data[2] == 'ASI'):
        # Check whether the choice is an asi, in that case skip everything
        return [0]
    maxA = int(data[1])
    session['currentChoiceType'] = data[2]
    options = data[0].split(',')
    option_values = []
    title = ""
    if (data[2] == "Proficiency"):
        # Get all proficiencies, and block proficiencies already taken
        allProfs = session["proficiencies"]
        for option in options:
            if option in allProfs:
                options.pop(options.index(option))
        option_values = options
        title = f"Select up to {maxA} proficiencies:"
    elif (data[2] == "Expertise"):
        # Find all proficiencies that can have expertise applied to them among
        # the current proficiencies. This also stops skils already with
        # proficiencies from getting more proficient
        allProfs = session["proficiencies"]
        i = 0
        while (i < len(options)):
            if allProfs.count(options[i]) != 1:
                options.pop(options.index(options[i]))
            else:
                i += 1
        option_values = options
        title = f"Take expertise(double proficiencies) in {maxA} skills:"
    elif (data[2] == "Ability"):
        abilities = session.get('ability', [])
        # Get ability id for each ability
        for option in options:
            value = querydb(F'''SELECT Ability_Id FROM Ability
                                 WHERE Name = \'{option}\'''',
                            (), True)[0]
            if value in abilities:
                continue
            option_values.append(value)
            title = f"Gain {maxA} Abilities:"
    elif (data[2] == "Subclass"):
        for option in options:
            option_value = querydb(F'''SELECT Name FROM Subclass
                                        WHERE Subclass_Id = {int(option)}''',
                                   (), True)
            option_values.append(option_value[0])
        option_values, options = options, option_values
        title = "Choose your subclass:"
    elif (data[2] == "Stat"):
        title = f'''Choose {maxA} stats for your
         character to have a +1 increase in:'''
        option_values = options
    return [options, option_values, maxA, title]


# Code to generate salts copied from
# https://pynative.com/python-generate-random-string/#h-how-to-create-a-random-string-in-python
def generate_salt(length):
    # Choose from set of characters
    letters = 'qwertyuiopasdfghjklzxcvbnm1234567890QWERTYUIOPASDFGHJKLZXCVBNM'
    result_str = ''.join(choice(letters) for i in range(length))
    return result_str


# Function to clear session while preserving the logged in user
def resetSession():
    if 'user_id' in session:
        placeholder = session['user_id']
    else:
        placeholder = None
    session.clear()
    collect()
    if placeholder is not None:
        session['user_id'] = placeholder


@app.route('/sign_up')
def sign_up():
    # Check for if password or username failed,
    # and pass that on to the html page
    if ('passwordFailed' in session):
        del session['passwordFailed']
        return render_template('SignUp.html', title="Sign Up:",
                               usernameFailed=False, passwordFailed=True)
    if ('usernameFailed' in session):
        del session['usernameFailed']
        return render_template('SignUp.html', title="Sign Up:",
                               usernameFailed=True, passwordFailed=False)
    else:
        return render_template('SignUp.html', title="Sign Up:",
                               usernameFailed=False, passwordFailed=False)


@app.route('/login')
def login():
    # Check for if password or username failed,
    #  and pass that on to the html page
    if ('failed' in session):
        return render_template('Login.html', title="Log in to your account:",
                               failed=True)
    else:
        return render_template('Login.html', title="Log in to your account:",
                               failed=False)


@app.route('/signupConfirm', methods=['POST'])
def signupConfirm():
    if request.method == 'POST':
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        # Check if passwords match
        if password1 == password2:
            username = request.form.get('username')
            conn = sqlite3.connect(db)
            cur = conn.cursor()
            # Ensure that no other users have the same name, if not,
            # return sign up with username error
            cur.execute('SELECT User_Id FROM User WHERE Username = ?',
                        (username,))
            if len(cur.fetchall()) == 0:
                # Generate a salt, add it to password, hash,
                # and then insert this user info into the user table
                salt = generate_salt(6)
                password1 += salt
                hasher = sha256()
                hasher.update(password1.encode())
                hashed = hasher.hexdigest()
                cur.execute('''INSERT INTO User (Username,Hash,Salt)
                             VALUES (?,?,?)''', (username, hashed, salt,))
                conn.commit()
                # Remove passwords immediately instead of letting them stay
                # in memory. This also removes any del keywords used in
                # sign up page
                del password1
                del password2
                collect()
                session.clear()
                return redirect(url_for('login'))
            session['usernameFailed'] = True
            return redirect(url_for('sign_up'))
        session['passwordFailed'] = True
        return redirect(url_for('sign_up'))


@app.route('/loginConfirm', methods=['POST'])
def loginConfirm():
    if request.method == 'POST':
        password = request.form.get('password')
        username = request.form.get('username')
        data = querydb('SELECT User_Id,Hash,Salt FROM User WHERE Username = ?',
                       (username,), True)
        # Check if user exists, else return poge with failed
        if data is not None:
            # Hash password with salt added, and if sucessful,
            # redirect to account page
            hasher = sha256()
            password += data[2]
            hasher.update(password.encode())
            hashed = hasher.hexdigest()
            if hashed == data[1]:
                session['user_id'] = data[0]
                # Delete password to acoid it staying in memory
                del password
                collect()
                return redirect('/user')
        session['failed'] = True
        return redirect(url_for('login'))


@app.route('/user')
def userPage():
    # Check if user logged in. Since name can only be obtained by going
    # through this page, any subsequent character creation pages will
    # need go thorugh this page
    if 'user_id' not in session:
        return redirect('/login')

    username = querydb('SELECT Username FROM User WHERE User_Id = ?',
                       (session['user_id'],), True)[0]

    characters = querydb('''SELECT Character.Character_Id,Character.Name,Race.Name,
                Class.Name FROM Character JOIN Class ON
                 Character.Class = Class.Class_Id JOIN Race ON
                 Character.Race = Race.Race_Id WHERE User_Id = ?''',
                         (session['user_id'],), False)

    resetSession()
    # Render the form template with initial options
    return render_template('UserPage.html', characters=characters,
                           username=username)


@app.route('/logout')
def logout():
    # Check if user logged in. Since name can only be obtained by going
    # through this page, any subsequent character creation pages
    # will need go thorugh this page
    if 'user_id' in session:
        session.clear()
    return redirect('login')


@app.route('/create/1')
def create():
    # Check if user logged in. Since name can only be obtained by
    # going through this page, any subsequent character
    # creation pages will need go thorugh this page
    if 'user_id' not in session:
        return redirect('/login')
    # Render the form template with initial options
    cClass = get_options("Class")
    races = get_options("Race")
    background = get_options("Background")
    resetSession()
    return render_template('CharacterCreation1.html', hClass=cClass,
                           raceData=races, backgroundData=background,
                           title="Character Creation")


@app.route('/create/2')
def create2():
    # Check if previous form has been filled
    if ('name' not in session):
        return redirect('/create/1')

    # Get the choices left to make for the character,
    # then check if the user has any more choices to make
    choices_left = session['choices_to_make']
    if (len(choices_left) > 0):
        current_choice = choices_left[0]
        choiceData = decompressChoice(current_choice)
        return render_template('ChooseProf.html', options=choiceData[0],
                               option_values=choiceData[1],
                               max_selections=choiceData[2],
                               title="Character Creation",
                               user_prompt=choiceData[3])
    else:
        return redirect('/create/3')


@app.route('/create/3')
def create3():
    # Check if previous form     has been filled
    if ('name' not in session):
        return redirect('/create/1')

    race = session['chosen_options'][1]
    data = querydb(f'SELECT ASI FROM Race WHERE Race_Id = {race}', (), True)
    ASI = []
    if ('ASI' not in session):
        ASI = list(map(int, data[0].split(',')))
    else:
        ASI = session['ASI']
        raceASI = list(map(int, data[0].split(',')))
        for i in range(6):
            ASI[i] += raceASI[i]

    session['FinalASI'] = ASI

    # Compose a message on which stats the player will get
    added = []
    for i in range(6):
        if (ASI[i] > 0):
            added.append(f"+{ASI[i]} {stat_names[i]}")
        elif (ASI[i] < 0):
            added.append(f"{ASI[i]} {stat_names[i]}")

    # Check if added message is needed
    if (added != []):
        # Add Race ASI to page, to give information on
        # what stats will be increased
        added2 = ', '.join(added)
        return render_template("CharacterCreation2.html",
                               added_message=f'''Please input your characters
                                stats<br>Your race also gives {added2}''',
                               destination='submit3', base='8',
                               title="Character Creation")
    else:
        return render_template("CharacterCreation2.html",
                               added_message="Please input your stats",
                               destination='submit3', base="8",
                               title="Character Creation")


@app.route('/submit1', methods=['POST'])
def submit1():
    if request.method == 'POST':

        # Get all options for each attribute
        cClass = request.form.get('cClass')
        name = request.form.get('name')
        race = request.form.get('race')
        background = request.form.get('background')

        proficiency_list = []
        characteristics = [cClass, race, background]
        table_names = ["Class", "Race", "Background"]
        for i in range(3):
            data = querydb(F'''SELECT Proficiencies FROM {table_names[i]}
                         WHERE {table_names[i]}_Id = {characteristics[i]}''',
                           (), True)
            if (data[0] is not None):
                proficiency_list = data[0].split(",")

        choices = querydb(f'''Select Choice_Id FROM ProfChoice WHERE
                     (Race_Id = {race} OR Class_Id = {cClass})
                      AND Level = 1''', (), False)
        choices = [y[0] for y in choices]

        setSession(['chosen_options', 'name',
                    'proficiencies', 'choices_to_make'],
                   [characteristics, name,
                   list(set(proficiency_list)), choices])
        return redirect(url_for('create2'))


@app.route('/submit2', methods=['POST'])
def submit2():
    if request.method == 'POST':
        if (len(session['choices_to_make'])) == 0:
            return redirect(url_for('create3'))
        elif session['current_choice'] is not session['choices_to_make'][0]:
            if 'id' not in session:
                return redirect(url_for('character_main', id=session['id']))
            else:
                return redirect(url_for('userPage'))
        else:
            if ((session['currentChoiceType'] == "Proficiency"
                 or session['currentChoiceType'] == "Expertise")):
                # Get the proficiencies so far,
                # and add the proficiencies chosen to the form,
                # then set
                profs_chosen = request.form.getlist('choices')
                all_profs = session['proficiencies']
                setSession(['proficiencies'], [all_profs + profs_chosen])
            elif (session['currentChoiceType'] == "Stat"):
                stats_chosen = request.form.getlist('choices')
                ASI = [0, 0, 0, 0, 0, 0]
                for stat in stats_chosen:
                    ASI[stat_names.index(stat)] += 1
                session['ASI'] = ASI
            elif (session['currentChoiceType'] == "Ability"):
                chosen_abilities = list(map(int,
                                            request.form.getlist('choices')))
                if 'ability' in session:
                    session['ability'] += chosen_abilities
                else:
                    session['ability'] = chosen_abilities
            elif (session['currentChoiceType'] == "Subclass"):
                subclass = request.form.getlist('choices')
                # SideBa
                if len(subclass) == 0:
                    subclass = 1
                else:
                    subclass = subclass[0]
                if subclass == 11:
                    session['choices_to_make'].append(143)
                session['subclass'] = subclass
            session['choices_to_make'].pop(0)
            if ('id' not in session):
                return redirect(url_for('create2'))
            return redirect(url_for('level', id=session['id']))


@app.route('/submit3', methods=['POST'])
def submit3():
    if request.method == 'POST':
        if ('id' not in session):
            if 'name' not in session:
                return redirect(url_for('user'))
            ASI = session['FinalASI']
            # Calculate total ability scores for each stat based
            # off race ASI and form results
            for i in range(6):
                stat = request.form.get(f'{i}')
                ASI[i] = str(min(20, int(ASI[i])+int(stat)))
            setSession(['AbilitySpread'], [ASI])
            return redirect(url_for('insert'))
        else:
            ASI = [0]*6
            for i in range(6):
                ASI[i] = int(request.form.get(f'{i}'))
                # Prevent negative numbers
                if (ASI[i] < 0):
                    return redirect(url_for('level', id=session['id']))
            # Stop ASIs from having more than 2 points set
            if (sum(ASI) > 2):
                return redirect(url_for('level', id=session['id']))
            session['choices_to_make'].pop(0)
            session['ASI'] = ASI
            return redirect(url_for('level', id=session['id']))


# Conn is defined here to insert values into table
@app.route('/insert', methods=['GET', 'POST'])
def insert():
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Get all values that need to be inserted
    # (python throws a fit when session is in the execute statement)
    name = session['name']
    cClass, race, background = session['chosen_options']
    stats = session['AbilitySpread']
    statsJoined = ','.join(stats)
    cur.execute(f'SELECT HpDie FROM Class WHERE Class_Id = {cClass}')
    hp = int(cur.fetchone()[0].split('d')[1])+(int(stats[5])-10)//2
    ac = 10+(int(stats[1])-10)//2
    proficiencies = ','.join(session['proficiencies'])
    user_id = session['user_id']

    # Get subclass if set, else keep it as none
    subclass = 1
    if ('subclass' in session):
        subclass = session['subclass']

    # Generate the characters notes template
    cur.execute(f'SELECT Languages FROM Race WHERE Race_Id = {race}')
    notes = f'''
Proficiencies - {proficiencies}\n
Money - 0 Platinum, 15 Gold, 0 Electrum, 0 Silver, 0 Copper\n
Languages - {cur.fetchone()[0]}\n
Personality Traits -\n\n
Ideals -\n\n
Bonds -\n\n
Flaws -\n\n
    '''

    if (race == 2 or subclass == 11):
        hp += 1
    cur.execute('''INSERT INTO Character (Name,Race,Class,Level,Background,HP,
                AC,Stats,Proficiencies,Current_HP,Subclass,User_Id,Notes)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (name, race, cClass, 1, background, hp, ac, statsJoined,
                 proficiencies, hp, subclass, user_id, notes))
    conn.commit()
    last_row = cur.lastrowid

    # Map any abilities set beforehand into AbilityCharacter
    if ('ability' in session):
        for ability in session['ability']:
            abilityType = "Race"
            if (ability >= 57 and ability <= 61):
                abilityType = "Class"
            cur.execute('''INSERT INTO AbilityCharacter
                         (Ability_Id,Character_Id,Type) VALUES (?,?,?)''',
                        (ability, last_row, abilityType,))
            conn.commit()
    resetSession()
    return redirect(f'/character/{last_row}')


def get_from_character(id):
    character_data = querydb('SELECT * FROM Character WHERE Character_Id = ?',
                             (id,), True)
    return character_data


@app.route('/character/<id>')
def character_main(id):
    character_data = get_from_character(id)

    # Check if character exists, or if user id matches.
    # redirect doesnt seem to work in a function,
    # so it has to be repeated in each character page
    if character_data is None:
        abort(404)
    elif ('user_id' not in session) or character_data[14] != session['user_id']:
        abort(403)

    resetSession()

    # Get Race, Class, Subclassm Proficiencies,
    # Prof Bonus, and Stats. classC is just player class,
    # but avoiding python class keyword
    race = querydb('SELECT Name FROM Race WHERE Race_Id = ?',
                   (character_data[2],), True)
    classC = querydb('SELECT Name FROM Class WHERE Class_Id = ?',
                     (character_data[3],), True)
    subclass = querydb('SELECT Name FROM Subclass WHERE Subclass_Id = ?',
                       (character_data[13],), True)
    proficiencies = character_data[9].split(',')
    stats = list(map(int, character_data[8].split(',')))
    prof_bonus = ((character_data[4]-1)//4)+2

    # Calculate ability score for each ability
    # by checking proficiencies list for given ability,
    # then -10 and /2 plus any profs to get score
    # Also calculate each stat modifier in the same loop
    i = 0
    skillBonus = []
    stat_data = []

    while (i < 6):
        stat_abilities = skills[i]
        mod = floor((stats[i]-10)//2)

        if (proficiencies.count(stat_names[i]) != 0):
            stat_data.append([stat_names[i], mod, mod+prof_bonus])
        else:
            stat_data.append([stat_names[i], mod, mod])

        # Add the profBonus depending on how many times
        # the ability shows up in the proficiencies
        for ability in stat_abilities:
            skillBonus.append((ability, mod +
                               (proficiencies.count(ability)) * prof_bonus))
        i += 1

    values_to_list = [character_data[1], race[0], classC[0]]
    values_category = ["Name", "Race", "Class"]

    # Sidebar Values
    # id, max health, current health, AC,
    # proficiency, user, class, level
    other_values = [id, character_data[6], character_data[12],
                    character_data[7], prof_bonus,
                    character_data[14], character_data[3], character_data[4]]

    # Avoid listing the default of no subclass
    if (character_data[13] != 1):
        values_to_list.append(subclass[0])
        values_category.append("Subclass")

    return render_template('CharacterMain.html', character=values_to_list,
                           skillData=skillBonus, other_values=other_values,
                           statData=stat_data,
                           characterCategories=values_category)


@app.route('/character_abilities/<id>')
def character_abilities(id):
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Check if character exists, or if user id matches
    character_data = get_from_character(id)
    if character_data is None:
        abort(404)
    elif ('user_id' not in session) or character_data[14] != session['user_id']:
        abort(403)

    resetSession()

    # Get all abilities (feats) by their type, race, class or background,
    # and add them to a list for insertion into html
    feat_names = []
    feat_descriptions = []
    feat_types = ["Race", "Class", "Background", "Subclass"]
    feat_types_parameters = [character_data[2], character_data[3],
                             character_data[5], character_data[13]]
    for i in range(4):
        added = ""
        # Account for class and subclass abilities being locked by levels
        if i == 1 or i == 3:
            added = f" AND Level <= {character_data[4]}"

        cur.execute(f'''SELECT Name,Description FROM Ability
                     WHERE Ability_Id IN (SELECT Ability_Id
                     FROM Ability{feat_types[i]}
                       WHERE {feat_types[i]}_Id =
                         {feat_types_parameters[i]}{added})''')
        data = cur.fetchall()

        # List comprehension from Stack Overflow
        feat_names.append([i[0] for i in data])
        feat_descriptions.append([i[1] for i in data])

    # Add all abilities that are chosen by the user
    # and stored in characterAbility
    cur.execute('''SELECT Ability_Id,Type FROM AbilityCharacter
                 WHERE Character_Id = ?''', (id,))
    data = cur.fetchall()
    for ability in data:
        cur.execute(f'''SELECT Name,Description FROM Ability
                     WHERE Ability_Id = {ability[0]}''')
        character_ability = cur.fetchone()
        # Check whether if the ability is a racial or class ability
        if (ability[1] == "Race"):
            feat_names[0].insert(0, character_ability[0])
            feat_descriptions[0].insert(0, character_ability[1])
        else:
            feat_names[1].insert(0, character_ability[0])
            feat_descriptions[1].insert(0, character_ability[1])

    # Sider bar values (list of what they represent on main page route code)
    other_values = [id, character_data[6], character_data[12],
                    character_data[7], ((character_data[4]-1)//4)+2,
                    character_data[14], character_data[3], character_data[4]]
    return render_template('CharacterAbility.html', other_values=other_values,
                           names=feat_names, descs=feat_descriptions)


@app.route('/levelUp/<id>')
def level(id):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    # Check if character exists, or if user id matches
    cur.execute('''SELECT Character_Id,Race,Class,Level,Stats,Proficiencies,
                Subclass,User_Id FROM Character WHERE Character_Id = ?''',
                (id,))
    character_data = cur.fetchone()
    if character_data is None:
        abort(404)
    elif ('user_id' not in session) or character_data[7] != session['user_id']:
        abort(403)

    if character_data[3] >= 20:
        return redirect(f'/character/{id}')

    # Get all choices to make if entered loop for first time
    if 'choices_to_make' not in session:
        resetSession()
        cur.execute(f'''Select Choice_Id FROM ProfChoice
                     WHERE (Class_Id = {character_data[2]})
                       AND Level = {character_data[3]+1}''')
        session['choices_to_make'] = [y[0] for y in cur.fetchall()]
        session['proficiencies'] = character_data[5].split(',')

        # Add Ability score improvements at certain levels
        if (character_data[3]+1 in [4, 8, 12, 16, 19]):
            session['choices_to_make'].append(17)

        # Account for champion fighters getting a choice of a new
        # fighting style at level 10
        if (character_data[3]+1 == 10 and character_data[6] == 6):
            session['choices_to_make'].apend(16)
            cur.execute('''SELECT Ability_Id FROM CharacterAbility
                         WHERE Character_Id = ?''',
                        id)
            session['ability'] = cur.fetchone()
        session['id'] = id
        return render_template("levelUp.html", id=id)

    # Check to see if there are no choices are left, and if so, update character
    if len(session['choices_to_make']) == 0:
        stats = list(map(int, character_data[4].split(',')))
        newLevel = character_data[3]+1
        con = (stats[5]-10)//2

        # Account for hill dwarfs having 1 extra hp per level,
        # same for the Draconic bloodline  sorcerous origin
        if (character_data[1] == 2 or character_data[6] == 11):
            con += 1

        # Process the ability score increase if its in the session
        if 'ASI' in session:
            for i in range(6):
                stats[i] = min(20, stats[i]+session['ASI'][i])

        if 'subclass' in session:
            # Python throws a fit when session is used in the string
            subclass = session['subclass']
            cur.execute(f'''UPDATE Character SET Subclass = {subclass}
                         WHERE Character_Id ={id}''')

        # Add an ability to the character if in session
        if 'ability' in session:
            for ability in session['ability']:
                abilityType = "'Race'"
                if (ability >= 57 and ability <= 61):
                    abilityType = "Class"
            cur.execute('''INSERT INTO AbilityCharacter
                         (Ability_Id,Character_Id,Type)
                         VALUES (?,?,?)''',
                        (ability, id, abilityType,))

        # Get Values to update for character
        statsToCommit = ','.join(list(map(str, stats)))
        cur.execute(f'''SELECT HpDie FROM Class
                     WHERE Class_Id = {character_data[2]}''')
        diceValue = int(cur.fetchone()[0].split('d')[1])
        hp = diceValue + (diceValue//2+1+con)*(newLevel-1)
        proficiencies = ','.join(session['proficiencies'])

        cur.execute(f'''UPDATE Character SET level = {newLevel},HP={hp},
                    Stats = "{statsToCommit}",Proficiencies = "{proficiencies}"
                      WHERE Character_Id ={id}''')
        conn.commit()
        resetSession()
        return redirect(f'/character/{id}')
    else:
        # Generate choice info thorugh decompressChoice
        choice = session['choices_to_make'][0]
        choiceData = decompressChoice(choice)
        # decompressChoice is rigged to return no choices if
        # and only if its a stat increase,
        # so then the ASI page will be loaded
        if (len(choiceData) == 1):
            return render_template("CharacterCreation2.html",
                                   added_message='''Distribute 2 points
                                    across your stats.''',
                                   destination='submit3', base='0',
                                   title="Level Up")
        return render_template('ChooseProf.html', options=choiceData[0],
                               option_values=choiceData[1],
                               max_selections=choiceData[2],
                               title="Level Up",
                               user_prompt=choiceData[3])


# store what the highest slot a caster can have at each level
# 0 is full, 1 is half, 2 is warlock
caster_spells = [
    [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 9, 9],
    [-1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5],
    [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
]


@app.route('/character_spells/<id>/<category>')
def character_spells(id, category):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    # Get the needed character data, and the class name
    cur.execute('''SELECT Character.Class,Character.User_Id,Class.Name,
                Character.HP,Character.Current_HP,Character.AC,
                Character.Level FROM Character JOIN Class ON
                 Character.Class = Class.Class_Id WHERE
                 Character_Id = ?''', (id,))
    character_data = cur.fetchone()
    # Check if character exists, or if user id matches
    if character_data is None:
        abort(404)
    elif ('user_id' not in session) or character_data[1] != session['user_id']:
        abort(403)

    # Prevent classes that cant cast spells from acessing page
    # Else, store what type of caster they are
    caster = 1
    if character_data[0] in [2, 5, 6, 9]:
        return redirect(f"/character/{id}")
    elif character_data[0] in [1, 3, 4, 10, 12]:
        caster = 0
    elif character_data[0] == 11:
        caster = 2

    # Check if the category of the spells page is valid
    # There are two categories, normal, and wizards who
    # have both a prepared and unknown spell list
    if category == "0" or (category == "1" and character_data[0] == 12):
        category = int(category)
    else:
        abort(404)

    spellData = []
    unknowns = []

    if category == 0:
        # Get all spells a character has
        cur.execute('''SELECT * FROM Spell WHERE Spell_Id in
                    (SELECT Spell_Id FROM SpellCharacter WHERE Character_Id = ?)
                    ORDER BY Level''', (id,))
        spellData = cur.fetchall()

        # Get all spells a character could learn at this level,
        # but haven't based off their class and caster type
        cur.execute('''SELECT Spell_Id,Name,Level FROM Spell WHERE Spell_Id IN
                    (SELECT Spell_Id FROM SpellClass WHERE Class_Id = ? AND
                    Spell_Id AND NOT Spell_Id In (SELECT Spell_Id FROM
                    SpellCharacter WHERE Character_Id = ?) AND Level <= ?)
                    ORDER BY Level''',
                    (character_data[0], id,
                     caster_spells[caster][character_data[6]-1]))
        unknowns = cur.fetchall()
    else:
        # Get all spells a character has prepared
        cur.execute('''SELECT * FROM Spell WHERE Spell_Id in
                    (SELECT Spell_Id FROM SpellCharacterWizard
                     WHERE Character_Id = ?)
                    ORDER BY Level''', (id,))
        spellData = cur.fetchall()

        # Get all spells the wizard knows but hasn't prepared
        cur.execute('''SELECT Spell_Id,Name,Level FROM Spell WHERE Spell_Id IN
                    (SELECT Spell_Id FROM SpellCharacter WHERE Character_Id = ?
                     AND NOT Spell_Id In (SELECT Spell_Id FROM
                    SpellCharacterWizard WHERE Character_Id = ?) AND Level <= ?)
                    ORDER BY Level''',
                    (id, id, caster_spells[caster][character_data[6]-1]))
        unknowns = cur.fetchall()

    resetSession()

    # SideBar Values
    other_values = [id, character_data[3], character_data[4],
                    character_data[5], ((character_data[6]-1)//4)+2,
                    character_data[1], character_data[0], character_data[6]]
    return render_template('CharacterSpells.html', other_values=other_values,
                           spellData=spellData,
                           unknownSpells=unknowns,
                           category=category)


@app.route('/updateHP', methods=['POST'])
def updateHP():
    # Get HP and AC, and update table to match.
    # The returned HP is not required, but it's nice to  have
    data = request.get_json()
    HP = int(data.get('HP'))
    AC = int(data.get('AC'))
    id = data.get('id')

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Stop really large numbers from being inputted into database
    if (HP <= 9999 and AC <= 99):
        cur.execute(f'''UPDATE Character SET Current_HP = '{HP}',
                    AC = {AC} WHERE Character_Id = {id}''')
        conn.commit()
    return jsonify({'status': 'success', 'received_value': HP})


@app.route('/insertSpell', methods=['POST'])
def insertSpell():
    # Get the chosen spell, and add it to the map table
    # Then, return all the info about the spell
    data = request.get_json()
    spell = int(data.get('spell_Id'))
    id = data.get('id')
    category = int(data.get('category'))

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    spellData = []

    # Differentiate between removing prepared spells, and spellbook spells
    # (Only matters if character is wizard)
    if category == 0:
        cur.execute('''INSERT INTO SpellCharacter (Spell_Id,Character_Id)
                    VALUES (?,?)''', (spell, id))
    else:
        cur.execute('''INSERT INTO SpellCharacterWizard (Spell_Id,Character_Id)
                    VALUES (?,?)''', (spell, id))
    cur.execute('''SELECT * FROM Spell WHERE Spell_Id = ?''', (spell,))
    spellData = cur.fetchone()
    conn.commit()

    return jsonify({'status': 'success', 'spellArray': spellData})


@app.route('/removeSpell', methods=['POST'])
def removeSpell():
    # Get the chosen spell, and remove it from the map table
    # Then, return all the info about the spell
    data = request.get_json()
    spell = int(data.get('spell_Id'))
    id = data.get('id')
    category = int(data.get('category'))

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Differentiate between removing prepared spells, and spellbook spells
    # (Only matters if character is wizard)
    if category == 0:
        cur.execute('''DELETE FROM SpellCharacter WHERE
                    Spell_Id = ? AND Character_Id = ?''', (spell, id))
    cur.execute('''DELETE FROM SpellCharacterWizard WHERE
                    Spell_Id = ? AND Character_Id = ?''', (spell, id))

    cur.execute('''SELECT Spell_Id,Name,Level FROM Spell
                 WHERE Spell_Id = ?''', (spell,))
    spellData = cur.fetchone()
    conn.commit()

    return jsonify({'status': 'success', 'spellArray': spellData})


@app.route('/character_notes/<id>')
def character_notes(id):

    # Check if character exists, or if user id matches
    character_data = get_from_character(id)
    if character_data is None:
        abort(404)
    elif ('user_id' not in session) or character_data[14] != session['user_id']:
        abort(403)

    resetSession()
    other_values = [id, character_data[6], character_data[12],
                    character_data[7], ((character_data[4]-1)//4)+2,
                    character_data[14], character_data[3], character_data[4]]
    return render_template('CharacterNotes.html', other_values=other_values,
                           notes=character_data[11])


@app.route('/updateNotes', methods=['POST'])
def updateNotes():
    # Get HP and AC, and update table to match.
    # The return value is not required, but it's nice to  have
    data = request.get_json()
    notes = data.get('notes')
    id = data.get('id')

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    cur.execute(f'''UPDATE Character SET Notes = ?
                WHERE Character_Id = {id}''', (notes,))
    conn.commit()
    return jsonify({'status': 'success', 'received_value': notes})


@app.route('/deleteCharacter', methods=['Post'])
def deleteCharacter():
    # Delete a character
    data = request.get_json()
    character_id = data.get('id')

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Delete Character, Pragma is to ensure that all
    # foreign keys referencing character are deleted
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute(f'''DELETE FROM Character WHERE
                 Character_Id = {character_id}''')

    conn.commit()
    return jsonify({'status': 'success'})


if __name__ == "__main__":
    app.run(debug=True)
