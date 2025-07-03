#!/usr/bin/env python3

from sqlmodel import create_engine, Session, select
from MakerMatrix.models.models import PartModel

# Create engine with correct database name  
engine = create_engine('sqlite:///makers_matrix.db')

# Search for the LMR16030SDDAR part
with Session(engine) as session:
    # Search by part number
    part = session.exec(select(PartModel).where(PartModel.part_number == 'LMR16030SDDAR')).first()
    
    if not part:
        # Search by part name  
        part = session.exec(select(PartModel).where(PartModel.part_name == 'LMR16030SDDAR')).first()
    
    if not part:
        # Search containing the string
        parts = session.exec(select(PartModel).where(
            PartModel.part_number.contains('LMR16030SDDAR') | 
            PartModel.part_name.contains('LMR16030SDDAR')
        )).all()
        if parts:
            part = parts[0]
    
    if part:
        print('=== PART FOUND ===')
        print(f'ID: {part.id}')
        print(f'Part Number: {part.part_number}')  
        print(f'Part Name: {part.part_name}')
        print(f'Description: {repr(part.description)}')
        print(f'Supplier: {part.supplier}')
        print(f'Additional Properties: {part.additional_properties}')
        print()
        
        # Check if additional_properties has description
        if part.additional_properties:
            if 'description' in part.additional_properties:
                print(f'Additional Properties Description: {repr(part.additional_properties["description"])}')
            if 'enrichment_data' in part.additional_properties:
                print(f'Enrichment Data: {part.additional_properties["enrichment_data"]}')
            if 'lcsc_data' in part.additional_properties:
                print(f'LCSC Data: {part.additional_properties["lcsc_data"]}')  
            print(f'All Additional Properties Keys: {list(part.additional_properties.keys())}')
    else:
        print('Part not found - searching all parts with LMR in name...')
        parts = session.exec(select(PartModel).where(
            PartModel.part_number.contains('LMR') |
            PartModel.part_name.contains('LMR')
        )).all()
        print(f'Found {len(parts)} parts with LMR in name:')
        for p in parts[:5]:  # Show first 5
            print(f'- {p.part_name} | {p.part_number} | {repr(p.description)}')