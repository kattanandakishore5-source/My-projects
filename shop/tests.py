from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from shop.models import Product, Cart, CartItem, Coupon, ProductReview
from shop.utils import calculate_cart_total, build_product_carousel
from datetime import date, timedelta

User = get_user_model()

class ShopTestCase(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username='testuser', password='password123')

        # Create test products
        self.product1 = Product.objects.create(
            product_name="Product 1",
            category="Category A",
            price=100,
            stock=10
        )
        self.product2 = Product.objects.create(
            product_name="Product 2",
            category="Category A",
            price=200,
            stock=5
        )
        self.product3 = Product.objects.create(
            product_name="Product 3",
            category="Category B",
            price=300,
            stock=20
        )

    def test_calculate_cart_total_no_coupon(self):
        cart = Cart.objects.create()
        CartItem.objects.create(cart=cart, product=self.product1, quantity=2)
        CartItem.objects.create(cart=cart, product=self.product2, quantity=1)

        subtotal, discount, total, coupon = calculate_cart_total(cart, None)

        self.assertEqual(subtotal, 400) # (100*2) + (200*1)
        self.assertEqual(discount, 0)
        self.assertEqual(total, 400)
        self.assertIsNone(coupon)

    def test_calculate_cart_total_with_percentage_coupon(self):
        cart = Cart.objects.create()
        CartItem.objects.create(cart=cart, product=self.product1, quantity=2) # 200

        # Create coupon
        coupon = Coupon.objects.create(
            code="SAVE10",
            valid_from=date.today() - timedelta(days=1),
            valid_to=date.today() + timedelta(days=1),
            discount_type="Percentage",
            discount_value=10,
            active=True
        )

        subtotal, discount, total, coupon_obj = calculate_cart_total(cart, coupon.id)

        self.assertEqual(subtotal, 200)
        self.assertEqual(discount, 20) # 10% of 200
        self.assertEqual(total, 180)
        self.assertEqual(coupon_obj, coupon)

    def test_calculate_cart_total_with_flat_coupon(self):
        cart = Cart.objects.create()
        CartItem.objects.create(cart=cart, product=self.product2, quantity=2) # 400

        # Create coupon
        coupon = Coupon.objects.create(
            code="FLAT50",
            valid_from=date.today() - timedelta(days=1),
            valid_to=date.today() + timedelta(days=1),
            discount_type="Flat",
            discount_value=50,
            active=True
        )

        subtotal, discount, total, coupon_obj = calculate_cart_total(cart, coupon.id)

        self.assertEqual(subtotal, 400)
        self.assertEqual(discount, 50)
        self.assertEqual(total, 350)

    def test_build_product_carousel(self):
        products = Product.objects.all().order_by('category')
        cart_items_dict = {self.product1.id: 2}
        user_wishlist_ids = {self.product2.id}

        carousel_data = build_product_carousel(products, cart_items_dict, user_wishlist_ids)

        # We have Category A (2 prods) and Category B (1 prod)
        self.assertEqual(len(carousel_data), 2)

        # Get Category A group from carousel data
        category_a_group = carousel_data[0][0]
        p1 = next(p for p in category_a_group if p.id == self.product1.id)
        p2 = next(p for p in category_a_group if p.id == self.product2.id)

        # Verify cart quantity assignment
        self.assertEqual(p1.cart_qty, 2)

        # Verify wishlist flags
        self.assertTrue(p2.in_wishlist)
        self.assertFalse(p1.in_wishlist)

    def test_product_review_rating_signals(self):
        # Product initially has no reviews
        self.assertEqual(self.product1.average_rating, 0.0)
        self.assertEqual(self.product1.review_count, 0)
        self.assertEqual(self.product1.star_rating, "☆☆☆☆☆")

        # Add a review
        review1 = ProductReview.objects.create(
            product=self.product1,
            user=self.user,
            rating=4,
            review_text="Good product"
        )

        # Refresh product
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.average_rating, 4.0)
        self.assertEqual(self.product1.review_count, 1)
        self.assertEqual(self.product1.star_rating, "★★★★☆")

        # Add another review
        user2 = User.objects.create_user(username='testuser2', password='password123')
        review2 = ProductReview.objects.create(
            product=self.product1,
            user=user2,
            rating=2,
            review_text="Decent"
        )

        self.product1.refresh_from_db()
        self.assertEqual(self.product1.average_rating, 3.0) # (4 + 2) / 2
        self.assertEqual(self.product1.review_count, 2)
        self.assertEqual(self.product1.star_rating, "★★★☆☆")

        # Delete review
        review2.delete()
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.average_rating, 4.0)
        self.assertEqual(self.product1.review_count, 1)
