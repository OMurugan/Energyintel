"""
Country model for energy data
"""
from app import db
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime


class Country(db.Model):
    """Country information"""
    __tablename__ = 'countries'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(3), unique=True, nullable=False, index=True)  # ISO 3166-1 alpha-3
    name = Column(String(100), nullable=False, index=True)
    region = Column(String(50), nullable=True, index=True)
    subregion = Column(String(50), nullable=True)
    continent = Column(String(50), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - specify foreign_keys to avoid ambiguity
    productions = db.relationship('Production', backref='country', lazy='dynamic', cascade='all, delete-orphan')
    # Exports and Imports relationships defined in their respective models to avoid ambiguity
    reserves = db.relationship('Reserves', backref='country', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Country {self.code}: {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'region': self.region,
            'subregion': self.subregion,
            'continent': self.continent
        }

