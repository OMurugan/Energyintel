"""
Upstream Project model for oil and gas upstream projects
"""
from app import db
from sqlalchemy import Column, Integer, ForeignKey, String, Float, Date, DateTime, Index, Text, Enum
from datetime import datetime
import enum


class ProjectStatus(enum.Enum):
    """Project status enumeration"""
    PLANNED = "Planned"
    APPROVED = "Approved"
    UNDER_CONSTRUCTION = "Under Construction"
    OPERATIONAL = "Operational"
    SUSPENDED = "Suspended"
    CANCELLED = "Cancelled"


class UpstreamProject(db.Model):
    """Upstream oil and gas projects"""
    __tablename__ = 'upstream_projects'
    
    id = Column(Integer, primary_key=True)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    project_type = Column(String(50), nullable=True)  # e.g., Onshore, Offshore, Deepwater
    status = Column(String(50), nullable=False, index=True)  # Using string instead of Enum for flexibility
    start_date = Column(Date, nullable=True)
    expected_completion_date = Column(Date, nullable=True)
    production_capacity_bbl = Column(Float, nullable=True)  # Production capacity in bbl/day
    investment_usd = Column(Float, nullable=True)  # Investment in USD
    carbon_intensity = Column(Float, nullable=True)  # Carbon intensity metric
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    country = db.relationship('Country', backref=db.backref('upstream_projects', lazy='dynamic'))
    company = db.relationship('Company', backref=db.backref('upstream_projects', lazy='dynamic'))
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_project_country_status', 'country_id', 'status'),
        Index('idx_project_company', 'company_id'),
    )
    
    def __repr__(self):
        return f'<UpstreamProject {self.name} ({self.status})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'country_id': self.country_id,
            'company_id': self.company_id,
            'name': self.name,
            'project_type': self.project_type,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'expected_completion_date': self.expected_completion_date.isoformat() if self.expected_completion_date else None,
            'production_capacity_bbl': self.production_capacity_bbl,
            'investment_usd': self.investment_usd,
            'carbon_intensity': self.carbon_intensity
        }

