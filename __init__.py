from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
CORS(app)
db = SQLAlchemy()
migrate = Migrate(app, db)

# Mettez le mot de passe correct s'il y en a un, sinon laissez-le vide.
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://user:postgres@localhost:5434/postgres"

# Initialise l'application Flask avec l'instance SQLAlchemy
db.init_app(app)
