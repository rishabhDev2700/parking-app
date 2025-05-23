import string
from django.db.models.signals import post_save
from django.dispatch import receiver
from parking.models import ParkingLot,ParkingSpace


@receiver(post_save, sender=ParkingLot)
def create_parking_spaces(sender, instance, created, **kwargs):
    """Signal to create parking spaces when a new parking lot is created"""
    if created:
        # Generate space IDs (A1, A2... B1, B2...)
        section_letters = string.ascii_uppercase
        spaces_per_section = 99
        
        spaces_to_create = []
        remaining_spaces = instance.total_spaces
        section_index = 0

        while remaining_spaces > 0:
            section_letter = section_letters[section_index]
            spaces_in_this_section = min(remaining_spaces, spaces_per_section)
            
            for space_number in range(1, spaces_in_this_section + 1):
                space_id = f"{section_letter}{space_number}"
                # Determine space type (every 10th space is handicap, every 5th is premium)
                if space_number % 10 == 0:
                    space_type = 'handicap'
                elif space_number % 5 == 0:
                    space_type = 'premium'
                else:
                    space_type = 'standard'
                
                spaces_to_create.append(
                    ParkingSpace(
                        parking_lot=instance,
                        space_number=space_id,
                        space_type=space_type
                    )
                )
            
            remaining_spaces -= spaces_in_this_section
            section_index += 1

        ParkingSpace.objects.bulk_create(spaces_to_create)
