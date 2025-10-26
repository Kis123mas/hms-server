from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import CustomUser
from .models import *
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

@receiver(post_save, sender=Appointment)
def create_appointment_notification(sender, instance, created, **kwargs):
    """
    Create a notification when a new appointment is created
    """
    if created:
        # Create notification for the doctor
        notification = Notification.objects.create(
            sender=instance.patient,
            title="New Appointment",
            message=f"You have a new appointment with {instance.patient.first_name} {instance.patient.last_name} on {instance.appointment_date.strftime('%Y-%m-%d %H:%M')}."
        )
        # Add doctor as receiver
        notification.receivers.add(instance.doctor)
        
        # Send WebSocket notification to the doctor if they are connected
        try:
            # Get the channel layer
            channel_layer = get_channel_layer()
            
            # Check if doctor has an active WebSocket connection
            doctor_connections = ActiveWebSocketConnection.objects.filter(email=instance.doctor.email)
            
            if doctor_connections.exists():
                # Convert email to a valid group name by replacing @ and . with _
                safe_email = instance.doctor.email.replace('@', '_').replace('.', '_')
                
                # Send notification to the doctor's WebSocket
                async_to_sync(channel_layer.group_send)(
                    f"user_{safe_email}",
                    {
                        "type": "send_notification",
                        "message": {
                            "action": "get_notifications",
                            "data": {}
                        }
                    }
                )
        except Exception as e:
            print(f"Error sending WebSocket notification: {str(e)}")


@receiver(post_save, sender=Appointment)
def send_patient_available_notification(sender, instance, **kwargs):
    """
    Send notification when patient marks themselves as available
    Notifies the doctor and all nurses in the doctor's department
    """
    # Only trigger if is_patient_available is True and this is an update (not creation)
    if instance.is_patient_available and not kwargs.get('created', False):
        # Use update_fields to check if is_patient_available was actually updated
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'is_patient_available' in update_fields:
            try:
                # Create notification for patient availability
                notification = Notification.objects.create(
                    sender=instance.patient,
                    title="Patient Available",
                    message=f"{instance.patient.first_name} {instance.patient.last_name} is now available for their appointment scheduled on {instance.appointment_date.strftime('%Y-%m-%d %H:%M')}. Ready for vitals check."
                )
                
                # Add doctor as receiver
                notification.receivers.add(instance.doctor)
                
                # Find all nurses in the doctor's department
                if hasattr(instance.doctor, 'profile') and instance.doctor.profile and instance.doctor.profile.department:
                    doctor_department = instance.doctor.profile.department
                    
                    # Get all nurses in the same department
                    nurses_in_department = CustomUser.objects.filter(
                        role__name='nurse',
                        profile__department=doctor_department,
                        is_active=True
                    )
                    
                    # Add all nurses as receivers
                    for nurse in nurses_in_department:
                        notification.receivers.add(nurse)
                
                # Send WebSocket notifications to all receivers
                send_websocket_notification_to_users(notification)
                
                # Also send appointment updates to refresh appointment lists
                send_websocket_appointments_update(notification)
                
            except Exception as e:
                print(f"Error in patient available notification: {str(e)}")


@receiver(post_save, sender=Appointment)
def send_vitals_taken_notification(sender, instance, **kwargs):
    """
    Send notification when nurse marks vitals as taken
    Notifies the doctor and patient
    """
    # Only trigger if is_vitals_taken is True and this is an update (not creation)
    if instance.is_vitals_taken and not kwargs.get('created', False):
        # Use update_fields to check if is_vitals_taken was actually updated
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'is_vitals_taken' in update_fields:
            try:
                # Get nurse name
                nurse_name = f"{instance.nurse.first_name} {instance.nurse.last_name}" if instance.nurse else "Nurse"
                
                # Create notification for vitals taken
                notification = Notification.objects.create(
                    sender=instance.nurse,
                    title="Vitals Taken",
                    message=f"Vitals have been taken by {nurse_name} for the appointment between {instance.patient.first_name} {instance.patient.last_name} and Dr. {instance.doctor.first_name} {instance.doctor.last_name} scheduled on {instance.appointment_date.strftime('%Y-%m-%d %H:%M')}."
                )
                
                # Add doctor as receiver
                notification.receivers.add(instance.doctor)
                
                # Add patient as receiver
                notification.receivers.add(instance.patient)
                
                # Send WebSocket notifications to all receivers
                send_websocket_notification_to_users(notification)
                
                # Also send appointment updates to refresh appointment lists
                send_websocket_appointments_update(notification)
                
            except Exception as e:
                print(f"Error in vitals taken notification: {str(e)}")


def send_websocket_notification_to_users(notification):
    """
    Helper function to send WebSocket notifications to all notification receivers
    """
    try:
        # Get the channel layer
        channel_layer = get_channel_layer()
        
        # Send to all receivers
        for receiver in notification.receivers.all():
            # Check if receiver has an active WebSocket connection
            receiver_connections = ActiveWebSocketConnection.objects.filter(email=receiver.email)
            
            if receiver_connections.exists():
                # Convert email to a valid group name by replacing @ and . with _
                safe_email = receiver.email.replace('@', '_').replace('.', '_')
                
                # Send notification to the receiver's WebSocket
                async_to_sync(channel_layer.group_send)(
                    f"user_{safe_email}",
                    {
                        "type": "send_notification",
                        "message": {
                            "action": "get_notifications",
                            "data": {}
                        }
                    }
                )
    except Exception as e:
        print(f"Error sending WebSocket notifications: {str(e)}")


def send_websocket_appointments_update(notification):
    """
    Helper function to send WebSocket appointments update to all notification receivers
    This refreshes the appointment lists in real-time for doctors and nurses
    """
    try:
        # Get the channel layer
        channel_layer = get_channel_layer()
        
        # Send to all receivers
        for receiver in notification.receivers.all():
            # Check if receiver has an active WebSocket connection
            receiver_connections = ActiveWebSocketConnection.objects.filter(email=receiver.email)
            
            if receiver_connections.exists():
                # Convert email to a valid group name by replacing @ and . with _
                safe_email = receiver.email.replace('@', '_').replace('.', '_')
                
                # Send appointments update to the receiver's WebSocket
                async_to_sync(channel_layer.group_send)(
                    f"user_{safe_email}",
                    {
                        "type": "send_notification",
                        "message": {
                            "action": "get_appointments",
                            "data": {}
                        }
                    }
                )
    except Exception as e:
        print(f"Error sending WebSocket appointments update: {str(e)}")