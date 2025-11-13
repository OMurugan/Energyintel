"""
Imports model for crude oil import data
"""
from app import db
from sqlalchemy import Column, Integer, ForeignKey, Float, Date, DateTime, Index
from datetime import datetime


class Imports(db.Model):
    """Crude oil import data by country and date"""
    __tablename__ = 'imports'
    
    id = Column(Integer, primary_key=True)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    imports_bbl = Column(Float, nullable=False)  # Imports in barrels
    imports_mt = Column(Float, nullable=True)  # Imports in metric tons
    source_country_id = Column(Integer, ForeignKey('countries.id'), nullable=True)  # Optional source
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - specify foreign_keys to avoid ambiguity with source_country_id
    country = db.relationship('Country', foreign_keys=[country_id], backref=db.backref('imports', lazy='dynamic', cascade='all, delete-orphan'))
    source_country = db.relationship('Country', foreign_keys=[source_country_id], backref=db.backref('exports_as_source', lazy='dynamic'))
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_import_country_date', 'country_id', 'date'),
    )
    
    def __repr__(self):
        return f'<Imports {self.country_id} {self.date}: {self.imports_bbl} bbl>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'country_id': self.country_id,
            'date': self.date.isoformat() if self.date else None,
            'imports_bbl': self.imports_bbl,
            'imports_mt': self.imports_mt,
            'source_country_id': self.source_country_id
        }

