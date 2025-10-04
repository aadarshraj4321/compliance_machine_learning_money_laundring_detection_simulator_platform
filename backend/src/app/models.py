from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    full_name = Column(String, index=True) # Index for searching by name
    email = Column(String, unique=True, index=True) # Unique and indexed for fast lookups
    country = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # This relationship now explicitly states it joins on the 'to_user_id' column
    # in the Transaction table. This resolves the ambiguity.
    transactions = relationship(
        "Transaction", 
        foreign_keys="[Transaction.to_user_id]", 
        back_populates="to_user"
    )

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True) # Index for time-based queries
    description = Column(String)
    
    # Both foreign keys are now indexed for performance
    to_user_id = Column(Integer, ForeignKey("users.id"), index=True) 
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # We tell each relationship which foreign key it corresponds to
    to_user = relationship("User", foreign_keys=[to_user_id], back_populates="transactions")
    from_user = relationship("User", foreign_keys=[from_user_id])

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    alert_type = Column(String, index=True) # Index for filtering by alert type
    message = Column(String)
    ai_summary = Column(String, nullable=True)
    status = Column(String, default="OPEN", index=True) # Index for finding open alerts
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Foreign key is indexed for performance
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    
    user = relationship("User")

class Watchlist(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True) # Index for fast name lookups
    reason = Column(String)

class GraphAnalysisResult(Base):
    __tablename__ = "graph_analysis_results"
    id = Column(Integer, primary_key=True)
    job_id = Column(String, unique=True, index=True)
    status = Column(String, default="PENDING")
    
    # Foreign key is indexed for performance
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    
    findings = Column(JSONB)
    ai_explanation = Column(String, nullable=True)
    plot_data = Column(JSONB, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User")