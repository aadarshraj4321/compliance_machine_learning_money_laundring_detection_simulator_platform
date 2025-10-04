from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from app import database, models
from app.tasks import process_uploaded_csv

router = APIRouter(
    prefix="/ingest",
    tags=["Ingestion"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload-csv", status_code=202, response_model=dict)
async def upload_transaction_csv(file: UploadFile = File(...)):
    """
    Accepts a CSV file and starts a background job to process it.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type.")

    try:
        file_content = await file.read()
        file_content_str = file_content.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {e}")

    task = process_uploaded_csv.delay(file_content_str)
    
    return {"message": "File upload successful. Processing has started in the background.", "job_id": task.id}

@router.post("/clear-all-data", status_code=200, response_model=dict)
def clear_all_data_endpoint(db: Session = Depends(get_db)):
    """
    Deletes all data from the database for a clean start.
    """
    try:
        print("Received request to clear all data...")
        # The order is critical
        db.query(models.GraphAnalysisResult).delete()
        db.query(models.Alert).delete()
        db.query(models.Transaction).delete()
        db.query(models.Watchlist).delete()
        db.query(models.User).delete()
        db.commit()
        print("All data cleared successfully.")
        return {"message": "All investigation data has been cleared."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {e}")