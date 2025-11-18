from django.db.models.signals import post_save, pre_save
from django.db import transaction
from django.dispatch import receiver
from accounts.models import CustomUser
from .models import *
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from django.db.models import Count

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
    Triggers get_appointment_detail action for instant updates
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
                
                # Collect all affected users
                affected_users = [instance.doctor]
                
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
                        affected_users.append(nurse)
                
                # Send WebSocket notifications to all receivers
                send_websocket_notification_to_users(notification)
                
                # Trigger get_appointment_detail action for all affected users
                send_refresh_appointment_action(affected_users, instance.id)
                
            except Exception as e:
                print(f"Error in patient available notification: {str(e)}")




@receiver(post_save, sender=Appointment)
def send_doctor_with_patient_notification(sender, instance, **kwargs):
    """
    Send notification when doctor marks is_doctor_with_patient as True
    Notifies the patient and the assigned nurse
    Triggers get_appointment_detail action for instant updates
    """
    # Only trigger if is_doctor_with_patient is True and this is an update (not creation)
    if instance.is_doctor_with_patient and not kwargs.get('created', False):
        # Use update_fields to check if is_doctor_with_patient was actually updated
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'is_doctor_with_patient' in update_fields:
            try:
                # Get doctor name
                doctor_name = f"Dr. {instance.doctor.first_name} {instance.doctor.last_name}"
                patient_name = f"{instance.patient.first_name} {instance.patient.last_name}"
                
                # Create notification for doctor with patient
                notification = Notification.objects.create(
                    sender=instance.doctor,
                    title="Doctor With Patient",
                    message=f"{doctor_name} is now with patient {patient_name} for the appointment scheduled on {instance.appointment_date.strftime('%Y-%m-%d %H:%M')}."
                )
                
                # Add patient as receiver
                notification.receivers.add(instance.patient)
                
                # Collect affected users for appointment details
                affected_users = [instance.patient]
                
                # Add nurse as receiver if assigned
                if instance.nurse:
                    notification.receivers.add(instance.nurse)
                    affected_users.append(instance.nurse)
                
                # Send WebSocket notifications to all receivers
                send_websocket_notification_to_users(notification)
                
                # Trigger get_appointment_detail action for all affected users
                send_refresh_appointment_action(affected_users, instance.id)
                    
            except Exception as e:
                print(f"Error in doctor with patient notification: {str(e)}")




@receiver(post_save, sender=Appointment)
def send_vitals_taken_notification(sender, instance, **kwargs):
    """
    Send notification when nurse marks vitals as taken
    Notifies the doctor and patient
    Triggers get_appointment_detail action for instant updates
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
                
                # Trigger get_appointment_detail action for all affected users
                send_refresh_appointment_action([instance.doctor, instance.patient], instance.id)
                
            except Exception as e:
                print(f"Error in vitals taken notification: {str(e)}")



@receiver(post_save, sender=Appointment)
def send_doctor_done_with_patient_notification(sender, instance, **kwargs):
    """
    Send notification when doctor marks is_doctor_done_with_patient as True
    Notifies the patient, nurse, and potentially pharmacists
    Triggers get_appointment_detail action for instant updates
    """
    # Only trigger if is_doctor_done_with_patient is True and this is an update (not creation)
    if instance.is_doctor_done_with_patient and not kwargs.get('created', False):
        # Use update_fields to check if is_doctor_done_with_patient was actually updated
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'is_doctor_done_with_patient' in update_fields:
            try:
                # Get doctor and patient names
                doctor_name = f"Dr. {instance.doctor.first_name} {instance.doctor.last_name}"
                patient_name = f"{instance.patient.first_name} {instance.patient.last_name}"
                
                # Create notification for consultation completion
                notification = Notification.objects.create(
                    sender=instance.doctor,
                    title="Consultation Completed",
                    message=f"{doctor_name} has completed the consultation with {patient_name} for the appointment scheduled on {instance.appointment_date.strftime('%Y-%m-%d %H:%M')}."
                )
                
                # Add patient as receiver
                notification.receivers.add(instance.patient)
                
                # Collect affected users for appointment details
                affected_users = [instance.patient]
                
                # Add nurse as receiver if assigned
                if instance.nurse:
                    notification.receivers.add(instance.nurse)
                    affected_users.append(instance.nurse)
                
                # Add all pharmacists as receivers (they may need to dispense prescriptions)
                pharmacists = CustomUser.objects.filter(
                    role__name='pharmacist',
                    is_active=True
                )
                for pharmacist in pharmacists:
                    notification.receivers.add(pharmacist)
                    affected_users.append(pharmacist)
                
                # Send WebSocket notifications to all receivers
                send_websocket_notification_to_users(notification)
                
                # Trigger get_appointment_detail action for all affected users
                send_refresh_appointment_action(affected_users, instance.id)
                    
            except Exception as e:
                print(f"Error in doctor done with patient notification: {str(e)}")



@receiver(post_save, sender=Appointment)
def send_appointment_update_to_all_parties(sender, instance, **kwargs):
    """
    General signal that triggers on ANY appointment update
    Sends WebSocket updates to refresh all client data for affected users
    """
    # Only trigger on updates (not creation, as creation is handled by create_appointment_notification)
    if not kwargs.get('created', False):
        try:
            # Collect all users who should receive the update
            affected_users = [instance.doctor, instance.patient]
            
            # Add nurse if assigned
            if instance.nurse:
                affected_users.append(instance.nurse)
            
            # Send all WebSocket get actions to refresh client data
            send_all_websocket_updates(affected_users)
            
        except Exception as e:
            print(f"Error in general appointment update signal: {str(e)}")



    

def send_all_websocket_updates(users):
    """
    Helper function to send all WebSocket get actions to a list of users
    This triggers the client to refresh appointments, notifications, and other data
    """
    try:
        # Get the channel layer
        channel_layer = get_channel_layer()
        
        # WebSocket actions to trigger on the client
        actions = [
            "get_appointments",
            "get_notifications",
            "get_department_appointments_today",
            # Add more actions here as needed (e.g., "get_prescriptions", "get_vitals", etc.)
        ]
        
        # Send to all affected users
        for user in users:
            # Check if user has an active WebSocket connection
            user_connections = ActiveWebSocketConnection.objects.filter(email=user.email)
            
            if user_connections.exists():
                # Convert email to a valid group name by replacing @ and . with _
                safe_email = user.email.replace('@', '_').replace('.', '_')
                
                # Send each action to the user's WebSocket
                for action in actions:
                    async_to_sync(channel_layer.group_send)(
                        f"user_{safe_email}",
                        {
                            "type": "send_notification",
                            "message": {
                                "action": action,
                                "data": {}
                            }
                        }
                    )
    except Exception as e:
        print(f"Error sending WebSocket updates: {str(e)}")


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


def send_appointment_details_to_users(users, appointment_data, event_type):
    """
    Helper function to send appointment details directly to users via WebSocket
    
    Args:
        users: List of users to send the appointment data to
        appointment_data: Serialized appointment data (dictionary)
        event_type: Type of event (e.g., 'patient_available', 'vitals_taken', etc.)
    """
    try:
        # Get the channel layer
        channel_layer = get_channel_layer()
        
        # Send to all specified users
        for user in users:
            # Check if user has an active WebSocket connection
            user_connections = ActiveWebSocketConnection.objects.filter(email=user.email)
            
            if user_connections.exists():
                # Convert email to a valid group name by replacing @ and . with _
                safe_email = user.email.replace('@', '_').replace('.', '_')
                
                # Send appointment details to the user's WebSocket
                async_to_sync(channel_layer.group_send)(
                    f"user_{safe_email}",
                    {
                        "type": "send_notification",
                        "message": {
                            "action": "appointment_updated",
                            "event_type": event_type,
                            "data": {
                                "appointment": appointment_data
                            }
                        }
                    }
                )
    except Exception as e:
        print(f"Error sending appointment details via WebSocket: {str(e)}")


def send_refresh_appointment_action(users, appointment_id):
    """
    Helper function to trigger get_appointment_detail action for users via WebSocket
    This prompts the client to fetch the updated appointment data
    
    Args:
        users: List of users to send the action to
        appointment_id: ID of the appointment to refresh
    """
    try:
        # Get the channel layer
        channel_layer = get_channel_layer()
        
        for user in users:
            if not isinstance(user, CustomUser):
                continue
                
            # Send refresh action to user's WebSocket group
            safe_email = user.email.replace('@', '_').replace('.', '_')
            async_to_sync(channel_layer.group_send)(
                f"user_{safe_email}",
                {
                    "type": "send_message",
                    "message": {
                        "type": "action",
                        "action": "get_appointment_detail",
                        "appointment_id": str(appointment_id)
                    }
                }
            )
    except Exception as e:
        print(f"Error sending refresh appointment action: {str(e)}")


@receiver(post_save, sender=Room)
def create_room_beds(sender, instance, created, **kwargs):
    """
    Automatically create or update beds when a room is created or updated.
    Creates new beds if bed_count is increased, deletes excess beds if decreased.
    """
    if created:
        # If it's a new room, create the specified number of beds
        with transaction.atomic():
            for i in range(1, instance.bed_count + 1):
                Bed.objects.create(
                    room=instance,
                    is_occupied=False,
                    created_at=timezone.now()
                )
    else:
        # If it's an update, check if bed_count has changed
        try:
            old_instance = Room.objects.get(pk=instance.pk)
            if old_instance.bed_count != instance.bed_count:
                with transaction.atomic():
                    current_bed_count = instance.beds.count()
                    occupied_beds = instance.beds.filter(is_occupied=True).count()
                    
                    # Ensure we don't set bed count below number of occupied beds
                    if instance.bed_count < occupied_beds:
                        raise ValidationError(
                            f"Cannot reduce bed count to {instance.bed_count} "
                            f"because there are {occupied_beds} occupied beds."
                        )
                    
                    if instance.bed_count > current_bed_count:
                        # Add new beds
                        for i in range(current_bed_count + 1, instance.bed_count + 1):
                            Bed.objects.create(
                                room=instance,
                                is_occupied=False,
                                created_at=timezone.now()
                            )
                    elif instance.bed_count < current_bed_count:
                        # Remove excess unoccupied beds
                        excess_beds = instance.beds.filter(is_occupied=False)[:current_bed_count - instance.bed_count]
                        excess_beds.delete()
        except Room.DoesNotExist:
            # Handle case where the room was just created in a different process
            pass
    """
    Helper function to trigger get_appointment_detail action for users via WebSocket
    This prompts the client to fetch the updated appointment data
    
    Args:
        users: List of users to send the action to
        appointment_id: ID of the appointment to refresh
    """
    try:
        # Get the channel layer
        channel_layer = get_channel_layer()
        
        # Send to all specified users
        for user in users:
            # Check if user has an active WebSocket connection
            user_connections = ActiveWebSocketConnection.objects.filter(email=user.email)
            
            if user_connections.exists():
                # Convert email to a valid group name by replacing @ and . with _
                safe_email = user.email.replace('@', '_').replace('.', '_')
                
                # Send get_appointment_detail action to the user's WebSocket
                async_to_sync(channel_layer.group_send)(
                    f"user_{safe_email}",
                    {
                        "type": "send_notification",
                        "message": {
                            "action": "get_appointment_detail",
                            "data": {
                                "appointment_id": appointment_id
                            }
                        }
                    }
                )
    except Exception as e:
        print(f"Error sending refresh appointment action via WebSocket: {str(e)}")


@receiver(post_save, sender=DrugSale)
def update_drug_quantities_on_payment(sender, instance, created, **kwargs):
    """
    Subtract drug quantities when DrugSale payment status changes to 'paid'
    """
    print(f"DrugSale signal triggered - created: {created}, payment_status: {instance.payment_status}, amount_paid: {instance.amount_paid}, total_amount: {instance.total_amount}")
    
    # Check if this is an update (not creation) and payment status is now 'paid'
    if not created and instance.payment_status == 'paid':
        print("Payment status is 'paid' and this is an update, checking update_fields...")
        
        # Use update_fields to check if payment_status was actually updated
        update_fields = kwargs.get('update_fields')
        print(f"Update fields: {update_fields}")
        
        if update_fields is None or 'payment_status' in update_fields or 'amount_paid' in update_fields:
            print("Proceeding with drug quantity update...")
            try:
                with transaction.atomic():
                    # Find related ReferralDispensedDrugItem through BulkSaleId
                    if instance.sales_id:
                        referral_items = ReferralDispensedDrugItem.objects.filter(
                            bulk_sale_id=instance.sales_id
                        )
                        
                        print(f"Processing payment for DrugSale {instance.id}, found {referral_items.count()} items")
                        
                        for item in referral_items:
                            # Subtract the number_of_cards from the drug quantity
                            drug = item.drug
                            if drug.quantity >= item.number_of_cards:
                                drug.quantity -= item.number_of_cards
                                drug.save(update_fields=['quantity'])
                                print(f"Reduced {drug.name} quantity by {item.number_of_cards}, new quantity: {drug.quantity}")
                            else:
                                # Handle insufficient quantity - could raise an error or log warning
                                print(f"Warning: Insufficient quantity for drug {drug.name}. "
                                      f"Available: {drug.quantity}, Required: {item.number_of_cards}")
                    else:
                        print("No sales_id found for this DrugSale")
                                
            except Exception as e:
                print(f"Error updating drug quantities on payment: {str(e)}")
        else:
            print("Update fields check failed - not processing")
    else:
        if created:
            print("This is a new DrugSale creation - not processing")
        else:
            print(f"Payment status is not 'paid': {instance.payment_status}")