from flask import Flask
from flask_cors import CORS, cross_origin
from db_api import DB_interface
from flask import request

app = Flask(__name__)
CORS(app, support_credentials=True)
dbi = DB_interface()

@app.route('/')
def index():
    return "Hi!"

@app.route("/getRegions")
def getRegions():
    result = dbi.get_regions()

    return {"responce": result}

@app.route("/addUser", methods=["GET", "POST"])
def addUser():
    name = request.form["user_name"]
    region = request.form["user_region"]

    if dbi.create_new_user(name, region):
        return {"responce": "OK"}
    else:
        return {"error": "NOT OK"}

@app.route("/getUsers", methods=["GET"])
def getUsers():
    ids = None
    if "ids" in request.values:
        ids = request.values["ids"].split(",")
    
    return {"responce": dbi.get_users(ids=ids)}

@app.route("/getCategories")
def getCategories():
    result = dbi.get_categories()

    return {"responce": result}

@app.route("/getByCategory", methods=["GET"])
def getByCategory():
    cat = request.values["cat"]
    tr = request.values["tr"]

    result = dbi.get_positions_by_category(cat, tr)

    return {"responce": result}

@app.route("/addVisited", methods=["GET"])
def addVisited():
    posID = request.values["posID"]
    userID = request.values["userID"]

    dbi.addVisited(userID, posID)
    dbi.ratingIncrement(userID, posID)
    return {"a": posID, "b": userID}

@app.route("/addToBasket", methods=["GET"])
def addToBasket():
    posID = request.values["posID"]
    userID = request.values["userID"]

    dbi.addToBasket(userID, posID)
    dbi.ratingIncrement(userID, posID)
    return {"a": posID, "b": userID}

@app.route("/kupi", methods=["GET"])
def kupi():
    userID = request.values["userID"]

    dbi.kupi(userID)
    return {"b": userID}

@app.route("/recomendationsFor", methods=["GET"])
def recomendationsFor():
    userID = request.values["userID"]

    return dbi.getRecomendationData(int(userID))

app.run(debug = True, host="0.0.0.0")