import os
import random
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import sys

import django
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from faker import Faker
from phonenumber_field.phonenumber import PhoneNumber

# Set up Django environment
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyNextHome.settings')
django.setup()

User = get_user_model()
fake = Faker()

# Constants for Ugandan context with accurate city coordinates
UGANDAN_CITIES = [
    ('Kampala', 'Central', (0.3136, 32.5811)),
    ('Jinja', 'Eastern', (0.4244, 33.2041)),
    ('Mbarara', 'Western', (-0.6049, 30.6485)),
    ('Gulu', 'Northern', (2.7746, 32.2980)),
    ('Entebbe', 'Central', (0.0644, 32.4465)),
    ('Mbale', 'Eastern', (1.0644, 34.1796)),
    ('Fort Portal', 'Western', (0.6933, 30.2666)),
    ('Lira', 'Northern', (2.2350, 32.9097)),
    ('Arua', 'Northern', (3.0201, 30.9111)),
    ('Masaka', 'Central', (-0.3333, 31.7333)),
]

PROPERTY_TYPES = [
    ('House', 'home', 'A standalone residential building'),
    ('Apartment', 'building', 'A unit within a multi-unit residential building'),
    ('Commercial Property', 'store', 'Property used for business purposes'),
    ('Land', 'tree', 'Undeveloped property for construction or investment'),
    ('Farm', 'tractor', 'Agricultural property'),
    ('Rental Unit', 'key', 'Property available for rent'),
    ('Hostel', 'bed', 'Budget accommodation with shared facilities'),
    ('Bungalow', 'home', 'Single-story detached house'),
    ('Villa', 'home', 'A large, luxurious house, often with extensive grounds'),
    ('Warehouse', 'warehouse', 'Storage or industrial space'),
]

AMENITY_CATEGORIES = [
    ('Interior', 'home'),
    ('Exterior', 'tree'),
    ('Kitchen', 'utensils'),
    ('Bathroom', 'bath'),
    ('Bedroom', 'bed'),
    ('Security', 'shield-alt'),
    ('Utilities', 'bolt'),
    ('Parking', 'parking'),
]

AMENITIES = {
    'Interior': [
        ('Air Conditioning', 'snowflake', True),
        ('Ceiling Fans', 'fan', True),
        ('Mosquito Nets', 'mosquito', True),
        ('Water Tank', 'water', True),
        ('Solar Power', 'solar-panel', False),
    ],
    'Exterior': [
        ('Compound Wall', 'fence', True),
        ('Veranda', 'umbrella-beach', True),
        ('Outdoor Kitchen', 'grill', False),
        ('Borehole', 'water', False),
    ],
    'Kitchen': [
        ('Refrigerator', 'refrigerator', True),
        ('Gas Cooker', 'fire', True),
        ('Electric Stove', 'temperature-high', False),
        ('Pantry', 'bread-slice', False),
    ],
    'Bathroom': [
        ('Western Toilet', 'toilet', True),
        ('Bath Tub', 'bath', False),
        ('Geyser', 'water', False),
    ],
    'Bedroom': [
        ('Wardrobe', 'door-closed', True),
        ('Ensuite Bathroom', 'bath', False),
        ('Dressing Area', 'tshirt', False),
    ],
    'Security': [
        ('Security Guard', 'user-shield', True),
        ('Electric Fence', 'bolt', False),
        ('CCTV', 'video', False),
        ('Alarm System', 'bell', False),
    ],
    'Utilities': [
        ('Backup Generator', 'generator', True),
        ('Inverter System', 'bolt', False),
        ('Solar Water Heating', 'solar-panel', False),
    ],
    'Parking': [
        ('Parking Space', 'parking', True),
        ('Car Port', 'car-side', False),
        ('Garage', 'garage', False),
    ],
}

NEIGHBORHOOD_CATEGORIES = [
    ('Education', 'graduation-cap'),
    ('Healthcare', 'hospital'),
    ('Transportation', 'bus'),
    ('Shopping', 'shopping-cart'),
    ('Dining', 'utensils'),
    ('Religious', 'place-of-worship'),
    ('Government', 'landmark'),
    ('Entertainment', 'film'),
]

NEIGHBORHOOD_FEATURES = {
    'Education': [
        ('Primary School', 'school', True),
        ('Secondary School', 'school', True),
        ('University', 'university', False),
        ('Nursery School', 'baby', False),
    ],
    'Healthcare': [
        ('Clinic', 'clinic-medical', True),
        ('Hospital', 'hospital', False),
        ('Pharmacy', 'pills', False),
    ],
    'Transportation': [
        ('Taxi Park', 'taxi', True),
        ('Boda Stage', 'motorcycle', True),
        ('Bus Stop', 'bus', False),
    ],
    'Shopping': [
        ('Market', 'shopping-basket', True),
        ('Supermarket', 'store', False),
        ('Shopping Mall', 'shopping-cart', False),
    ],
    'Dining': [
        ('Restaurant', 'utensils', False),
        ('Cafe', 'coffee', False),
        ('Street Food', 'hamburger', False),
    ],
    'Religious': [
        ('Church', 'church', False),
        ('Mosque', 'mosque', False),
        ('Temple', 'place-of-worship', False),
    ],
    'Government': [
        ('Local Council Office', 'landmark', False),
        ('Police Station', 'police-box', True),
    ],
    'Entertainment': [
        ('Cinema', 'film', False),
        ('Sports Club', 'running', False),
        ('Night Club', 'glass-cheers', False),
    ],
}

LISTING_STATUS = ['draft', 'published', 'pending', 'sold', 'hidden']
LISTING_CATEGORY = ['sale', 'rent', 'lease', 'short_term', 'long_term']
FURNISHING_STATUS = ['furnished', 'unfurnished', 'partially']
AVAILABILITY_STATUS = ['available', 'sold', 'rented', 'under_construction']

def create_property_types():
    from accounts.models import PropertyType
    
    print("Creating property types...")
    for name, icon, description in PROPERTY_TYPES:
        PropertyType.objects.get_or_create(
            name=name,
            defaults={
                'icon': icon,
                'description': description,
            }
        )

def create_amenity_categories():
    from accounts.models import AmenityCategory
    
    print("Creating amenity categories...")
    for name, icon in AMENITY_CATEGORIES:
        AmenityCategory.objects.get_or_create(
            name=name,
            defaults={'icon': icon}
        )

def create_amenities():
    from accounts.models import Amenity, AmenityCategory
    
    print("Creating amenities...")
    for category_name, amenities in AMENITIES.items():
        category = AmenityCategory.objects.get(name=category_name)
        for name, icon, is_featured in amenities:
            Amenity.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'icon': icon,
                    'is_featured': is_featured,
                }
            )

def create_neighborhood_categories():
    from accounts.models import NeighborhoodFeatureCategory
    
    print("Creating neighborhood feature categories...")
    for name, icon in NEIGHBORHOOD_CATEGORIES:
        NeighborhoodFeatureCategory.objects.get_or_create(
            name=name,
            defaults={'icon': icon}
        )

def create_neighborhood_features():
    from accounts.models import NeighborhoodFeature, NeighborhoodFeatureCategory
    
    print("Creating neighborhood features...")
    for category_name, features in NEIGHBORHOOD_FEATURES.items():
        category = NeighborhoodFeatureCategory.objects.get(name=category_name)
        for name, icon, is_essential in features:
            NeighborhoodFeature.objects.get_or_create(
                name=name,
                category=category,
                defaults={
                    'icon': icon,
                    'is_essential': is_essential,
                }
            )

def create_users(count=20):
    from accounts.models import UserProfile
    
    print(f"Creating {count} users...")
    
    # First create an admin user
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123',
        first_name='Admin',
        last_name='User',
        is_realtor=True,
        referral_code=uuid.uuid4()
    )
    UserProfile.objects.create(
        user=admin,
        username='admin',
        unique_id='000000001',
        first_name='Admin',
        last_name='User',
        email='admin@example.com',
        email_confirmed=True,
        phone=PhoneNumber.from_string('+256700000001'),
        gender='M',
        city='Kampala',
        is_verified=True,
        is_active=True
    )
    
    # Create regular users
    for i in range(count):
        first_name = fake.first_name()
        last_name = fake.last_name()
        username = f"{first_name.lower()}{last_name.lower()}"
        email = f"{username}@example.com"
        phone = f"+2567{random.randint(10000000, 99999999)}"
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password='testpass123',
            first_name=first_name,
            last_name=last_name,
            is_realtor=random.random() < 0.3,
            referral_code=uuid.uuid4()
        )
        
        UserProfile.objects.create(
            user=user,
            username=username,
            unique_id=f"{random.randint(100000000, 999999999)}",
            first_name=first_name,
            last_name=last_name,
            email=email,
            email_confirmed=random.random() < 0.8,
            phone=PhoneNumber.from_string(phone),
            gender=random.choice(['M', 'F']),
            date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=70),
            city=random.choice([city[0] for city in UGANDAN_CITIES]),
            bio=fake.text(max_nb_chars=200),
            interests=random.choice(['Sports', 'Travel', 'Real Estate', 'Technology', 'Business']),
            is_verified=random.random() < 0.7,
            is_active=True
        )

def create_addresses(count=1000):
    from accounts.models import Address
    
    print(f"Creating {count} addresses...")
    for i in range(count):
        city_data = random.choice(UGANDAN_CITIES)
        city = city_data[0]
        region = city_data[1]
        city_coords = city_data[2]
        
        street_address = fake.street_address()
        
        # Generate Ugandan-style addresses
        if random.random() < 0.5:
            street_address = f"{random.randint(1, 100)} {fake.street_name()}"
        
        # Generate coordinates within 10km of city center
        lat = city_coords[0] + random.uniform(-0.1, 0.1)
        lon = city_coords[1] + random.uniform(-0.1, 0.1)
        
        # Generate Ugandan postal codes (not official but for testing)
        postal_code = f"UG-{random.randint(1000, 9999)}"
        
        Address.objects.create(
            street_address=street_address,
            apartment_suite=f"Room {random.randint(1, 20)}" if random.random() < 0.3 else None,
            city=city,
            state=region,
            country="Uganda",
            zip_code=postal_code,
            latitude=Decimal(str(round(lat, 6))),
            longitude=Decimal(str(round(lon, 6))),
            neighborhood=fake.city_suffix() if random.random() < 0.5 else None,
            nearby_landmarks=fake.text(max_nb_chars=100) if random.random() < 0.7 else '',
        )

def create_properties(count=1000):
    from accounts.models import (
        Property, PropertyType, Amenity, NeighborhoodFeature, Address
    )
    
    print(f"Creating {count} properties...")
    users = list(User.objects.filter(is_realtor=True))
    property_types = list(PropertyType.objects.all())
    addresses = list(Address.objects.all())
    amenities = list(Amenity.objects.all())
    neighborhood_features = list(NeighborhoodFeature.objects.all())
    
    for i in range(count):
        try:
            owner = random.choice(users)
            agent = random.choice(users) if random.random() < 0.5 else None
            property_type = random.choice(property_types)
            address = addresses[i] if i < len(addresses) else random.choice(addresses)
            
            # Ugandan-style property titles
            title_options = [
                f"{property_type.name} for {'Rent' if random.random() < 0.5 else 'Sale'} in {address.city}",
                f"Beautiful {property_type.name} in {address.neighborhood or address.city}",
                f"Affordable {property_type.name.lower()} in {address.city}",
                f"Luxury {property_type.name.lower()} with great amenities"
            ]
            title = random.choice(title_options)
            slug = slugify(title)
            
            # Generate realistic Ugandan property details
            bedrooms = random.randint(1, 6)
            bathrooms = Decimal(str(round(random.uniform(1, bedrooms + 1), 1)))
            square_feet = random.randint(300, 5000)
            
            # Price ranges in UGX (Ugandan Shillings)
            if property_type.name == 'Land':
                price = Decimal(str(round(random.uniform(5000000, 50000000), 2)))
            elif property_type.name == 'Commercial Property':
                price = Decimal(str(round(random.uniform(10000000, 200000000), 2)))
            else:
                price = Decimal(str(round(random.uniform(2000000, 15000000), 2)))
            
            # Create the property
            prop = Property.objects.create(
                owner=owner,
                agent=agent,
                title=title,
                slug=f"{slug}-{i}",
                description=fake.text(max_nb_chars=500),
                property_type=property_type,
                address=address,
                price=price,
                price_currency='UGX',
                price_per_sqft=price / square_feet,
                is_price_negotiable=random.random() < 0.7,  # More negotiable in Uganda
                tax_rate=Decimal(str(round(random.uniform(0.5, 1.5), 2))),  # Lower tax rates
                hoa_fee=Decimal(str(round(random.uniform(50000, 200000), 2))) if random.random() < 0.2 else None,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                square_feet=square_feet,
                lot_size=Decimal(str(round(random.uniform(0.05, 2.0), 2))) if random.random() < 0.7 else None,
                year_built=random.randint(1980, 2023),
                floors=random.randint(1, 3),
                furnishing_status=random.choice(FURNISHING_STATUS),
                status=random.choice(LISTING_STATUS),
                category=random.choice(LISTING_CATEGORY),
                is_featured=random.random() < 0.1,
                available_from=fake.date_between(start_date='-30d', end_date='+180d') if random.random() < 0.7 else None,
                last_refurbished=fake.date_between(start_date='-10y', end_date='today') if random.random() < 0.4 else None,
                view_count=random.randint(0, 1000),
                favorite_count=random.randint(0, 100),
                is_published=random.random() < 0.8,
                listed_by=owner,
                rating=Decimal(str(round(random.uniform(1, 5), 2))),
                parking_spaces=random.randint(0, 3),
                internet_included=random.random() < 0.6,
                furnish_status=random.choice(FURNISHING_STATUS),
                availability_status=random.choice(AVAILABILITY_STATUS),
            )
            
            # Add amenities (3-8 per property)
            prop_amenities = random.sample(amenities, random.randint(3, 8))
            prop.amenities.set(prop_amenities)
            
            # Add neighborhood features (2-6 per property)
            prop_features = random.sample(neighborhood_features, random.randint(2, 6))
            prop.neighborhood_features.set(prop_features)
            
            if (i + 1) % 100 == 0:
                print(f"Created {i + 1} properties")
                
        except Exception as e:
            print(f"Error creating property: {e}")
            continue

def create_property_images():
    from accounts.models import Property, PropertyImage
    
    print("Creating property images...")
    properties = Property.objects.all()
    image_paths = [
        "property_images/house1.jpg",
        "property_images/apartment1.jpg",
        "property_images/land1.jpg",
        "property_images/commercial1.jpg",
        "property_images/farm1.jpg",
    ]
    
    for prop in properties:
        # Create 2-6 images per property
        for i in range(random.randint(2, 6)):
            PropertyImage.objects.create(
                property=prop,
                image=random.choice(image_paths),
                caption=fake.sentence(),
                is_primary=(i == 0),
                order=i,
            )

def create_property_videos():
    from accounts.models import Property, PropertyVideo
    
    print("Creating property videos...")
    properties = Property.objects.all()
    video_urls = [
        "https://www.youtube.com/watch?v=ugandan_property1",
        "https://www.youtube.com/watch?v=ugandan_property2",
        "https://vimeo.com/ugandan_property3",
    ]
    
    for prop in properties:
        if random.random() < 0.2:  # 20% chance of having videos
            # Create 1-2 videos per property
            for i in range(random.randint(1, 2)):
                PropertyVideo.objects.create(
                    property=prop,
                    video_url=random.choice(video_urls),
                    caption=fake.sentence(),
                    is_primary=(i == 0),
                    order=i,
                )

def main():
    # Create all necessary data
    create_property_types()
    create_amenity_categories()
    create_amenities()
    create_neighborhood_categories()
    create_neighborhood_features()
    create_users()
    create_addresses()
    create_properties()
    create_property_images()
    create_property_videos()
    
    print("Data generation complete!")

if __name__ == '__main__':
    main()