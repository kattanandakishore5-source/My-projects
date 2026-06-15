import os
import sys
import django

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myawesomecart.settings')
django.setup()

from shop.models import Product
from PIL import Image
from django.db.models import Q


def convert_images():
    media_dir = os.path.join('media', 'shop', 'images')
    if not os.path.exists(media_dir):
        print(f"Directory {media_dir} not found.")
        return

    converted_count = 0
    # Update files
    for filename in os.listdir(media_dir):
        if filename.lower().endswith(('.jpg', '.jpeg')):
            filepath = os.path.join(media_dir, filename)
            webp_filename = filename.rsplit('.', 1)[0] + '.webp'
            webp_filepath = os.path.join(media_dir, webp_filename)

            try:
                with Image.open(filepath) as img:
                    img.save(webp_filepath, 'webp')
                os.remove(filepath)
                converted_count += 1
                print(f"Converted: {filename} -> {webp_filename}")
            except Exception as e:
                print(f"Error converting {filename}: {e}")

    # Update database
    # Optimized: Only fetch records that actually have .jpg or .jpeg extensions
    products = Product.objects.filter(
        Q(image__icontains='.jpg') | Q(image__icontains='.jpeg')
    )

    db_updated = 0
    for product in products:
        old_path = str(product.image)
        new_path = old_path.rsplit('.', 1)[0] + '.webp'
        product.image = new_path
        product.save(update_fields=['image'])
        db_updated += 1

    print(f"\nConversion complete. \nImages converted: {converted_count}. \nDB records updated: {db_updated}.")


if __name__ == '__main__':
    convert_images()