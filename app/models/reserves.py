"""
Reserves model for crude oil reserves data
"""
from app import db
from sqlalchemy import Column, Integer, ForeignKey, Float, Date, DateTime, Index
from datetime import datetime


class Reserves(db.Model):
    """Crude oil reserves data by country and date"""
    __tablename__ = 'reserves'
    
    id = Column(Integer, primary_key=True)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    reserves_bbl = Column(Float, nullable=False)  # Reserves in barrels
    reserves_mt = Column(Float, nullable=True)  # Reserves in metric tons
    proven_reserves_bbl = Column(Float, nullable=True)  # Proven reserves
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_reserve_country_date', 'country_id', 'date'),
    )
    
    def __repr__(self):
        return f'<Reserves {self.country_id} {self.date}: {self.reserves_bbl} bbl>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'country_id': self.country_id,
            'date': self.date.isoformat() if self.date else None,
            'reserves_bbl': self.reserves_bbl,
            'reserves_mt': self.reserves_mt,
            'proven_reserves_bbl': self.proven_reserves_bbl
        }

