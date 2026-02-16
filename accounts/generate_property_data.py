import os
import sys
import uuid
import random
from decimal import Decimal
from datetime import datetime, timedelta


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
    # (Name, Icon, Description, is_residential, is_commercial, is_hospitality, default_pricing_model)
    ('House', 'home', 'A standalone residential building', True, False, False, 'fixed'),
    ('Apartment', 'building', 'A unit within a multi-unit residential building', True, False, False, 'fixed'),
    ('Commercial Property', 'store', 'Property used for business purposes', False, True, False, 'fixed'),
    ('Land', 'tree', 'Undeveloped property for construction or investment', False, False, False, 'fixed'),
    ('Farm', 'tractor', 'Agricultural property', False, True, False, 'fixed'),
    ('Rental Unit', 'key', 'Property available for rent', True, False, False, 'per_month'),
    ('Hostel', 'bed', 'Budget accommodation with shared facilities', False, False, True, 'per_night'),
    ('Bungalow', 'home', 'Single-story detached house', True, False, False, 'fixed'),
    ('Villa', 'home', 'A large, luxurious house, often with extensive grounds', True, False, False, 'fixed'),
    ('Warehouse', 'warehouse', 'Storage or industrial space', False, True, False, 'per_sqft'),
    ('Office', 'briefcase', 'Office space for business', False, True, False, 'per_sqft'),
    ('Shop', 'shopping-bag', 'Retail shop space', False, True, False, 'fixed'),
    ('Hotel Room', 'hotel', 'Hotel accommodation', False, False, True, 'per_night'),
    ('Coworking Space', 'laptop', 'Shared office workspace', False, True, False, 'per_hour'),
    ('Event Hall', 'glass-cheers', 'Venue for events and parties', False, True, True, 'per_hour'),
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
    for name, icon, description, is_res, is_com, is_hos, pricing in PROPERTY_TYPES:
        PropertyType.objects.update_or_create(
            name=name,
            defaults={
                'icon': icon,
                'description': description,
                'is_residential': is_res,
                'is_commercial': is_com,
                'is_hospitality': is_hos,
                'default_pricing_model': pricing
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
    
    # First create an admin user if not exists
    if not User.objects.filter(username='admin').exists():
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
        username = f"{first_name.lower()}{last_name.lower()}{random.randint(1000, 9999)}"
        email = f"{username}@example.com"
        phone = f"+2567{random.randint(10000000, 99999999)}"
        
        if User.objects.filter(username=username).exists():
            continue

        try:
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
        except Exception as e:
            print(f"Skipping duplicate or error for {username}: {e}")
            continue

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
    if not users:
        users = list(User.objects.all())
        
    property_types = list(PropertyType.objects.all())
    addresses = list(Address.objects.all())
    amenities = list(Amenity.objects.all())
    neighborhood_features = list(NeighborhoodFeature.objects.all())
    
    if not addresses:
        print("No addresses found, creating some...")
        create_addresses(count=count)
        addresses = list(Address.objects.all())

    for i in range(count):
        try:
            owner = random.choice(users)
            agent = random.choice(users) if random.random() < 0.5 else None
            property_type = random.choice(property_types)
            address = addresses[i] if i < len(addresses) else random.choice(addresses)
            
            # Use property type default specific logic
            pricing_model = property_type.default_pricing_model
            is_res = property_type.is_residential
            is_com = property_type.is_commercial
            is_hos = property_type.is_hospitality
            
            # Base data
            prop_data = {
                'owner': owner,
                'agent': agent,
                'property_type': property_type,
                'address': address,
                'description': fake.text(max_nb_chars=500),
                'price_currency': 'UGX',
                'is_price_negotiable': random.random() < 0.7,
                'status': random.choice(LISTING_STATUS),
                'is_featured': random.random() < 0.1,
                'view_count': random.randint(0, 500),
                'favorite_count': random.randint(0, 50),
                'is_published': random.random() < 0.8,
                'listed_by': owner,
                'rating': Decimal(str(round(random.uniform(3, 5), 2))),
                'parking_spaces': random.randint(0, 5),
                'internet_included': random.random() < 0.7,
                'year_built': random.randint(1990, 2025),
                'floors': random.randint(1, 4),
                'furnishing_status': random.choice(FURNISHING_STATUS),
                'availability_status': random.choice(AVAILABILITY_STATUS),
            }

            # Generate Title
            city_name = address.city
            prop_data['title'] = f"{random.choice(['Modern', 'Spacious', 'Prime', 'Luxury', 'Cozy'])} {property_type.name} in {city_name}"
            # Ensure unique slug
            base_slug = slugify(prop_data['title'])
            prop_data['slug'] = f"{base_slug}-{uuid.uuid4().hex[:8]}"

            # Pricing Logic
            base_value = random.randint(50, 5000) * 1000 # Base numeric factor
            
            if pricing_model == 'fixed':
                # Sale prices usually
                prop_data['price'] = Decimal(base_value * 100) # e.g. 5M to 500M
                prop_data['category'] = 'sale'
            elif pricing_model == 'per_month':
                # Rent
                prop_data['monthly_rate'] = Decimal(base_value) # e.g. 50k to 5M
                prop_data['category'] = 'rent'
                # Optional: set price to monthly rate for fallback
                prop_data['price'] = prop_data['monthly_rate']
            elif pricing_model == 'per_night':
                prop_data['nightly_rate'] = Decimal(base_value / 20) 
                prop_data['category'] = 'nightly'
                prop_data['price'] = prop_data['nightly_rate']
            elif pricing_model == 'per_hour':
                prop_data['hourly_rate'] = Decimal(base_value / 100)
                prop_data['category'] = 'hourly'
                prop_data['price'] = prop_data['hourly_rate']
            elif pricing_model == 'per_sqft':
                prop_data['price_per_sqft'] = Decimal(random.randint(10, 50) * 1000)
                prop_data['category'] = 'lease'
                prop_data['price'] = Decimal(0) 
            else:
                # Fallback
                prop_data['price'] = Decimal(base_value * 10)
                prop_data['category'] = 'sale'

            # Type Specific Details
            prop_data['square_feet'] = random.randint(300, 5000)

            if is_res:
                prop_data['bedrooms'] = random.randint(1, 6)
                prop_data['bathrooms'] = Decimal(random.randint(1, 5))
                prop_data['lot_size'] = Decimal(str(round(random.uniform(0.05, 1.0), 2)))
            
            if is_com:
                prop_data['shop_size'] = prop_data['square_feet'] if 'Shop' in property_type.name else 0
                prop_data['office_spaces'] = random.randint(1, 10) if 'Office' in property_type.name else 0
                prop_data['warehouse_capacity'] = random.randint(1000, 20000) if 'Warehouse' in property_type.name else 0
                prop_data['has_storefront'] = random.random() < 0.5
                prop_data['garage_slots'] = random.randint(0, 10)

            if is_hos:
                prop_data['maximum_occupancy'] = random.randint(1, 4)
                prop_data['minimum_stay_nights'] = 1
                prop_data['check_in_time'] = "12:00"
                prop_data['check_out_time'] = "10:00"

            # Create Property
            prop = Property.objects.create(**prop_data)

            # Assign Amenities
            prop.amenities.set(random.sample(amenities, k=random.randint(2, 6)))
            prop.neighborhood_features.set(random.sample(neighborhood_features, k=random.randint(2, 5)))
            
            if (i + 1) % 50 == 0:
                print(f"Created {i + 1} properties")
                
        except Exception as e:
            print(f"Error creating property index {i}: {e}")
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