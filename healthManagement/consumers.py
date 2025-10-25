import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from accounts.models import CustomUser
from healthManagement.models import ActiveWebSocketConnection, Appointment, Notification
from healthManagement.serializers import (
    PatientAppointmentSerializer as AppointmentSerializer,
    NotificationSerializer
)
from django.utils import timezone
from django.db.models import Prefetch
from django.core.serializers.json import DjangoJSONEncoder


class SimpleConsumer(AsyncWebsocketConsumer):
    """
    Simple WebSocket consumer with email-based authentication
    Only users with email in the database can connect
    Saves connection to database on connect and removes on disconnect
    """
    
    async def connect(self):
        """
        Handle WebSocket connection
        Authenticate user by email from query parameters
        Save connection to database
        """
        # Get email from query parameters
        query_string = self.scope.get('query_string', b'').decode()
        email = None
        
        # Parse query string to get email
        if query_string:
            params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
            email = params.get('email')
        
        # Check if email exists in database
        if email:
            user_exists = await self.check_user_exists(email)
            if user_exists:
                self.email = email
                
                # Save connection to database
                await self.save_connection(email)
                
                await self.accept()
                
                # Send connection success message
                await self.send(text_data=json.dumps({
                    'type': 'connection_established',
                    'message': f'Connected successfully as {email}'
                }))
                
                print(f"WebSocket connected: {email}")
            else:
                # Reject connection if email not found
                await self.close(code=4001)
                print(f"WebSocket connection rejected: {email} not found in database")
        else:
            # Reject connection if no email provided
            await self.close(code=4000)
            print("WebSocket connection rejected: No email provided")
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection
        Remove connection from database
        """
        if hasattr(self, 'email'):
            # Remove connection from database
            await self.remove_connection(self.email)
            print(f"WebSocket disconnected: {self.email} (code: {close_code})")
        else:
            print(f"WebSocket disconnected (code: {close_code})")
    
    async def receive(self, text_data):
        """
        Handle messages received from WebSocket
        Expected message format:
        {
            'action': 'get_appointments',  # Action to perform
            'data': {}  # Additional data for the action
        }
        """
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'get_appointments':
                await self.handle_get_appointments(data.get('data', {}))
            elif action == 'get_notifications':
                await self.handle_get_notifications(data.get('data', {}))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown action: {action}'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
            
    async def handle_get_appointments(self, data):
        """
        Handle get_appointments action
        """
        try:
            appointments = await self.get_patient_appointments(self.email)
            await self.send(text_data=json.dumps({
                'type': 'appointments_data',
                'data': appointments
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Failed to fetch appointments: {str(e)}'
            }))
    
    @database_sync_to_async
    def get_patient_appointments(self, email):
        """
        Get all appointments for a patient by email
        """
        try:
            # Get current date and time
            now = timezone.now()
            
            # Get upcoming appointments (today and future)
            appointments = Appointment.objects.filter(
                patient__email=email,
                appointment_date__gte=now.date()
            ).order_by('appointment_date')
            
            # Serialize the appointments
            serializer = AppointmentSerializer(appointments, many=True)
            return serializer.data
            
        except Exception as e:
            print(f"Error getting appointments: {str(e)}")
            return []
    
    @database_sync_to_async
    def check_user_exists(self, email):
        """
        Check if user with given email exists in database
        """
        return CustomUser.objects.filter(email=email).exists()
    
    @database_sync_to_async
    def save_connection(self, email):
        """
        Save active WebSocket connection to database
        If connection already exists, update the last_activity timestamp
        """
        connection, created = ActiveWebSocketConnection.objects.get_or_create(
            email=email
        )
        if not created:
            # Update last_activity if connection already exists
            connection.save()
        return connection
    
    @database_sync_to_async
    def remove_connection(self, email):
        """
        Remove active WebSocket connection from database
        """
        ActiveWebSocketConnection.objects.filter(email=email).delete()
        
    async def handle_get_notifications(self, data):
        """
        Handle get_notifications action
        """
        try:
            notifications, unread_count = await self.get_user_notifications(self.email)
            await self.send(text_data=json.dumps({
                'type': 'notifications_data',
                'data': {
                    'notifications': notifications,
                    'unread_count': unread_count
                }
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Failed to fetch notifications: {str(e)}'
            }))
    
    @database_sync_to_async
    def get_user_notifications(self, email):
        """
        Get all notifications for a user by email using NotificationSerializer
        Returns a tuple of (serialized_notifications, unread_count)
        """
        # Get all notifications for the user
        notifications = Notification.objects.filter(
            receivers__email=email
        ).select_related('sender').order_by('-created_at')
        
        # Get unread count
        unread_count = notifications.filter(is_read=False).count()
        
        # Create a fake request context for URL building
        from django.test.client import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        
        # Use the serializer
        serializer = NotificationSerializer(
            notifications,
            many=True,
            context={'request': request}
        )
        
        return serializer.data, unread_count
