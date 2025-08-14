"""
Source Processor - Handles extracting and processing contacts from different sources
"""

import logging
import os
import csv
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from waha_functions import WAHAClient
from utils.file_handler import FileHandler
from .campaign_sources import (
    SourceType, CSVSource, WhatsAppGroupSource, 
    UserContactsSource, GroupDeliveryMethod
)

logger = logging.getLogger(__name__)

class SourceProcessor:
    """Processes different contact sources for campaigns"""
    
    def __init__(self):
        self.waha_client = WAHAClient()
        self.file_handler = FileHandler()
        self.logger = logger
    
    async def process_source(
        self, 
        source: Any, 
        session_name: str,
        save_to_db: bool = True
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Process any source type and return contacts
        
        Returns:
            Tuple of (contacts_list, metadata_dict)
        """
        source_type = source.source_type
        
        if source_type == SourceType.CSV_UPLOAD:
            return await self._process_csv_source(source, session_name)
        elif source_type == SourceType.WHATSAPP_GROUP:
            return await self._process_group_source(source, session_name)
        elif source_type == SourceType.USER_CONTACTS:
            return await self._process_contacts_source(source, session_name)
        else:
            raise ValueError(f"Unknown source type: {source_type}")
    
    async def _process_csv_source(
        self, 
        source: CSVSource, 
        session_name: str
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """Process CSV file source"""
        try:
            # Use existing file handler logic
            validation_result = self.file_handler.validate_file(source.file_path)
            if not validation_result.get("valid"):
                raise ValueError(f"Invalid CSV file: {validation_result.get('error')}")
            
            # Read CSV file
            contacts = []
            with open(source.file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader, 1):
                    if idx < source.start_row:
                        continue
                    if source.end_row and idx > source.end_row:
                        break
                    
                    # Extract phone number (handle different column names)
                    phone = (row.get('phone_number') or 
                            row.get('phone') or 
                            row.get('number') or 
                            row.get('formatted_phone', '')).strip()
                    
                    if phone:
                        # Clean phone number
                        phone = phone.replace(' ', '').replace('-', '')
                        if not phone.startswith('+'):
                            phone = f"+{phone}"
                        
                        contacts.append({
                            'phone_number': phone,
                            'name': row.get('name') or row.get('saved_name', ''),
                            'data': row  # Keep all columns for template variables
                        })
            
            metadata = {
                'source_type': 'csv',
                'file_path': source.file_path,
                'total_rows': len(contacts),
                'start_row': source.start_row,
                'end_row': source.end_row
            }
            
            return contacts, metadata
            
        except Exception as e:
            self.logger.error(f"Error processing CSV source: {str(e)}")
            raise
    
    async def _process_group_source(
        self, 
        source: WhatsAppGroupSource, 
        session_name: str
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """Process WhatsApp group source"""
        try:
            contacts = []
            group_names = []
            
            self.logger.info(f"Processing group source with session_name: '{session_name}'")
            
            for group_id in source.group_ids:
                # Get group info
                self.logger.info(f"Getting group info for: '{group_id}' using session: '{session_name}'")
                group_info = self.waha_client.get_group_info(session_name, group_id)
                group_name = group_info.get('groupMetadata', {}).get('subject', 'Unknown Group')
                group_names.append(group_name)
                
                if source.delivery_method == GroupDeliveryMethod.INDIVIDUAL_DMS:
                    # Extract group members for individual DMs
                    participants = self.waha_client.get_group_participants_details(
                        session_name, group_id
                    )
                    
                    for participant in participants:
                        phone = participant.get('formatted_phone', '')
                        if phone and not phone.startswith('+'):
                            phone = f"+{phone}"
                        
                        if phone:
                            # Include all 16 fields from participant data
                            contacts.append({
                                'phone_number': phone,
                                'formatted_phone': participant.get('formatted_phone', ''),
                                'country_code': participant.get('country_code', ''),
                                'country_name': participant.get('country_name', ''),
                                'saved_name': participant.get('saved_name', ''),
                                'public_name': participant.get('public_name', ''),
                                'name': participant.get('saved_name') or participant.get('public_name', ''),
                                'is_my_contact': 'true' if participant.get('saved_name') else 'false',
                                'is_business': 'true' if participant.get('is_business') else 'false',
                                'is_blocked': 'true' if participant.get('is_blocked') else 'false',
                                'is_admin': 'true' if participant.get('is_admin') else 'false',
                                'is_super_admin': 'true' if participant.get('is_super_admin') else 'false',
                                'labels': participant.get('labels', ''),
                                'last_msg_text': participant.get('last_msg_text', ''),
                                'last_msg_date': participant.get('last_msg_date', ''),
                                'last_msg_type': participant.get('last_msg_type', ''),
                                'last_msg_status': participant.get('last_msg_status', ''),
                                'group_name': group_name,
                                'data': participant
                            })
                
                elif source.delivery_method == GroupDeliveryMethod.GROUP_MESSAGE:
                    # For group messages, we'll handle differently
                    # Add group as a "contact" for the campaign processor
                    contacts.append({
                        'phone_number': group_id,  # Use group ID as identifier
                        'name': group_name,
                        'is_group': True,
                        'group_id': group_id,
                        'data': {'group_name': group_name}
                    })
                
                # Handle auto-join if needed
                if source.auto_join:
                    await self._ensure_group_membership(session_name, group_id)
            
            # Remove duplicates if sending individual DMs
            if source.delivery_method == GroupDeliveryMethod.INDIVIDUAL_DMS:
                seen = set()
                unique_contacts = []
                for contact in contacts:
                    phone = contact['phone_number']
                    if phone not in seen:
                        seen.add(phone)
                        unique_contacts.append(contact)
                contacts = unique_contacts
            
            metadata = {
                'source_type': 'whatsapp_group',
                'group_ids': source.group_ids,
                'group_names': group_names,
                'delivery_method': source.delivery_method.value,
                'total_contacts': len(contacts)
            }
            
            return contacts, metadata
            
        except Exception as e:
            self.logger.error(f"Error processing group source: {str(e)}")
            raise
    
    async def _process_contacts_source(
        self, 
        source: UserContactsSource, 
        session_name: str
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """Process user contacts source"""
        try:
            # Get all contacts from session
            all_contacts = self.waha_client.get_all_contacts(session_name)
            
            contacts = []
            for contact in all_contacts:
                # Skip groups
                if contact.get('isGroup', False):
                    continue
                
                # Skip @lid contacts
                if '@lid' in str(contact.get('id', '')):
                    continue
                
                # Apply filter if needed
                if source.filter_only_my_contacts and not contact.get('isMyContact', False):
                    continue
                
                # Check if specific contacts selected or all
                if isinstance(source.contact_selection, list):
                    if contact.get('id') not in source.contact_selection:
                        continue
                
                phone = contact.get('number', '')
                
                # Extract from id if number is missing
                if not phone and contact.get('id'):
                    contact_id = str(contact.get('id', ''))
                    if '@c.us' in contact_id:
                        phone = contact_id.replace('@c.us', '')
                
                if phone:
                    # Format phone number with space after country code (matching export format)
                    formatted_phone = phone
                    country_code = ''
                    country_name = ''
                    
                    # Clean phone first
                    phone = phone.strip()
                    if not phone.startswith('+'):
                        phone = f"+{phone}"
                    
                    # Format based on country code
                    if phone.startswith('+1') and len(phone) >= 12:
                        formatted_phone = f"+1 {phone[2:]}"
                        country_code = '+1'
                        country_name = 'United States/Canada'
                    elif phone.startswith('+234') and len(phone) >= 14:
                        formatted_phone = f"+234 {phone[4:]}"
                        country_code = '+234'
                        country_name = 'Nigeria'
                    elif phone.startswith('+91') and len(phone) >= 13:
                        formatted_phone = f"+91 {phone[3:]}"
                        country_code = '+91'
                        country_name = 'India'
                    elif phone.startswith('+44'):
                        formatted_phone = f"+44 {phone[3:]}"
                        country_code = '+44'
                        country_name = 'United Kingdom'
                    else:
                        # For other countries, try to detect and format
                        formatted_phone = phone
                    
                    # Get additional contact details for all 16 fields
                    contacts.append({
                        'phone_number': formatted_phone,  # Use formatted version with space
                        'formatted_phone': formatted_phone,
                        'country_code': country_code,
                        'country_name': country_name,
                        'saved_name': contact.get('name', '') if contact.get('isMyContact') else '',
                        'public_name': contact.get('pushname', ''),
                        'name': contact.get('name') or contact.get('pushname', ''),
                        'is_my_contact': 'true' if contact.get('isMyContact', False) else 'false',
                        'is_business': 'true' if contact.get('isBusiness', False) else 'false',
                        'is_blocked': 'false',  # Would need to check blocked status
                        'is_admin': 'false',  # N/A for direct contacts
                        'is_super_admin': 'false',  # N/A for direct contacts
                        'labels': '',  # Would need to fetch labels
                        'last_msg_text': '',  # Would need chat history
                        'last_msg_date': '',  # Would need chat history
                        'last_msg_type': '',  # Would need chat history
                        'last_msg_status': '',  # Would need chat history
                        'data': contact
                    })
            
            metadata = {
                'source_type': 'user_contacts',
                'selection': source.contact_selection,
                'filter_only_my_contacts': source.filter_only_my_contacts,
                'total_contacts': len(contacts)
            }
            
            return contacts, metadata
            
        except Exception as e:
            self.logger.error(f"Error processing contacts source: {str(e)}")
            raise
    
    async def _ensure_group_membership(self, session_name: str, group_id: str):
        """Ensure the session is a member of the group"""
        try:
            # Check if already a member
            group_info = self.waha_client.get_group_info(session_name, group_id)
            
            # Get session's own ID
            session_info = self.waha_client.get_session_info(session_name)
            my_id = session_info.get('me', {}).get('id', '')
            
            # Check if we're in the participants list
            participants = group_info.get('groupMetadata', {}).get('participants', [])
            is_member = any(p.get('id', {}).get('_serialized', '') == my_id 
                          for p in participants)
            
            if not is_member:
                self.logger.info(f"Auto-joining group {group_id}")
                # Note: WAHA might not support auto-join via API
                # This would need to be handled via invite link or manual process
                self.logger.warning(f"Cannot auto-join group {group_id}. Manual join required.")
                
        except Exception as e:
            self.logger.error(f"Error checking group membership: {str(e)}")
    
    def deduplicate_contacts(self, contacts: List[Dict]) -> List[Dict]:
        """Remove duplicate contacts based on phone number"""
        seen = set()
        unique = []
        for contact in contacts:
            phone = contact.get('phone_number', '')
            if phone and phone not in seen:
                seen.add(phone)
                unique.append(contact)
        return unique