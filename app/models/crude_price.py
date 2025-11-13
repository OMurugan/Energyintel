"""
Crude Price model for crude oil pricing data
"""
from app import db
from sqlalchemy import Column, Integer, ForeignKey, Float, Date, DateTime, Index, String
from datetime import datetime


class CrudePrice(db.Model):
    """Crude oil price data by crude type and date"""
    __tablename__ = 'crude_prices'
    
    id = Column(Integer, primary_key=True)
    crude_id = Column(Integer, ForeignKey('crudes.id'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    price_usd_bbl = Column(Float, nullable=False)  # Price in USD per barrel
    price_type = Column(String(50), nullable=True)  # e.g., Spot, Futures, Dated
    benchmark = Column(String(50), nullable=True)  # e.g., Brent, WTI
    gross_product_worth = Column(Float, nullable=True)  # GPW
    margin = Column(Float, nullable=True)  # Refining margin
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_crude_price_date', 'crude_id', 'date'),
    )
    
    def __repr__(self):
        return f'<CrudePrice {self.crude_id} {self.date}: ${self.price_usd_bbl}/bbl>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'crude_id': self.crude_id,
            'date': self.date.isoformat() if self.date else None,
            'price_usd_bbl': self.price_usd_bbl,
            'price_type': self.price_type,
            'benchmark': self.benchmark,
            'gross_product_worth': self.gross_product_worth,
            'margin': self.margin
        }

