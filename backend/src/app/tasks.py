import os
import csv
import io
import json
import google.generativeai as genai
from celery_worker import celery_app
from app.database import SessionLocal
from app.models import User, Watchlist, Alert, Transaction, GraphAnalysisResult
from app import aml_rules, graph_analysis, ml_inference, advisor
from datetime import datetime, timedelta

# --- AI and Setup code ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')
HIGH_RISK_COUNTRIES = ["Iran", "North Korea", "Syria", "Yemen"]

# --- AI Helper Functions ---
def generate_kyc_summary(reasons: list) -> str:
    if not reasons: return "No issues found."
    prompt = f"Concisely summarize this compliance risk in one sentence: A user was flagged for these reasons: {', '.join(reasons)}."
    try:
        response = model.generate_content(prompt)
        return response.text.strip() if response.text else "AI summary could not be generated."
    except Exception as e:
        print(f"Error calling Gemini API for KYC summary: {e}")
        return "AI summary could not be generated."

def generate_graph_explanation(findings: dict) -> str:
    prompt_parts = ["You are a compliance investigator. Explain the primary risk of this network structure:"]
    has_findings = False
    if findings.get("cycles") and findings["cycles"][0]: 
        prompt_parts.append(f"- The entity is part of a {len(findings['cycles'][0])}-node money laundering cycle.")
        has_findings = True
    if findings.get("pagerank_score", 0) > 0.02: 
        prompt_parts.append(f"- The user is a financial hub (PageRank: {findings['pagerank_score']:.3f}).")
        has_findings = True
    if findings.get("betweenness_score", 0) > 0.1: 
        prompt_parts.append(f"- The user is a financial bridge (Betweenness: {findings['betweenness_score']:.2f}).")
        has_findings = True
    if not has_findings: 
        return "No significant graph patterns were detected."
    try:
        response = model.generate_content("\n".join(prompt_parts))
        return response.text.strip() if response.text else "AI explanation could not be generated."
    except Exception as e:
        print(f"Error calling Gemini API for graph explanation: {e}")
        return "AI explanation could not be generated."

def explain_risk_profile(evidence: dict) -> dict:
    if not evidence.get("alerts"): return {"explanation": "No open alerts; user appears low-risk."}
    evidence_str = json.dumps(evidence, indent=2)
    prompt = f"You are an expert financial crime investigator. Here is a user's dossier:\n```json\n{evidence_str}\n```\nSummarize the user's overall risk level, list the top 2-3 most severe risk factors, and recommend a next action (e.g., 'Continue Monitoring', 'Escalate for Investigation'). Be concise."
    try:
        response = model.generate_content(prompt)
        return {"explanation": response.text.strip()}
    except Exception as e:
        return {"error": f"AI risk explanation failed: {e}"}

def generate_sar_draft(evidence: dict) -> dict:
    if not evidence.get("alerts"): return {"sar_draft": "No suspicious activity found. SAR not warranted."}
    evidence_str = json.dumps(evidence, indent=2)
    prompt = f"You are a compliance officer. Draft a formal SAR narrative based on this evidence:\n```json\n{evidence_str}\n```\nUse sections for Introduction, Narrative of Suspicious Activity, and Conclusion. Be factual."
    try:
        response = model.generate_content(prompt)
        return {"sar_draft": response.text.strip()}
    except Exception as e:
        return {"error": f"SAR generation failed: {e}"}

# --- Core Celery Tasks ---

@celery_app.task
def run_kyc_check(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return
        reasons = []
        if user.country in HIGH_RISK_COUNTRIES: reasons.append(f"from high-risk country: {user.country}")
        watchlist_entry = db.query(Watchlist).filter(Watchlist.name.ilike(f"%{user.full_name}%")).first()
        if watchlist_entry: reasons.append("matches watchlist")
        if reasons:
            ai_summary = generate_kyc_summary(reasons)
            db.add(Alert(user_id=user.id, alert_type="KYC_FLAG", message="; ".join(reasons), ai_summary=ai_summary, status="OPEN"))
            db.commit()
    finally: db.close()

@celery_app.task
def analyze_transaction_patterns(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return
        payment_reason = aml_rules.check_structuring_by_payment(db, user)
        if payment_reason:
            if not db.query(Alert).filter(Alert.user_id==user.id, Alert.alert_type=="AML_STRUCTURING_PAYMENT").first():
                db.add(Alert(user_id=user.id, alert_type="AML_STRUCTURING_PAYMENT", message=payment_reason, ai_summary="User sent multiple payments under reporting thresholds."))
        deposit_reason = aml_rules.check_structuring_by_deposit(db, user)
        if deposit_reason:
            if not db.query(Alert).filter(Alert.user_id==user.id, Alert.alert_type=="AML_STRUCTURING_DEPOSIT").first():
                db.add(Alert(user_id=user.id, alert_type="AML_STRUCTURING_DEPOSIT", message=deposit_reason, ai_summary="User received multiple deposits, suggesting use as a mule account."))
        db.commit()
    finally: db.close()

@celery_app.task
def score_transaction_anomaly(transaction_id: int):
    db = SessionLocal()
    try:
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction: return
        scores = ml_inference.score_transaction(transaction.amount)
        if scores["anomaly"]:
            message = (f"Anomalous transaction of ₹{transaction.amount:,.2f} detected. (I-Forest:{scores['iso_forest_score']:.2f}, AE-Error:{scores['autoencoder_error']:.4f})")
            db.add(Alert(user_id=transaction.to_user_id, alert_type="ML_ANOMALY", message=message, ai_summary="ML model detected a significant deviation from normal activity.", status="OPEN"))
            db.commit()
    finally: db.close()



@celery_app.task(bind=True)
def run_graph_analysis(self, user_id: int):
    """
    This is the final, corrected version.
    It correctly fetches the job record and updates it.
    """
    job_id = self.request.id
    db = SessionLocal()
    
    # Create the job record first, so the frontend can find it.
    job_record = GraphAnalysisResult(job_id=job_id, user_id=user_id, status="RUNNING")
    db.add(job_record)
    db.commit()

    try:
        analysis = graph_analysis.build_and_analyze_graph(db, user_id)
        
        # --- THIS IS THE FIX ---
        # We must fetch the record again within the same session to update it.
        job_to_update = db.query(GraphAnalysisResult).filter(GraphAnalysisResult.job_id == job_id).one()

        if analysis.get("error"):
            job_to_update.status = "FAILED"
            job_to_update.findings = {"error": analysis["error"]}
        else:
            job_to_update.status = "COMPLETED"
            job_to_update.findings = analysis["findings"]
            job_to_update.plot_data = analysis["plot_data"]
            job_to_update.ai_explanation = generate_graph_explanation(analysis["findings"])
        
        job_to_update.completed_at = datetime.now()
        
        # Commit the final state to the database
        db.commit()
        
        # This return value is for Celery's own backend, it's good practice.
        return {"status": job_to_update.status, "job_id": job_id}
        
    except Exception as e:
        db.rollback()
        # If any error occurs, we still try to mark the job as FAILED.
        job_to_fail = db.query(GraphAnalysisResult).filter(GraphAnalysisResult.job_id == job_id).one_or_none()
        if job_to_fail:
            job_to_fail.status = "FAILED"
            job_to_fail.findings = {"error": str(e)}
            job_to_fail.completed_at = datetime.now()
            db.commit()
        print(f"Graph analysis task {job_id} failed with an unhandled exception: {e}")
        raise
    finally:
        db.close()




@celery_app.task(bind=True)
def process_uploaded_csv(self, file_content_str: str):
    db = SessionLocal()
    try:
        print(f"Starting BATCH CSV processing for job {self.request.id}")
        file_stream = io.StringIO(file_content_str)
        reader = csv.DictReader(file_stream)
        rows = list(reader)

        all_accounts_in_csv = {row.get('Debit_Account') for row in rows if row.get('Debit_Account')} | \
                              {row.get('Credit_Account') for row in rows if row.get('Credit_Account')}
        existing_users = db.query(User).filter(User.full_name.in_(all_accounts_in_csv)).all()
        existing_user_names = {u.full_name for u in existing_users}
        user_map = {u.full_name: u.id for u in existing_users}
        new_user_names = all_accounts_in_csv - existing_user_names
        users_to_create = [User(full_name=name, email=f"{name.lower().replace(' ', '_')}@bank.com", country="Unknown") for name in new_user_names]
        
        if users_to_create:
            db.bulk_save_objects(users_to_create)
            db.commit()
            print(f"Bulk created {len(users_to_create)} new users.")
            newly_created_users = db.query(User).filter(User.full_name.in_(new_user_names)).all()
            for user in newly_created_users:
                user_map[user.full_name] = user.id
        
        transactions_to_create = []
        for row in rows:
            from_user_id = user_map.get(row.get('Debit_Account'))
            to_user_id = user_map.get(row.get('Credit_Account'))
            if not from_user_id or not to_user_id: continue
            transactions_to_create.append(Transaction(from_user_id=from_user_id, to_user_id=to_user_id, amount=float(row['Amount']), currency=row.get('Currency', 'INR'), description=row.get('Description', 'N/A')))
        
        if transactions_to_create:
            db.bulk_save_objects(transactions_to_create)
            db.commit()
            print(f"Bulk inserted {len(transactions_to_create)} transactions.")

        print("Starting BATCH analysis...")
        all_affected_users = db.query(User).filter(User.id.in_(user_map.values())).all()
        
        alerts_to_create = []
        for user in all_affected_users:
            payment_reason = aml_rules.check_structuring_by_payment(db, user)
            if payment_reason: alerts_to_create.append(Alert(user_id=user.id, alert_type="AML_STRUCTURING_PAYMENT", message=payment_reason, ai_summary="User sent multiple payments under reporting thresholds."))
            deposit_reason = aml_rules.check_structuring_by_deposit(db, user)
            if deposit_reason: alerts_to_create.append(Alert(user_id=user.id, alert_type="AML_STRUCTURING_DEPOSIT", message=deposit_reason, ai_summary="User received multiple deposits, suggesting use as a mule account."))

        all_new_transactions = db.query(Transaction).filter(Transaction.to_user_id.in_(user_map.values())).all()
        if ml_inference.load_models_lazily():
            for tx in all_new_transactions:
                scores = ml_inference.score_transaction(tx.amount)
                if scores["anomaly"]:
                    message = f"Anomalous transaction of ₹{tx.amount:,.2f} detected. (I-Forest:{scores['iso_forest_score']:.2f}, AE-Error:{scores['autoencoder_error']:.4f})"
                    alerts_to_create.append(Alert(user_id=tx.to_user_id, alert_type="ML_ANOMALY", message=message, ai_summary="ML model detected a significant deviation from normal activity."))

        if alerts_to_create:
            db.bulk_save_objects(alerts_to_create)
            db.commit()
            print(f"BATCH analysis complete. Created {len(alerts_to_create)} new alerts.")

        return f"Processing complete. {len(transactions_to_create)} transactions ingested."
    except Exception as e:
        db.rollback()
        print(f"CSV Processing task FAILED: {e}")
        raise
    finally:
        db.close()

# --- NEW TASKS FOR THE AI ADVISOR ---
@celery_app.task
def explain_risk_task(user_id: int):
    """A Celery task that synthesizes evidence and gets an AI risk explanation."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return {"error": "User not found."}
        evidence = advisor.synthesize_user_evidence(db, user)
        return explain_risk_profile(evidence)
    finally:
        db.close()

@celery_app.task
def generate_sar_task(user_id: int):
    """A Celery task that synthesizes evidence and generates a SAR draft."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return {"error": "User not found."}
        evidence = advisor.synthesize_user_evidence(db, user)
        return generate_sar_draft(evidence)
    finally:
        db.close()