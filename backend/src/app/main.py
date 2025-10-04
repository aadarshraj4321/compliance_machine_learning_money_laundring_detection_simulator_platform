from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app import models, database, ingestion, advisor
from celery_worker import celery_app


app = FastAPI(title="AI-Powered Regulatory Compliance Simulator")

app.include_router(ingestion.router)

# Middleware for CORS
origins = ["http://localhost:3000", "http://localhost:5173"]
app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins, 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"],
)

# --- Pydantic Schemas (Correctly Formatted) ---
class TransactionCreate(BaseModel):
    amount: float
    description: str

class TransactionSchema(BaseModel):
    id: int
    amount: float
    currency: str
    timestamp: datetime
    description: str
    class Config:
        from_attributes = True

class UserSchema(BaseModel):
    id: int
    full_name: str
    email: str
    country: str
    created_at: datetime
    class Config:
        from_attributes = True

class AlertSchema(BaseModel):
    id: int
    alert_type: str
    message: str
    ai_summary: Optional[str] = None
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

class UserDetailSchema(UserSchema):
    transactions: List[TransactionSchema] = []
    class Config:
        from_attributes = True

# --- Dependency ---
def get_db():
    db = database.SessionLocal()
    try: 
        yield db
    finally: 
        db.close()

# --- API Endpoints ---
@app.get("/api/v1/health")
def health_check(): 
    return {"status": "ok"}

@app.get("/api/v1/users", response_model=List[UserSchema])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.id).offset(skip).limit(limit).all()

@app.get("/api/v1/users/{user_id}", response_model=UserDetailSchema)
def read_user_details(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/api/v1/users/{user_id}/transactions", response_model=List[TransactionSchema])
def read_user_transactions(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    return db.query(models.Transaction).filter(models.Transaction.to_user_id == user_id).order_by(models.Transaction.timestamp.desc()).all()

@app.get("/api/v1/users/{user_id}/alerts", response_model=List[AlertSchema])
def get_user_alerts_endpoint(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail=f"User {user_id} not found.")
    return db.query(models.Alert).filter(models.Alert.user_id == user_id).order_by(models.Alert.created_at.desc()).all()

@app.post("/api/v1/users/{user_id}/transactions", status_code=201, response_model=TransactionSchema)
def create_transaction_for_user_endpoint(user_id: int, transaction: TransactionCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    external_user = db.query(models.User).filter(models.User.email == "external@system.com").first()
    if not external_user: raise HTTPException(status_code=500, detail="External System user not found. Please run the seeder.")
    db_transaction = models.Transaction(amount=transaction.amount, description=transaction.description, to_user_id=user_id, from_user_id=external_user.id)
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    celery_app.send_task("app.tasks.analyze_transaction_patterns", args=[user_id])
    celery_app.send_task("app.tasks.score_transaction_anomaly", args=[db_transaction.id])
    return db_transaction

# --- ON-DEMAND & ADVISOR ENDPOINTS ---
@app.post("/api/v1/users/{user_id}/run-kyc-check", status_code=202, response_model=dict)
def trigger_kyc_check_endpoint(user_id: int):
    task = celery_app.send_task("app.tasks.run_kyc_check", args=[user_id])
    return {"job_id": task.id}

@app.post("/api/v1/users/{user_id}/run-graph-analysis", status_code=202, response_model=dict)
def trigger_graph_analysis_endpoint(user_id: int):
    task = celery_app.send_task("app.tasks.run_graph_analysis", args=[user_id])
    return {"job_id": task.id}

@app.post("/api/v1/advisor/explain-risk/{user_id}", status_code=202, response_model=dict)
def trigger_explain_risk_endpoint(user_id: int):
    task = celery_app.send_task("app.tasks.explain_risk_task", args=[user_id])
    return {"job_id": task.id}

@app.post("/api/v1/advisor/generate-sar/{user_id}", status_code=202, response_model=dict)
def trigger_generate_sar_endpoint(user_id: int):
    task = celery_app.send_task("app.tasks.generate_sar_task", args=[user_id])
    return {"job_id": task.id}

@app.get("/api/v1/results/{job_id}", response_model=dict)
def get_task_result(job_id: str, db: Session = Depends(get_db)):
    # 1. Try GraphAnalysisResult first
    graph_result = db.query(models.GraphAnalysisResult).filter(models.GraphAnalysisResult.job_id == job_id).first()
    if graph_result:
        if graph_result.status not in ["COMPLETED", "FAILED"]:
            return {"status": graph_result.status}
        return {
            "status": "SUCCESS",
            "result_type": "graph",
            "result": {
                "plot_data": graph_result.plot_data,
                "ai_explanation": graph_result.ai_explanation,
            }
        }

    # 2. Fallback: Check Celery result backend
    task_result = celery_app.AsyncResult(job_id)

    if task_result.status == "PENDING":
        return {"status": "PENDING", "result_type": "generic"}

    if task_result.ready():
        return {
            "status": task_result.state,
            "result_type": "generic",
            "result": task_result.result,
        }

    return {"status": "UNKNOWN", "result_type": "generic"}
