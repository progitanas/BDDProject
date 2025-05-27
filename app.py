from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

# Configuration
app.secret_key = 'cle_secrete_pour_session_urgence_medicale'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hopital_urgence.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ------------------ MODELES ------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    fiche_medicale = db.Column(db.Text)
    specialite = db.Column(db.String(100))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'prenom': self.prenom,
            'email': self.email,
            'role': self.role,
            'fiche_medicale': self.fiche_medicale,
            'specialite': self.specialite
        }

class Urgence(db.Model):
    id_urgence = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    medecin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    commentaire = db.Column(db.Text, nullable=False)
    statut = db.Column(db.String(20), default='urgente')
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_assignation = db.Column(db.DateTime)
    date_resolution = db.Column(db.DateTime)

    patient = db.relationship('User', foreign_keys=[patient_id], backref='urgences_patient')
    medecin = db.relationship('User', foreign_keys=[medecin_id], backref='urgences_medecin')

    def to_dict(self):
        return {
            'id_urgence': self.id_urgence,
            'patient_id': self.patient_id,
            'medecin_id': self.medecin_id,
            'commentaire': self.commentaire,
            'statut': self.statut,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
            'date_assignation': self.date_assignation.isoformat() if self.date_assignation else None,
            'date_resolution': self.date_resolution.isoformat() if self.date_resolution else None,
            'patient_nom': self.patient.nom if self.patient else '',
            'patient_prenom': self.patient.prenom if self.patient else '',
            'medecin_nom': self.medecin.nom if self.medecin else '',
            'medecin_prenom': self.medecin.prenom if self.medecin else ''
        }

class Patient(db.Model):
    id_patient = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    date_naissance = db.Column(db.Date)
    sexe = db.Column(db.String(10))
    mode_arrivee = db.Column(db.String(50))

    def to_dict(self):
        return {
            'id_patient': self.id_patient,
            'nom': self.nom,
            'prenom': self.prenom,
            'date_naissance': self.date_naissance.strftime("%Y-%m-%d") if self.date_naissance else None,
            'sexe': self.sexe,
            'mode_arrivee': self.mode_arrivee
        }

# ------------------ ROUTES ------------------

@app.route('/')
def index():
    return render_template('auth.html')

@app.route('/auth')
def auth():
    return render_template('auth.html')

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')

        if User.query.filter_by(email=email).first():
            return jsonify({'message': 'Email déjà utilisé'}), 400

        user = User(nom='Nom', prenom='Prénom', email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['user_role'] = user.role
        session['user_email'] = user.email

        return jsonify({'message': 'Compte créé avec succès'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Erreur lors de la création du compte: {str(e)}'}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')

        user = User.query.filter_by(email=email, role=role).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_email'] = user.email
            return jsonify({'message': 'Connexion réussie'}), 200
        else:
            return jsonify({'message': 'Email, mot de passe ou rôle invalide'}), 400

    except Exception as e:
        return jsonify({'message': f'Erreur lors de la connexion: {str(e)}'}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth'))

@app.route('/patient/dashboard')
def dashboard_patient():
    if 'user_id' not in session or session.get('user_role') != 'patient':
        return redirect(url_for('auth'))
    return render_template('dashbords_patients.html')

@app.route('/medecin/dashboard')
def dashboard_medecin():
    if 'user_id' not in session or session.get('user_role') != 'medecin':
        return redirect(url_for('auth'))
    return render_template('dashbords_médecins.html')

@app.route('/admin/patients')
def admin_patients():
    return render_template('index.html')

# ------------------ INITIALISATION ------------------

def init_db():
    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            medecin = User(nom="Martin", prenom="Jean", email="medecin@test.com", role="medecin", specialite="Urgentiste")
            medecin.set_password("123456")
            db.session.add(medecin)

            patient = User(nom="Dupont", prenom="Alice", email="patient@test.com", role="patient", fiche_medicale="Aucun antécédent particulier")
            patient.set_password("123456")
            db.session.add(patient)
            try:
                db.session.commit()
                print("Utilisateurs de test créés")
            except Exception as e:
                db.session.rollback()
                print(f"Erreur : {e}")

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
