import os
import time
import json
import requests
from datetime import datetime
from io import BytesIO
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from shop.models import Product
from faker import Faker

class Command(BaseCommand):
    help = 'Seed exactly 100 fake products with placeholder images'

    def handle(self, *args, **options):
        fake = Faker()
        
        start_count = Product.objects.count()
        self.stdout.write(f"[START] Product count: {start_count}")
        
        start_time = time.time()
        
        samples = []
        
        for i in range(100):
            product_name = fake.company() + " " + fake.word().capitalize()
            category = fake.word().capitalize()
            subcategory = fake.word().capitalize()
            price = fake.random_int(min=10, max=10000)
            desc = fake.text(max_nb_chars=200)
            
            # Fetch a random image from picsum
            response = requests.get(f'https://picsum.photos/seed/{fake.uuid4()}/400/400')
            
            product = Product(
                product_name=product_name,
                category=category,
                subcategory=subcategory,
                price=price,
                desc=desc,
                stock=fake.random_int(min=0, max=500),
                low_stock_threshold=fake.random_int(min=1, max=10),
                is_active=True,
                average_rating=round(fake.pyfloat(min_value=1.0, max_value=5.0), 1),
                review_count=fake.random_int(min=0, max=1000)
            )
            
            if response.status_code == 200:
                image_name = f"product_{fake.uuid4()}.jpg"
                product.image.save(image_name, ContentFile(response.content), save=False)
                
            product.save()
            
            if len(samples) < 5:
                samples.append({
                    "product_name": product.product_name,
                    "price": product.price
                })
                
        end_time = time.time()
        time_taken = round(end_time - start_time, 2)
        
        end_count = Product.objects.count()
        self.stdout.write(f"[END] Product count: {end_count} and total time taken in seconds: {time_taken}")
        
        proof_data = {
            "start_count": start_count,
            "end_count": end_count,
            "time_taken": time_taken,
            "samples": samples,
            "timestamp": datetime.now().isoformat()
        }
        
        proof_path = os.path.join(os.getcwd(), 'seed_proof.json')
        with open(proof_path, 'w') as f:
            json.dump(proof_data, f, indent=4)
            
        self.stdout.write(self.style.SUCCESS(f'Successfully saved proof to {proof_path}'))
