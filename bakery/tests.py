"""
Basic test suite for Tastyz Bakery AI System.

Covers:
- Model tests (Product, Order)
- View tests (home, products, chat, recommend)
- Agent tool tests
- Token tracker tests
"""

from django.test import TestCase, Client
from django.urls import reverse

from bakery.models import Product, Order
from bakery.token_tracker import estimate_tokens, estimate_cost, TokenTracker


# ──────────────────────────────────────────────────────────────
# Model Tests
# ──────────────────────────────────────────────────────────────


class ProductModelTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Vanilla Sponge Cake",
            category="cake",
            description="A classic vanilla sponge cake",
            price_small=65000,
            price_large=85000,
            is_available=True,
        )

    def test_product_str(self):
        self.assertEqual(str(self.product), "Vanilla Sponge Cake")

    def test_product_price_display(self):
        display = self.product.price_display
        self.assertIn("65", display)

    def test_product_is_available(self):
        self.assertTrue(self.product.is_available)

    def test_product_category(self):
        self.assertEqual(self.product.category, "cake")


class OrderModelTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Chocolate Cake",
            category="cake",
            price_small=75000,
            price_large=95000,
        )

    def test_order_creation(self):
        order = Order.objects.create(
            customer_name="John Doe",
            customer_phone="+256700000000",
            product=self.product,
            product_name_snapshot="Chocolate Cake",
            size="1KG",
            quantity=1,
            delivery_date="2026-03-25",
            delivery_address="Kampala, Uganda",
            payment_method="mobile_money",
        )
        self.assertEqual(order.customer_name, "John Doe")
        self.assertEqual(order.product_name_snapshot, "Chocolate Cake")


# ──────────────────────────────────────────────────────────────
# View Tests
# ──────────────────────────────────────────────────────────────


class HomeViewTest(TestCase):
    def test_home_status_code(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_home_template(self):
        response = self.client.get(reverse("home"))
        self.assertTemplateUsed(response, "bakery/home.html")

    def test_home_contains_title(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Tastyz Bakery")


class ProductsViewTest(TestCase):
    def setUp(self):
        Product.objects.create(
            name="Test Cake",
            category="cake",
            price_small=50000,
            price_large=70000,
            is_available=True,
        )

    def test_products_status_code(self):
        response = self.client.get(reverse("products"))
        self.assertEqual(response.status_code, 200)

    def test_products_shows_product(self):
        response = self.client.get(reverse("products"))
        self.assertContains(response, "Test Cake")


class ChatViewTest(TestCase):
    def test_chat_page_loads(self):
        response = self.client.get(reverse("chat"))
        self.assertEqual(response.status_code, 200)

    def test_chat_template(self):
        response = self.client.get(reverse("chat"))
        self.assertTemplateUsed(response, "bakery/chat.html")

    def test_chat_contains_ai_label(self):
        response = self.client.get(reverse("chat"))
        self.assertContains(response, "Tastyz AI")


class ChatAPITest(TestCase):
    def test_chat_api_rejects_get(self):
        response = self.client.get(reverse("chat_api"))
        self.assertEqual(response.status_code, 405)

    def test_chat_api_rejects_empty_question(self):
        response = self.client.post(
            reverse("chat_api"),
            data='{"question": ""}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_chat_api_rejects_long_question(self):
        response = self.client.post(
            reverse("chat_api"),
            data='{"question": "' + "x" * 501 + '"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class RecommendViewTest(TestCase):
    def test_recommend_page_loads(self):
        response = self.client.get(reverse("recommend"))
        self.assertEqual(response.status_code, 200)

    def test_recommend_template(self):
        response = self.client.get(reverse("recommend"))
        self.assertTemplateUsed(response, "bakery/recommend.html")


class OrderViewTest(TestCase):
    def test_order_page_loads(self):
        response = self.client.get(reverse("place_order"))
        self.assertEqual(response.status_code, 200)

    def test_order_template(self):
        response = self.client.get(reverse("place_order"))
        self.assertTemplateUsed(response, "bakery/order.html")


# ──────────────────────────────────────────────────────────────
# Token Tracker Tests
# ──────────────────────────────────────────────────────────────


class TokenEstimationTest(TestCase):
    def test_empty_string(self):
        self.assertEqual(estimate_tokens(""), 0)

    def test_short_text(self):
        tokens = estimate_tokens("Hello world")
        self.assertGreater(tokens, 0)

    def test_longer_text(self):
        text = "The quick brown fox jumps over the lazy dog. " * 10
        tokens = estimate_tokens(text)
        self.assertGreater(tokens, 50)

    def test_cost_calculation(self):
        cost = estimate_cost("gpt-4o-mini", 1000, 500)
        self.assertGreater(cost, 0)
        self.assertLess(cost, 1.0)  # Should be fractions of a cent


class TokenTrackerTest(TestCase):
    def test_tracker_record(self):
        tracker = TokenTracker()
        record = tracker.record("rag_agent", "gpt-4o-mini", "Hello", "World")
        self.assertEqual(record.agent, "rag_agent")
        self.assertGreater(record.input_tokens, 0)

    def test_tracker_summary(self):
        tracker = TokenTracker()
        tracker.record("rag", "gpt-4o-mini", "Test input", "Test output")
        tracker.record("rec", "gpt-4o-mini", "Another input", "Another output")
        summary = tracker.get_summary()
        self.assertEqual(summary["total_requests"], 2)
        self.assertGreater(summary["total_tokens"], 0)

    def test_tracker_cost_accumulation(self):
        tracker = TokenTracker()
        tracker.record("test", "gpt-4o-mini", "a" * 4000, "b" * 2000)
        summary = tracker.get_summary()
        self.assertGreater(summary["total_cost_usd"], 0)
