from fastapi import FastAPI, Depends, HTTPException, status, security
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, Session
from typing import List
from sqlalchemy.ext.declarative import declarative_base
from fastapi.templating import Jinja2Templates
import uvicorn
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from fastapi.responses import JSONResponse
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder
from fpdf import FPDF



# Connexion à la base de données MySQL
DATABASE_URL = "mysql+pymysql://root:@localhost/test"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

templates = Jinja2Templates(directory="templates")

# Définition du modèle SQLAlchemy
Base = declarative_base()
class Expense(Base):
    __tablename__ = 'expenses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255))
    amount = Column(Float)
    category = Column(String(255))

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255))
    password = Column(String(255))
    role = Column(String(255))

# Création de la base de données et des tables
Base.metadata.create_all(bind=engine)

# Modèles Pydantic
class ExpenseCreate(BaseModel):
    title: str
    amount: float
    category: str

class ExpenseUpdate(BaseModel):
    title: str
    amount: float
    category: str

class ExpenseResponse(BaseModel):
    id: int
    title: str
    amount: float
    category: str

#class PDF(FPDF):
    #    def titles(self, title):
    #    self.set_xy(0.0, 0.0)
    #    self.set_font('Arial', 'B' 16)
    #    self.set_text_color(220, 50, 50)
    #    self.cell(w=210.0, h=40.0, align='C', txt=title, border=0)

    #def texts(self, description):
        #self.set_xy(10.0, 40.0)
        #self.set_text_color(76.0, 32.0, 250.0)
        #self.set_font('Arial', '', 12)

# Dépendance pour la session SQLAlchemy
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Fonctions utilitaires pour l'authentification
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Création de l'instance FastAPI
app = FastAPI()

# Sécurité basique HTTP
security = HTTPBasic()


# Fonction d'authentification
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = "Adam"  # Remplacez par le nom d'utilisateur correct
    correct_password = "Taka"  # Remplacez par le mot de passe correct
    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

# Routes API
@app.get("/", response_class=JSONResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/expenses/", response_model=ExpenseResponse)
def create_expense(expense: ExpenseCreate, db: SessionLocal = Depends(get_db)):
    new_expense = Expense(**expense.dict())
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    return jsonable_encoder(new_expense)

@app.get("/expenses/", response_model=List[ExpenseResponse])
def get_expenses(db: SessionLocal = Depends(get_db)):
    expenses = db.query(Expense).all()
    return jsonable_encoder(expenses)

@app.get("/expenses/{expense_id}", response_model=ExpenseResponse)
def get_expense(expense_id: int, db: SessionLocal = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return jsonable_encoder(expense)

@app.put("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(expense_id: int, expense: ExpenseUpdate, db: SessionLocal = Depends(get_db)):
    updated_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not updated_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    for field, value in expense.dict().items():
        setattr(updated_expense, field, value)
    db.commit()
    db.refresh(updated_expense)
    return jsonable_encoder(updated_expense)

@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, db: SessionLocal = Depends(get_db)):
    deleted_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not deleted_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(deleted_expense)
    db.commit()
    return {"message": "Expense deleted"}

def create_invoice_pdf(filename, invoice_id, title, amount, category, description, tvamount):
    tvamount = amount//20
    tvamount = tvamount*100

    # Création d'un nouveau fichier PDF
    c = canvas.Canvas(filename, pagesize=A4)

    # Ajout du numéro de facture
    c.setFont("Helvetica", 17)
    c.drawString(50, 750, f"Facture numéro : {invoice_id}")

    # Ajout du titre, montant, catégorie et description
    c.setFont("Helvetica", 10)
    c.drawString(50, 700, f"Titre : {title}")
    c.drawString(50, 680, f"Montant : {amount} dont 20% de TVA soit : {tvamount})")
    c.drawString(50, 660, f"Montant sans TVA : {tvamount})")
    c.drawString(50, 640, f"Catégorie : {category}")
    c.drawString(50, 620, "Informations :")
    text_lines = description.split("\n")
    y = 620  # Position verticale initiale pour la description
    for line in text_lines:
        c.drawString(70, y, line)
        y -= 20

    # Enregistrement du document PDF
    c.save()

@app.get("/invoices/{invoice_id}")
def generate_invoice(invoice_id: int, db: SessionLocal = Depends(get_db)):
    # ... récupérer les informations de la facture (numéro et description) ...
    expense = db.query(Expense).filter(Expense.id == invoice_id).first()

    title = expense.title
    category = expense.category
    amount = expense.amount
    description = "Les frais forfaitaires doivent être justifiés par une facture acquittée faisant apparaître le montant de la TVA. \nCes documents ne sont pas à joindre à l’état de frais mais doivent être conservés pendant trois années. \nIls peuvent être contrôlés par le délégué régional ou le service comptable."

    # Générer le nom de fichier du PDF
    filename = f"invoice_{invoice_id}.pdf"

    def create_invoice_pdf(filename, invoice_id, title, amount, category, description):
        # Création d'un nouveau fichier PDF
        c = canvas.Canvas(filename, pagesize=A4)

        # Ajout du numéro de facture
        c.setFont("Helvetica", 12)
        c.drawString(50, 750, f"Facture numéro : {invoice_id}")

        # Ajout du titre, montant, catégorie et description
        c.setFont("Helvetica", 10)
        c.drawString(50, 700, f"Titre : {title}")
        c.drawString(50, 680, f"Montant : {amount}")
        c.drawString(50, 660, f"Catégorie : {category}")
        c.drawString(50, 640, "Description :")
        text_lines = description.split("\n")
        y = 620  # Position verticale initiale pour la description
        for line in text_lines:
            c.drawString(70, y, line)
            y -= 20

        # Enregistrement du document PDF
        c.save()

    # Créer le PDF de la facture avec la description
    create_invoice_pdf(filename, invoice_id, title, amount, category, description)

    # Renvoyer le fichier PDF en tant que réponse de l'API
    return FileResponse(filename, media_type="application/pdf", filename=filename)

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    uvicorn.run(app, host="0.0.0.0", port=8000)
