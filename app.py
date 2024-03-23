from functools import wraps
from sqlalchemy.sql import func
from . import app, db
from flask import jsonify, request, make_response
from.models import Users, Funds
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from flask_cors import CORS
from flask import flash
from werkzeug.utils import secure_filename
import os
import json


UPLOAD_FOLDER = 'static/uploads'

# Vérifiez si le répertoire existe, sinon créez-le
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Ajoutez cette ligne

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No image selected for uploading"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('Image successfully uploaded and displayed below')
        
        # Enregistrement du chemin de l'image dans la base de données
        user_id = 1  # Remplacez cela par l'ID de l'utilisateur approprié
        user = Users.query.get(user_id)
        if user:
            user.profile_image = filename
            db.session.commit()
        
        return jsonify({"filename": filename}), 200
    else:
        return jsonify({"message": "Allowed image types are - png, jpg, jpeg, gif"}), 400

@app.route('/signup', methods=['POST'])
def signup():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No image selected for uploading"}), 400
    
    # Vérifier si les données de formulaire sont présentes dans request.form
    if 'firstName' not in request.form or 'lastName' not in request.form or 'email' not in request.form or 'password' not in request.form:
        return jsonify({"message": "Missing form data"}), 400
    
    # Récupérer les données de formulaire
    firstName = request.form['firstName']
    lastName = request.form['lastName']
    email = request.form['email']
    password = request.form['password']

    # Enregistrer le fichier sur le serveur
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # Hasher le mot de passe avant de l'enregistrer dans la base de données
        hashed_password = generate_password_hash(password)
        
        # Créer un nouvel utilisateur avec les données du formulaire et le nom de fichier
        new_user = Users(firstName=firstName, lastName=lastName, email=email, password=hashed_password, profile_image=filename)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": "User created successfully"}), 200
    else:
        return jsonify({"message": "Allowed image types are - png, jpg, jpeg, gif"}), 400

@app.route("/login",methods=["POST"])
def login():
    auth=request.json
    print("Auth reçu :", auth)
    if not auth or not auth.get("email") or not auth.get("password"):
        print("Informations d'identification manquantes")
        return make_response(
            jsonify({"message": "Proper credentials were not provided"}), 401
        )
    user = Users.query.filter_by(email=auth.get("email")).first()
    if not user:
        print("Utilisateur non trouvé")
        return make_response(
            jsonify({"message": "Please create an account"}), 401
        ) 
    if check_password_hash(user.password,auth.get('password')):
        token = jwt.encode({
            'id':user.id,
            'exp':datetime.utcnow() + timedelta(minutes=30)
        },
        "secret",
        "HS256"
        )
        print("Token généré :", token)
        return make_response(jsonify({'token':token}), 201)
    print("Informations d'identification incorrectes")
    return make_response(
        jsonify({'message': 'Please check your credentials'}), 401
    )



def token_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        token=None
        if 'Authorization' in request.headers:
            token = request.headers["Authorization"]
        if not token:
            return make_response({"message":"Token is missing "},401)
        
        try:
            data=jwt.decode(token,"secret",algorithms=["HS256"])
            current_user = Users.query.filter_by(id=data["id"]).first()
            print(current_user)
        except Exception as e :
            print(e)
            return make_response({
            "message":"token is invalid"},401)
        return f(current_user, *args,**kwargs)
    return decorated


@app.route("/funds", methods=["GET"])
@token_required
def getAllFunds(current_user):
    funds = Funds.query.filter_by(userId=current_user.id).all()
    totalSum = 0
    if funds:
        totalSum = Funds.query.with_entities(db.func.round(func.sum(Funds.amount), 2)).filter_by(userId=current_user.id).first()[0]
    return jsonify({
        "data": [fund.serialize for fund in funds],
        "sum": totalSum
    })

@app.route("/funds", methods=["POST"])
@token_required
def createFund(current_user):
    data = request.json
    amount = data.get("amount")

    if amount is not None:  # Assurez-vous que le montant n'est pas nul
        fund = Funds(
            amount=amount,
            userId=current_user.id
        )

        db.session.add(fund)
        db.session.commit()

        return make_response({"message": "Fonds créé avec succès", "fund": fund.serialize}, 201)
    else:
        return make_response({"message": "Montant invalide"}, 400)


@app.route("/funds/<id>",methods=["PUT"])
@token_required
def updateFund(current_user,id):
    try:
        funds =Funds.query.filter_by(userId=current_user.id,id=id).first()
        if funds == None:
            return make_response({"message":"unable to update"},409)
    
        data=request.json
        amount=data.get("amount")
        if amount:
            funds.amount =amount
        db.session.commit()
        return make_response({"message": funds.serialize},200) 
    except Exception as e:
        print(e)
        return make_response({"message":"Unable to process"},409)


@app.route("/funds/<id>",methods=["DELETE"])
@token_required
def deleteFund(current_user,id):
   try:
        fund =Funds.query.filter_by(userId=current_user.id,id=id).first()
        if fund == None:
            return make_response({"message":f"Fund with {id} not found"},404)
        db.session.delete(fund)
        db.session.commit()
        return make_response({"message": "Deleted"},202) 
   except Exception as e:
        print(e)
        return make_response({"message":"Unable to process"},409)

@app.route("/users", methods=["GET"])
def get_all_users():
    try:
        # Fetch all users
        users = Users.query.all()

        # Print debug information
        print("All Users:", users)

        # Commit the transaction explicitly
        db.session.commit()

        # Serialize user data
        serialized_users = [user.serialize() for user in users]  # Call the serialize method

        return jsonify({"data": serialized_users}), 200

    except Exception as e:
        print(e)
        # Rollback the transaction in case of an exception
        db.session.rollback()
        return make_response({"message": f"Error: {str(e)}"}, 500)


# ...

# Ajoutez cette route à votre code Flask
@app.route("/users/<int:user_id>/profile-image", methods=["PUT"])
def update_profile_image(user_id):
    try:
        user = Users.query.get(user_id)
        if not user:
            return make_response({"message": f"User with id {user_id} not found"}, 404)

        # Vérifiez si une image a été téléchargée dans la requête
        if 'file' not in request.files:
            return jsonify({"message": "No file part"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"message": "No image selected for uploading"}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Mettez à jour les autres attributs de l'utilisateur s'ils sont envoyés depuis le front-end
            user_data = request.form.get('user')
            if user_data:
                user_data = json.loads(user_data)
                user.firstName = user_data.get('firstName', user.firstName)
                user.lastName = user_data.get('lastName', user.lastName)
                user.email = user_data.get('email', user.email)
                # Ajoutez d'autres attributs si nécessaire

            # Mettez à jour le chemin de l'image de profil dans la base de données
            user.profile_image = filename
            db.session.commit()

            return jsonify({"message": "Profile image updated successfully"}), 200
        else:
            return jsonify({"message": "Allowed image types are - png, jpg, jpeg, gif"}), 400

    except Exception as e:
        print(e)
        db.session.rollback()
        return make_response({"message": "Unable to update profile image"}, 500)


@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    try:
        user = Users.query.get(user_id)
        if not user:
            return make_response({"message": f"User with id {user_id} not found"}, 404)

        db.session.delete(user)
        db.session.commit()

        return make_response({"message": "User deleted successfully"}, 200)

    except Exception as e:
        print(e)
        db.session.rollback()
        return make_response({"message": f"Unable to delete user: {str(e)}"}, 500)


@app.route('/user-profile', methods=['GET'])
@token_required
def get_user_profile(current_user):
    return jsonify({
        'firstName': current_user.firstName,
        'lastName': current_user.lastName,
        'profileImage': current_user.profile_image
    }), 200



if __name__ == '__main__':
    app.run(debug=True)