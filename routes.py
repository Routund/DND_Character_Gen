from flask import Flask, render_template,redirect,request,url_for
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
    return "Home"

# STATS GO STR, DEX, INT, WIS, CHA, CON

def get_options(previous_selection):
    # Perform SQL query to retrieve options based on previous_selection
    # Replace this with your actual SQL query
    options = [("Option 1", "value1"), ("Option 2", "value2"), ("Option 3", "value3")]
    return options

@app.route('/create')
def index():
    # Render the form template with initial options
    options = get_options(None)  # Pass None for initial form render
    return render_template('CharacterCreation.html', options=options)

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        # Get form data
        selected_option = request.form.get('option')
        
        # Insert the user's choice into the database
        # Replace this with your actual database insertion code
        
        # Redirect to success page or back to form
        return redirect(url_for('success'))

@app.route('/success')
def success():
    return "Form submitted successfully!"

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