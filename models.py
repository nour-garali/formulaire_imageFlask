from . import db
from sqlalchemy.sql import func

class Users(db.Model):
    __tablename__ = "Users"
    id = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String(100), nullable=False)
    lastName = db.Column(db.String(200), nullable=False)
    password = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    profile_image = db.Column(db.String(250))  # Nouveau champ pour le chemin de l'image
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    funds = db.relationship('Funds', backref="user")
   
    def __repr__(self):
        return f'<User {self.firstName} {self.id}>'

    def serialize(self):
        return {
            'id': self.id,
            'firstName': self.firstName,
            'lastName': self.lastName,
            'email': self.email,
            'profile_image': self.profile_image,  # Inclure le chemin de l'image dans la sérialisation
            'created_at': self.created_at
        }

class Funds(db.Model):
    __tablename__ = "Funds"
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(10, 2))
    userId = db.Column(db.Integer, db.ForeignKey("Users.id"))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    def serialize(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "created_at": self.created_at,
        }

