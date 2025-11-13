"""
Exports model for crude oil export data
"""
from app import db
from sqlalchemy import Column, Integer, ForeignKey, Float, Date, DateTime, Index
from datetime import datetime


class Exports(db.Model):
    """Crude oil export data by country and date"""
    __tablename__ = 'exports'
    
    id = Column(Integer, primary_key=True)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    exports_bbl = Column(Float, nullable=False)  # Exports in barrels
    exports_mt = Column(Float, nullable=True)  # Exports in metric tons
    destination_country_id = Column(Integer, ForeignKey('countries.id'), nullable=True)  # Optional destination
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - specify foreign_keys to avoid ambiguity with destination_country_id
    country = db.relationship('Country', foreign_keys=[country_id], backref=db.backref('exports', lazy='dynamic', cascade='all, delete-orphan'))
    destination_country = db.relationship('Country', foreign_keys=[destination_country_id], backref=db.backref('imports_as_destination', lazy='dynamic'))
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_export_country_date', 'country_id', 'date'),
    )
    
    def __repr__(self):
        return f'<Exports {self.country_id} {self.date}: {self.exports_bbl} bbl>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'country_id': self.country_id,
            'date': self.date.isoformat() if self.date else None,
            'exports_bbl': self.exports_bbl,
            'exports_mt': self.exports_mt,
            'destination_country_id': self.destination_country_id
        }

