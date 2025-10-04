from sqlalchemy.orm import Session
from app.models import User, Alert
from typing import Dict, Any

def synthesize_user_evidence(db: Session, user: User) -> Dict[str, Any]:
    """
    Gathers all alerts and key user info into a single structured dictionary.
    """
    alerts = db.query(Alert).filter(Alert.user_id == user.id).order_by(Alert.created_at.desc()).all()
    
    evidence = {
        "user_profile": {
            "id": user.id,
            "full_name": user.full_name,
            "country": user.country,
            "member_since": user.created_at.isoformat()
        },
        "alerts": [
            {
                "type": alert.alert_type,
                "reason": alert.message,
                "ai_summary": alert.ai_summary,
                "timestamp": alert.created_at.isoformat()
            }
            for alert in alerts
        ]
    }
    
    evidence["summary_stats"] = {
        "total_alerts": len(alerts),
        "alert_types": list(set(alert.alert_type for alert in alerts))
    }

    return evidence