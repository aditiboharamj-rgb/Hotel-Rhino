import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_rhino_core.settings')
django.setup()

from django.contrib.auth.models import User
from thakali_app.models import (
    StaffProfile, RestaurantTable, KhanaSet, CustomerReview, TableReservation
)

print("Starting Hotel Rhino seed script...")

# 1. Create Superuser / Admin & Staff Accounts
admin_user, created = User.objects.get_or_create(username='admin', defaults={
    'email': 'admin@hotelrhinothakali.com',
    'first_name': 'Subash',
    'last_name': 'Thakali',
    'is_staff': True,
    'is_superuser': True,
})
if created:
    admin_user.set_password('admin123')
    admin_user.save()
    StaffProfile.objects.create(user=admin_user, role='ADMIN', phone='+977-9801234567')
    print("Created Admin user: admin / admin123")
else:
    StaffProfile.objects.get_or_create(user=admin_user, defaults={'role': 'ADMIN', 'phone': '+977-9801234567'})

# Cashier User
cashier_user, created = User.objects.get_or_create(username='cashier', defaults={
    'email': 'cashier@hotelrhinothakali.com',
    'first_name': 'Pooja',
    'last_name': 'Gauchan',
    'is_staff': True,
})
if created:
    cashier_user.set_password('cashier123')
    cashier_user.save()
    StaffProfile.objects.create(user=cashier_user, role='CASHIER', phone='+977-9812345678')
    print("Created Cashier user: cashier / cashier123")

# Waiter User
waiter_user, created = User.objects.get_or_create(username='waiter', defaults={
    'email': 'waiter@hotelrhinothakali.com',
    'first_name': 'Bikash',
    'last_name': 'Sherchan',
    'is_staff': True,
})
if created:
    waiter_user.set_password('waiter123')
    waiter_user.save()
    StaffProfile.objects.create(user=waiter_user, role='WAITER', phone='+977-9823456789')
    print("Created Waiter user: waiter / waiter123")

# Kitchen Staff User
kitchen_user, created = User.objects.get_or_create(username='kitchen', defaults={
    'email': 'kitchen@hotelrhinothakali.com',
    'first_name': 'Chef Pemba',
    'last_name': 'Tulachan',
    'is_staff': True,
})
if created:
    kitchen_user.set_password('kitchen123')
    kitchen_user.save()
    StaffProfile.objects.create(user=kitchen_user, role='KITCHEN', phone='+977-9834567890')
    print("Created Kitchen user: kitchen / kitchen123")

# 2. Seed Restaurant Tables
tables_data = [
    ('1', 'Courtyard Garden 1', 2),
    ('2', 'Courtyard Garden 2', 4),
    ('3', 'Heritage Dining 3', 4),
    ('4', 'Heritage Dining 4', 6),
    ('5', 'Mustang Hall 5', 4),
    ('6', 'Mustang Hall 6', 8),
    ('7', 'Terrace View 7', 4),
    ('8', 'Terrace View 8', 2),
]
for t_num, name, cap in tables_data:
    t, _ = RestaurantTable.objects.get_or_create(
        table_number=t_num,
        defaults={'name': name, 'capacity': cap, 'status': 'AVAILABLE'}
    )
print(f"Ensured {RestaurantTable.objects.count()} restaurant tables initialized.")

# 3. Seed Exclusive Authentic Nepali Thakali Khana Sets
khana_sets = [
    {
        'name': 'Traditional Vegetarian Thakali Khana Set',
        'slug': 'veg-thakali-khana-set',
        'category': 'VEG',
        'price_npr': Decimal('450.00'),
        'description': 'The quintessence of Mustang mountain nourishment. Featuring slow-simmered Mustang black lentils hand-tempered in aromatic Jimbu and pure golden ghee, served with fragrant steamed rice, fresh mountain mustard greens (Rayo ko Saag), seasonal spiced curry, sun-cured Gundruk Sadeko, stone-ground Timur tomato chutney, and crispy lentil papadam in authentic heavy brass Kansa tableware.',
        'traditional_items': 'Mustang Jimbu Dal, Steamed Rice, Seasonal Tarkari, Rayo ko Saag, Gundruk Sadeko, Timur Chutney, Papad, Pure Mountain Ghee',
        'portion_info': 'Complete Himalayan Thali with Unlimited Bhat, Dal & Tarkari refills',
        'image_url': 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=800&q=80',
        'order_priority': 1,
    },
    {
        'name': 'Authentic Chicken Thakali Khana Set (Local Kukhura)',
        'slug': 'chicken-thakali-khana-set',
        'category': 'CHICKEN',
        'price_npr': Decimal('650.00'),
        'description': 'Free-range Nepali local chicken (Local Kukhura) slow-cooked with whole Himalayan spices, cloves, black cardamom, and fragrant mountain herbs. Accompanied by steaming fluffy rice, Mustang Jimbu dal, fresh seasonal vegetables, Rayo ko saag, fermented Gundruk, stone-milled Timur achar, and crisp roasted papad, finished with generous spoonfuls of hot aromatic cow ghee.',
        'traditional_items': 'Local Chicken Curry (Kukhura ko Jhol), Jimbu Dal, Basmati Rice, Tarkari, Rayo ko Saag, Gundruk Sadeko, Timur Achar, Papad, Ghee',
        'portion_info': 'Generous chicken portion with Unlimited Rice, Dal & Vegetable refills',
        'image_url': 'https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?auto=format&fit=crop&w=800&q=80',
        'order_priority': 2,
    },
    {
        'name': 'Royal Mutton Thakali Khana Set (Himalayan Khasi)',
        'slug': 'mutton-thakali-khana-set',
        'category': 'MUTTON',
        'price_npr': Decimal('850.00'),
        'description': 'Our most celebrated culinary masterpiece. Tender mountain goat (Himalayan Khasi) braised patiently in traditional brass degh with wild Sichuan peppercorns (Timur), shallots, and fragrant mountain spice blend. Served alongside unlimited piping hot steamed rice, Jimbu Mustang black dal, crisp seasonal greens, organic Gundruk, Timur tomato relish, and pure Shingati ghee.',
        'traditional_items': 'Tender Mountain Mutton Curry, Jimbu Dal, Steamed Rice, Seasonal Tarkari, Rayo ko Saag, Gundruk Sadeko, Timur Achar, Papad, Pure Ghee',
        'portion_info': 'Rich slow-braised mutton portion with Unlimited Bhat & Dal refills',
        'image_url': 'https://images.unsplash.com/photo-1596797038530-2c107229654b?auto=format&fit=crop&w=800&q=80',
        'order_priority': 3,
    },
    {
        'name': 'Himalayan Fresh River Fish Thakali Khana Set',
        'slug': 'fish-thakali-khana-set',
        'category': 'FISH',
        'price_npr': Decimal('750.00'),
        'description': 'Fresh mountain river fish gently pan-seared and simmered in a light golden turmeric, mustard seed, and fenugreek broth. Served with aromatic steamed rice, slow-cooked Jimbu Mustang dal, seasonal hill potatoes, fresh green mustard saag, roasted Timur chutney, sun-dried Gundruk, and crunchy papad.',
        'traditional_items': 'Fresh River Fish Curry (Machha ko Jhol), Jimbu Dal, Steamed Rice, Tarkari, Saag, Gundruk, Timur Chutney, Papad, Ghee',
        'portion_info': 'Pan-seared river fish with Unlimited Steamed Rice & Dal refills',
        'image_url': 'https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?auto=format&fit=crop&w=800&q=80',
        'order_priority': 4,
    },
    {
        'name': 'Special Mustang Dhido Thakali Khana Set',
        'slug': 'mustang-dhido-thakali-set',
        'category': 'VEG',
        'price_npr': Decimal('550.00'),
        'description': 'A time-honored Himalayan staple made from stone-ground organic mountain buckwheat (Phapar) and millet (Kodo), served piping hot with melted Shingati Chyangra cow ghee, Jimbu-fried black dal, fresh rayo saag, spicy timur pickle, and seasonal hill tarkari.',
        'traditional_items': 'Hot Organic Buckwheat/Millet Dhido, Pure Cow Ghee, Jimbu Mustang Dal, Rayo ko Saag, Gundruk Sadeko, Timur Chutney, Seasonal Tarkari',
        'portion_info': 'Wholesome ancestral energy meal with unlimited soup & vegetable refills',
        'image_url': 'https://images.unsplash.com/photo-1589302168068-964664d93dc0?auto=format&fit=crop&w=800&q=80',
        'order_priority': 5,
    },
    {
        'name': 'Heritage Sukuti & Sekuwa Thakali Feast Set',
        'slug': 'sukuti-sekuwa-thakali-feast-set',
        'category': 'MUTTON',
        'price_npr': Decimal('950.00'),
        'description': 'The ultimate celebratory Thakali feast. Features smoked hill goat Sukuti sautéed with garlic, green chilies, and fenugreek, served alongside tender mountain mutton curry, hot Basmati rice, Jimbu Mustang dal, charred Timur chutney, roasted Bhatmas, and pure golden ghee.',
        'traditional_items': 'Dry-Cured Goat Sukuti, Tender Mutton Curry, Jimbu Dal, Steamed Rice, Rayo ko Saag, Gundruk Sadeko, Timur Chutney, Papad, Pure Ghee',
        'portion_info': 'Grand celebratory Himalayan banquet with full unlimited side refills',
        'image_url': 'https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=800&q=80',
        'order_priority': 6,
    },
]

for kd in khana_sets:
    ks, created = KhanaSet.objects.get_or_create(
        slug=kd['slug'],
        defaults=kd
    )
    if not created:
        for key, val in kd.items():
            setattr(ks, key, val)
        ks.save()
print(f"Ensured {KhanaSet.objects.count()} authentic Thakali Khana Sets initialized.")

# 4. Seed Approved Real Customer Reviews
reviews_data = [
    ("Prabhat Bhattarai", 5, "Without doubt the finest authentic Thakali Thali in the country. The Jimbu dal tempered in hot ghee transported me straight to Mustang. Exceptional service and gracious refills!", "Kathmandu"),
    ("Dipendra Thapa Magar", 5, "The Mutton Thakali set here is extraordinary. The tender meat infused with mountain timur pepper is something I have never tasted before. The traditional brass plates are breathtaking.", "Dhangadhi, Kailali"),
    ("Binita Shrestha", 5, "I love how pure the food is. No fast food nonsense, no fake flavors — pure traditional Nepali cooking with unlimited hot rice and saag. Hotel Rhino is a true gem.", "Pokhara"),
]
for name, rating, comment, city in reviews_data:
    CustomerReview.objects.get_or_create(
        name=name,
        defaults={'rating': rating, 'comment': comment, 'city': city, 'is_approved': True}
    )

print("Hotel Rhino database seed completed successfully.")

