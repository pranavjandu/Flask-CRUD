from flask import Flask, render_template, request, flash , redirect, send_from_directory
import os
import numpy as np
import pandas as pd
from flask.helpers import url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.elements import Null
from os import listdir
from os.path import isfile, join
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, __version__

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

           

from secret import AZURE_STORAGE_CONNECTION_STRING
AZURE_CONTAINER_NAME = "images"
UPLOAD_FOLDER = 'upload'
mypath = "static/images"
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
    return render_template('home.html')

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
                blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
                container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
                blob_list = container_client.list_blobs()
                onlyfiles = []
                for blob in blob_list:
                    onlyfiles.append(blob.name)
                if filename in onlyfiles:
                    raise Exception
            except:
                flash('Same name image already exists','danger')
                return redirect(request.url)
            try:
                file.save(os.path.join('static', 'images/'+filename))
                blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER_NAME, blob=filename)
                with open("static/images/"+filename, "rb") as data:
                    blob_client.upload_blob(data)
            except:
                flash('Error while saving image','danger')
                return redirect(request.url)
            try:
                os.remove("static/images/"+filename)
            except:
                pass
            flash('Image successfully uploaded','success')
            return redirect(request.url)
        else:
            flash('Wrong extention. Please select a valid file.','warning')
            return redirect(request.url)
    else:
        # In case of GET request
        return render_template('upload_image.html')


@app.route('/see_people', methods=['GET'])
def see_people():
    peoples = People.query.all()
    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
        blob_list = container_client.list_blobs()
        images = []
        for blob in blob_list:
            images.append(blob.name)
    except:
        flash('Error occured.','danger')
        return redirect(request.url)
    return render_template('see_people.html',peoples=peoples, images=images)


@app.route('/delete/<int:id>', methods=['GET'])
def delete(id):
    people_to_delete = People.query.get_or_404(id)
    try:
        db.session.delete(people_to_delete)
        db.session.commit()
        flash('Deleted Successfully','success')
        return redirect(url_for('see_people'))
    except:
        flash('Could not delete','danger')
        return redirect(url_for('see_people'))

@app.route('/create_people',methods=['GET','POST'])
def create_people():
    if request.method=="POST":
        name = request.form['name']
        state = request.form['state']
        salary = request.form['salary']
        grade = request.form['grade']
        room = request.form['room']
        telnum = request.form['telnum']
        picture = request.form['picture']
        keywords = request.form['keywords']
        people = People(name=name,state=state,salary=salary,grade=grade,room=room,telnum=telnum,picture=picture,keywords=keywords)
        try:
            db.session.add(people)
            db.session.commit()
        except:
            flash('There was a problem in adding the record','danger')
            return redirect(url_for('create_people'))
        flash('Record added successfully','success')
        return redirect(url_for('index'))
    return render_template('create_people.html')

@app.route('/update/<int:id>',methods=['GET','POST'])
def update(id):
    if request.method=="POST":
        id = request.form['id']
        people = People.query.get_or_404(id)
        people.name = request.form['name']
        people.state = request.form['state']
        people.salary = request.form['salary']
        people.grade = request.form['grade']
        people.room = request.form['room']
        people.telnum = request.form['telnum']
        people.picture = request.form['picture']
        people.keywords = request.form['keywords']
        try:
            db.session.commit()
            flash('Successfully updated the record','success')
            return redirect(url_for('index'))
        except:
            flash('Problem in updating the record','danger')
            return redirect(url_for('index'))
    people_to_update = People.query.get_or_404(id)
    return render_template('update_people.html',people=people_to_update,id=id)

@app.route('/search_name',methods=['GET','POST'])
def search_name():
    if request.method=="POST":
        names = request.form['name']
        names = names.capitalize()
        peoples = People.query.filter_by(name=names).all()
        try:
            blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
            container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
            blob_list = container_client.list_blobs()
            images = []
            for blob in blob_list:
                images.append(blob.name)
        except:
            flash('Error occured.','danger')
            return redirect(request.url)
        return render_template('search_name.html',show=True, peoples=peoples,images=images)
    return render_template('search_name.html',show=False)


#Route to show details of peoples with salary less than given
@app.route('/search_less', methods=['GET','POST'])
def search_less():
    if request.method=="POST":
        salaryy = float(request.form['salary'])
        peoples = People.query.filter(People.salary<=salaryy).all()
        try:
            blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
            container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
            blob_list = container_client.list_blobs()
            images = []
            for blob in blob_list:
                images.append(blob.name)
        except:
            flash('Error occured.','danger')
            return redirect(request.url)
        return render_template('search_less.html',show=True, peoples=peoples,images=images)
    return render_template('search_less.html',show=False)

@app.errorhandler(404)
@app.route("/404")
def page_not_found(error):
    return render_template('404.html', title='404')


@app.errorhandler(500)
@app.route("/500")
def server_error(error):
    return render_template('500.html', title='500')
    

if __name__=="__main__":
    app.run(debug=True)