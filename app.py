from flask import Flask, render_template, request, flash , redirect, send_from_directory
import os
import numpy as np
import pandas as pd
from flask.helpers import url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.elements import Null
from os import listdir
from os.path import isfile, join

from werkzeug.utils import secure_filename

app = Flask(__name__)

def csv_allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in CSV_ALLOWED_EXTENSIONS

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def Load_Data(file_name):
    data = pd.read_csv("people2.csv")
    if list(data.columns) == HEADERS_CHECK:
        data.fillna("", inplace = True) 
        listdict = data.to_dict('records')
        return listdict
    else:
        raise Exception

           



UPLOAD_FOLDER = 'upload'
mypath = "upload/images"
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024    #16Mb Limit

db = SQLAlchemy(app)


class People(db.Model):
    __tablename__ = 'Price_History'
    __table_args__ = {'sqlite_autoincrement': True}
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50),nullable=False)
    state = db.Column(db.String(2),nullable=True)
    salary = db.Column(db.Float,nullable=True)
    grade = db.Column(db.Integer,nullable=True)
    room = db.Column(db.Integer,nullable=True)
    telnum = db.Column(db.String(10),nullable=True)
    picture = db.Column(db.String(50),nullable=True)
    keywords = db.Column(db.String(250),nullable=True)



CSV_ALLOWED_EXTENSIONS = set(['csv',])
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
HEADERS_CHECK = ['Name', 'State', 'Salary', 'Grade', 'Room', 'Telnum', 'Picture', 'Keywords']

@app.route('/')
def index():
    return "Hello World"

@app.route('/upload_csv', methods=['GET','POST'])
def upload_csv():
    if request.method=='POST':
        if 'csvFile' not in request.files:
            flash('No file part','warning')
            return redirect(request.url)
        file = request.files['csvFile']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file','warning')
            return redirect(request.url)
        if file and csv_allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            try:
                num_rows_deleted = db.session.query(People).delete()
                db.session.commit()
                
            except:
                db.session.rollback()
                flash('A fatal error occured.','danger')
                return redirect(request.url)
            try:
                data = Load_Data(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            except:
                flash('A fatal error occured.','danger')
                return redirect(request.url)
            try:
                for i in data:  #['Name', 'State', 'Salary', 'Grade', 'Room', 'Telnum', 'Picture', 'Keywords']
                    if i['Salary'] == '':
                        salary = None
                    else:
                        try:
                            salary = float(i['Salary'])
                        except:
                            salary = None
                    if i['Grade'] == '':
                        grade = None
                    else:
                        try:
                            grade = int(i['Grade'])
                        except:
                            grade = None
                    if i['Room'] == '':
                        room = None
                    else:
                        try:
                            room = int(i['Room'])
                        except:
                            room = None
                    if i['Telnum'] == '':
                        telnum = None
                    else:
                        try:
                            telnum = str(i['Telnum'])
                        except:
                            telnum = None
                    if i['Picture'] == '':
                        picture = None
                    else:
                        try:
                            picture = str(i['Picture'])
                        except:
                            picture = None
                    if i['Keywords'] == '':
                        keywords = None
                    else:
                        try:
                            keywords = str(i['Keywords'])
                        except:
                            keywords = None
                    record = People(**{
                        'name' : i['Name'],
                        'state' : i['State'],
                        'salary' : salary,

                        'grade' : grade,
                        'room' : room,
                        'telnum' : telnum,
                        'picture': picture,
                        'keywords': keywords
                    })
                    db.session.add(record) #Add all the records

                db.session.commit() #Attempt to commit all the records
            except Exception as e:
                db.session.rollback() #Rollback the changes on error
                flash('Error while adding data to database','danger')
                return redirect(request.url)

            flash('Successfully add data to database','success')
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            except:
                flash('Error while deleting csv file','danger')
                return redirect(request.url)
            return redirect(request.url)
        else:
            flash('Wrong extention. Please select a csv file.','warning')
            return redirect(request.url)
    else:
        # In case of GET request
        return render_template('upload_csv.html')

#return redirect(url_for('uploaded_file',filename=filename))
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


@app.route('/upload_image', methods=['GET','POST'])
def upload_image():
    if request.method=='POST':
        if 'image' not in request.files:
            flash('No Image','warning')
            return redirect(request.url)
        file = request.files['image']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file','warning')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            try:
                onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
                if filename in onlyfiles:
                    raise Exception
            except:
                flash('Same name image already exists','danger')
                return redirect(request.url)
            try:
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'images/'+filename))
            except:
                flash('Error while saving image','danger')
                return redirect(request.url)
            flash('Image successfully uploaded','success')
            return redirect(request.url)
        else:
            flash('Wrong extention. Please select a valid file.','warning')
            return redirect(request.url)
    else:
        # In case of GET request
        return render_template('upload_image.html')

if __name__=="__main__":
    app.run(debug=True)