from django import template
from hospital.models import WardRoom

register = template.Library()

@register.filter
def get_ward_room(patient):
    try:
        room = WardRoom.objects.get(assigned_patient=patient)
        return room.room_id
    except WardRoom.DoesNotExist:
        return "Not Assigned"