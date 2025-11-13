"""
Crude model for crude oil types and quality data
"""
from app import db
from sqlalchemy import Column, Integer, ForeignKey, String, Float, Date, DateTime, Index, Text
from datetime import datetime


class Crude(db.Model):
    """Crude oil types and grades"""
    __tablename__ = 'crudes'
    
    id = Column(Integer, primary_key=True)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    grade = Column(String(50), nullable=True)  # e.g., Light, Medium, Heavy
    api_gravity = Column(Float, nullable=True)  # API gravity
    sulfur_content = Column(Float, nullable=True)  # Sulfur content percentage
    carbon_intensity = Column(Float, nullable=True)  # Carbon intensity metric
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    country = db.relationship('Country', backref=db.backref('crudes', lazy='dynamic'))
    prices = db.relationship('CrudePrice', backref='crude', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Crude {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'country_id': self.country_id,
            'name': self.name,
            'grade': self.grade,
            'api_gravity': self.api_gravity,
            'sulfur_content': self.sulfur_content,
            'carbon_intensity': self.carbon_intensity
        }

