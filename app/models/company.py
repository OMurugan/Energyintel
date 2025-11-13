"""
Company model for oil and gas companies
"""
from app import db
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Index
from datetime import datetime


class Company(db.Model):
    """Oil and gas companies"""
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    company_type = Column(String(50), nullable=True)  # e.g., NOC, IOC, Independent
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=True, index=True)
    headquarters = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    country = db.relationship('Country', backref=db.backref('companies', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Company {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'company_type': self.company_type,
            'country_id': self.country_id,
            'headquarters': self.headquarters
        }

