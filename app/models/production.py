"""
Production model for crude oil production data
"""
from app import db
from sqlalchemy import Column, Integer, ForeignKey, Float, Date, DateTime, Index
from datetime import datetime


class Production(db.Model):
    """Crude oil production data by country and date"""
    __tablename__ = 'productions'
    
    id = Column(Integer, primary_key=True)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    production_bbl = Column(Float, nullable=False)  # Production in barrels
    production_mt = Column(Float, nullable=True)  # Production in metric tons
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_country_date', 'country_id', 'date'),
    )
    
    def __repr__(self):
        return f'<Production {self.country_id} {self.date}: {self.production_bbl} bbl>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'country_id': self.country_id,
            'date': self.date.isoformat() if self.date else None,
            'production_bbl': self.production_bbl,
            'production_mt': self.production_mt
        }

