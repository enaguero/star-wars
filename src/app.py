"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, People
#from models import Person
import requests
import json 

app = Flask(__name__)
app.url_map.strict_slashes = False

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

# Handle/serialize errors like a JSON object
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints
@app.route('/')
def sitemap():
    return generate_sitemap(app)


@app.route('/import_people')
def import_people():
    res = requests.get('https://www.swapi.tech/api/people/')
    response = json.loads(res.text)
    
    data = response["results"]
    for person_data in data:
        person_res = requests.get(person_data["url"])
        person_json = json.loads(person_res.text)
        result = person_json['result']
        properties = result['properties']
        p = People(external_uid = result['uid'], name = properties['name'], birth_year= properties['birth_year'])
        db.session.add(p)

    db.session.commit()

    return jsonify({"msg": "All the people was added"}), 200

@app.route('/user', methods=['GET'])
def handle_hello():

    response_body = {
        "msg": "Hello, this is your GET /user response "
    }

    return jsonify(response_body), 200

@app.route('/people', methods=['GET'])
def handle_people():
    people = People.query.all()
    # https://stackoverflow.com/questions/7102754/jsonify-a-sqlalchemy-result-set-in-flask
    return jsonify([p.serialize() for p in people]), 200

@app.route('/people/<int:person_id>', methods=['PUT', 'GET'])
def handle_person(person_id):
    # Potential reference : https://stackoverflow.com/questions/54472696/failed-to-decode-json-object-expecting-value-line-1-column-1-char-0
    if request.method == 'GET':
        person = People.query.get(person_id)
        return jsonify(person.serialize()), 200
    
    if request.method == 'PUT':
        person = People.query.get(person_id)
        body = request.get_json()
        person.username = body.username
        db.session.commit()
        return jsonify(person.serialize()), 200
    
    return "Invalid Method", 404

# this only runs if `$ python src/app.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
