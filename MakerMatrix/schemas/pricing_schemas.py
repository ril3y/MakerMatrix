"""
Standardized Pricing Schemas

All suppliers must massage their pricing data into these standardized formats.
We support 3 main pricing patterns that cover 99% of use cases.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class PricingType(str, Enum):
    """Supported pricing types"""
    NO_PRICING = "no_pricing"           # Part has no pricing information
    SINGLE_PRICE = "single_price"       # Simple unit price only  
    QUANTITY_BREAKS = "quantity_breaks" # Quantity-based price tiers


class PriceBreak(BaseModel):
    """Individual price break for quantity-based pricing"""
    quantity: int = Field(ge=1, description="Minimum quantity for this price")
    price: float = Field(ge=0, description="Price per unit at this quantity")


class StandardPricing(BaseModel):
    """
    Universal pricing format that ALL suppliers must conform to.
    Supports 3 scenarios:
    
    1. NO_PRICING: Part has no price information
    2. SINGLE_PRICE: Simple unit price (e.g., $0.25 each)  
    3. QUANTITY_BREAKS: Tiered pricing (e.g., 1-99: $0.25, 100+: $0.20)
    """
    
    pricing_type: PricingType = Field(description="Type of pricing structure")
    currency: str = Field(default="USD", description="Currency code (USD, EUR, etc.)")
    
    # For SINGLE_PRICE and QUANTITY_BREAKS
    unit_price: Optional[float] = Field(default=None, description="Primary unit price")
    
    # For QUANTITY_BREAKS only
    price_breaks: Optional[List[PriceBreak]] = Field(default=None, description="Quantity-based price tiers")
    
    # Metadata (always included)
    supplier: Optional[str] = Field(default=None, description="Source supplier")
    last_updated: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    def get_price_for_quantity(self, quantity: int) -> Optional[float]:
        """Get the best price for a given quantity"""
        if self.pricing_type == PricingType.NO_PRICING:
            return None
            
        if self.pricing_type == PricingType.SINGLE_PRICE:
            return self.unit_price
            
        if self.pricing_type == PricingType.QUANTITY_BREAKS and self.price_breaks:
            # Find the best price break for this quantity
            applicable_breaks = [pb for pb in self.price_breaks if quantity >= pb.quantity]
            if applicable_breaks:
                # Return the price for the highest quantity break that applies
                best_break = max(applicable_breaks, key=lambda x: x.quantity)
                return best_break.price
                
        # Fallback to unit price
        return self.unit_price
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage in PartModel.pricing_data"""
        data = {
            "pricing_type": self.pricing_type.value,
            "currency": self.currency,
            "supplier": self.supplier,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }
        
        if self.pricing_type != PricingType.NO_PRICING:
            data["unit_price"] = self.unit_price
            
        if self.pricing_type == PricingType.QUANTITY_BREAKS and self.price_breaks:
            data["price_breaks"] = [{"quantity": pb.quantity, "price": pb.price} for pb in self.price_breaks]
            
        return data


# Helper functions for suppliers to convert their data
def create_no_pricing() -> StandardPricing:
    """Create pricing structure for parts with no pricing"""
    return StandardPricing(pricing_type=PricingType.NO_PRICING)


def create_single_price(price: float, currency: str = "USD", supplier: str = None) -> StandardPricing:
    """Create pricing structure for simple unit pricing"""
    return StandardPricing(
        pricing_type=PricingType.SINGLE_PRICE,
        unit_price=price,
        currency=currency,
        supplier=supplier
    )


def create_quantity_breaks(
    price_breaks: List[Dict[str, Any]], 
    currency: str = "USD", 
    supplier: str = None
) -> StandardPricing:
    """
    Create pricing structure for quantity-based pricing
    
    Args:
        price_breaks: List of {"quantity": int, "price": float} dictionaries
        currency: Currency code
        supplier: Supplier name
        
    Example:
        create_quantity_breaks([
            {"quantity": 1, "price": 0.33},
            {"quantity": 100, "price": 0.25},
            {"quantity": 1000, "price": 0.20}
        ])
    """
    breaks = []
    unit_price = None
    
    for break_data in price_breaks:
        if "quantity" in break_data and "price" in break_data:
            quantity = int(break_data["quantity"])
            price = float(break_data["price"])
            breaks.append(PriceBreak(quantity=quantity, price=price))
            
            # Set unit price to the lowest quantity break (usually qty=1)
            if unit_price is None or quantity == 1:
                unit_price = price
    
    # Sort breaks by quantity
    breaks.sort(key=lambda x: x.quantity)
    
    return StandardPricing(
        pricing_type=PricingType.QUANTITY_BREAKS,
        unit_price=unit_price,
        price_breaks=breaks,
        currency=currency,
        supplier=supplier
    )


def convert_generic_pricing_data(raw_data: Any, supplier: str = None) -> StandardPricing:
    """
    Generic converter that attempts to handle common pricing formats
    
    This is a fallback for suppliers that haven't implemented specific conversion logic.
    """
    
    # No data = no pricing
    if not raw_data:
        return create_no_pricing()
    
    # Simple number = single price
    if isinstance(raw_data, (int, float)):
        return create_single_price(float(raw_data), supplier=supplier)
    
    # List of price breaks
    if isinstance(raw_data, list):
        # Check if it looks like price breaks
        if all(isinstance(item, dict) and "quantity" in item and "price" in item for item in raw_data):
            return create_quantity_breaks(raw_data, supplier=supplier)
    
    # Dictionary with price info
    if isinstance(raw_data, dict):
        # Single price in dict format
        if "price" in raw_data and "quantity" not in raw_data:
            price = float(raw_data["price"])
            currency = raw_data.get("currency", "USD")
            return create_single_price(price, currency, supplier)
            
        # Price breaks in dict format
        if "breaks" in raw_data or "price_breaks" in raw_data:
            breaks_key = "breaks" if "breaks" in raw_data else "price_breaks"
            currency = raw_data.get("currency", "USD")
            return create_quantity_breaks(raw_data[breaks_key], currency, supplier)
    
    # Couldn't parse - no pricing
    return create_no_pricing()