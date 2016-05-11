from flask import Flask, render_template,request,url_for,redirect, flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from company60 import Base, Company, Employee, User
from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Company App"

#Connect to database and create database session
engine = create_engine('sqlite:///company60.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create anti-forgery state token
@app.route('/login')
def showLogin():
    # A forger will have to guess this 32 character token if we wants to make requests on the user's behalf
    # Make sure that the user and login_session have the same state value
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = json.loads(answer.text)
    login_session['provider'] = 'google'
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email']) 
    if user_id :
        name = getUserName(login_session['email']) 
        login_session['username'] = name
    if not user_id :
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    

    output = ''
    output += '<h1>Welcome, '
    '''output += user.name '''
    output += login_session['username'] 
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# create a new user
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

# get user information
def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

#get user ID
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

def getUserName(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.name
    except:
        return None 


@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response
@app.route('/disconnect')
def disconnect():
  
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['provider']
            flash("you have successfully logged out ")
        else:
            flash("logged in with unknown provider")
    else:
        flash("you were not logged in to begin with")
    return redirect('/')

#JSON endpoint for all employees in a company
@app.route('/company/<int:company_id>/employees/JSON')
def viewEmpJSON(company_id):
    company = session.query(Company).filter_by(id=company_id).one()
    employee = session.query(Employee).filter_by(company_id=company_id).all()
    return jsonify(employees=[i.serialize for i in employee])

# JSON endpoint for all companies
@app.route('/companies/JSON')
def companiesJSON():
    company = session.query(Company)
    return jsonify(companies=[i.serialize for i in company])

# JSON endpoint for one employee
@app.route('/company/<int:company_id>/employees/<int:employee_id>/JSON')
def employeesJSON(company_id, employee_id):
    employee = session.query(Employee).filter_by(company_id= company_id, id=employee_id).one()
    return jsonify(employees= employee.serialize)

 # Show all companies   
@app.route('/')
@app.route('/companies')
def companies():
    company = session.query(Company)
    if 'username' not in login_session:
        return render_template('publiccompanies.html', company=company)
    else:
        return render_template('companies.html', company=company)

@app.route('/users')
def users():
    user = session.query(User)
    return render_template('users.html', user=user) 


# Create new company
@app.route('/company/new', methods=['GET', 'POST'])
def newCompany(): 
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newCompany = Company(name=request.form['name'], user_id=login_session['user_id'] )
        session.add(newCompany)
        session.commit()
        flash("New company added!")
        return redirect(url_for('companies'))
    else:
        return render_template('newCompany.html')

# Edit a company
@app.route('/company/<int:company_id>/edit', methods=['GET','POST'])
def editCompany(company_id):
    editedItem = session.query(Company).filter_by(id=company_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedItem.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this company. Please create your own company in order to edit.');}</script><body onload='myFunction()''>"    
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        session.add(editedItem)
        session.commit()
        flash("Company details edited!")
        return redirect(url_for('companies', company_id=company_id))
    else:
        return render_template('editCompany.html', company_id=company_id, item = editedItem)
# Delete a company
@app.route('/company/<int:company_id>/delete', methods=['GET','POST'])
def deleteCompany(company_id):
    itemToDelete = session.query(Company).filter_by(id=company_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if itemToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this company. Please create your own company in order to delete.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("Company deleted!")
        return redirect(url_for('companies', company_id=company_id))
    else:
        return render_template('deleteCompany.html', item=itemToDelete)
    
    
# View employees in a company
@app.route('/company/<int:company_id>/employees')
def viewEmp(company_id):
    company = session.query(Company).filter_by(id=company_id).one()
    creator = getUserInfo(company.user_id)
    employee = session.query(Employee).filter_by(company_id=company_id).all()
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicemployees.html', company = company, employee= employee, creator=creator)
    else:
        return render_template('employee.html', company = company, employee= employee, creator=creator)

    
# create new employees
@app.route('/company/<int:company_id>/employees/new', methods=['GET', 'POST'])
def newEmployee(company_id):
    if 'username' not in login_session:
        return redirect('/login')
    company = session.query(Company).filter_by(id=company_id).one()
    if login_session['user_id'] != company.user_id:
        return "<script>function myFunction() {alert('You are not authorized to add employees to this company. Please create your own company in order to add employees.');}</script><body onload='myFunction()''>"   
    if request.method == 'POST':
        newEmployee = Employee(
            name=request.form['name'], doj = request.form['doj'], department = request.form['department'], email = request.form['email'], company_id=company_id)
        session.add(newEmployee)
        session.commit()
        flash("New Employee created!")
        return redirect(url_for('viewEmp', company_id=company_id))
    else:
        return render_template('newEmployee.html', company_id=company_id)

# Edit employees
@app.route('/company/<int:company_id>/employees/<int:employee_id>/edit', methods = ['GET','POST'])
def editEmp(company_id, employee_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Employee).filter_by(id=employee_id).one()
    company = session.query(Company).filter_by(id=company_id).one()
    if login_session['user_id'] != company.user_id:
        return "<script>function myFunction() {alert('You are not authorized to edit employees of this company. Please create your own company in order to edit employees.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['doj']:
            editedItem.doj = request.form['doj']
        if request.form['department']:
            editedItem.department = request.form['department']
        if request.form['email']:
            editedItem.email = request.form['email']
        session.add(editedItem)
        session.commit()
        flash("Employee details edited!")
        return redirect(url_for('viewEmp', company_id=company_id))
    else:
        return render_template('editEmployee.html', company_id=company_id, employee_id=employee_id, item = editedItem)


# delete employees
@app.route('/company/<int:company_id>/employees/<int:employee_id>/delete', methods = ['GET','POST'])
def deleteEmp(company_id, employee_id):
    if 'username' not in login_session:
        return redirect('/login')
    company = session.query(Company).filter_by(id=company_id).one()
    itemToDelete = session.query(Employee).filter_by(id=employee_id).one()
    if login_session['user_id'] != company.user_id:
        return "<script>function myFunction() {alert('You are not authorized to delete employees from this company. Please create your own company in order to delete employees.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("Employee deleted!")
        return redirect(url_for('viewEmp', company_id=company_id))
    else:
        return render_template('deleteEmployee.html', item=itemToDelete)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)