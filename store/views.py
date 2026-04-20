"""
Module: store.views

Contains Django views for managing items, profiles,
and deliveries in the store application.

Classes handle product listing, creation, updating,
deletion, and delivery management.
The module integrates with Django's authentication
and querying functionalities.
"""

# Standard library imports
import operator
from functools import reduce
import json

# Django core imports
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Sum, F, FloatField

# Authentication and permissions
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

# Class-based views
from django.views.generic import (
    DetailView, CreateView, UpdateView, DeleteView, ListView
)
from django.views.generic.edit import FormMixin

# Third-party packages
from django_tables2 import SingleTableView
import django_tables2 as tables
from django_tables2.export.views import ExportMixin

# Local app imports
from accounts.models import Profile, Vendor
from transactions.models import Sale, SaleDetail, Purchase
from .models import Category, Item, Delivery
from .forms import ItemForm, CategoryForm, DeliveryForm
from .tables import ItemTable


@login_required
def dashboard(request):
    profiles = Profile.objects.all()
    Category.objects.annotate(nitem=Count("item"))
    items = Item.objects.all()
    total_items = (
        Item.objects.all()
        .aggregate(Sum("quantity"))
        .get("quantity__sum", 0.00)
    )
    items_count = items.count()
    profiles_count = profiles.count()

    # Prepare data for charts
    category_counts = Category.objects.annotate(
        item_count=Count("item")
    ).values("name", "item_count")
    categories = [cat["name"] for cat in category_counts]
    category_counts = [cat["item_count"] for cat in category_counts]

    # Emoji mapping for categories
    category_emoji_map = {
        "Fruits": "🍇",
        "Vegetables": "🥦",
        "Dairy": "🥛",
        "Bakery": "🍞",
        "Meat": "🥩",
        "Beverages": "🥤",
        "Snacks": "🍪",
        "Seafood": "🦐",
        # Add more as needed
    }
    category_emojis = [category_emoji_map.get(cat, '') for cat in categories]

    sale_dates = (
        Sale.objects.values("date_added__date")
        .annotate(total_sales=Sum("grand_total"))
        .order_by("date_added__date")
    )
    sale_dates_labels = [
        date["date_added__date"].strftime("%Y-%m-%d") for date in sale_dates
    ]
    sale_dates_values = [float(date["total_sales"]) for date in sale_dates]

    # Calculate Profit/Loss data (aggregate method: sales vs purchases)
    from datetime import datetime, timedelta
    from django.utils import timezone

    # Get last 30 days for profit/loss calculation
    thirty_days_ago = timezone.now() - timedelta(days=30)

    # Calculate total revenue from sales
    total_revenue = Sale.objects.filter(
        date_added__gte=thirty_days_ago
    ).aggregate(total=Sum('grand_total'))['total'] or 0

    # Calculate total cost from purchases
    total_cost = Purchase.objects.filter(
        order_date__gte=thirty_days_ago
    ).aggregate(total=Sum('total_value'))['total'] or 0

    # Calculate profit/loss
    profit_loss = float(total_revenue) - float(total_cost)

    # Get daily profit/loss data for chart
    daily_profit_data = []
    daily_labels = []

    for i in range(30):
        date = timezone.now() - timedelta(days=i)
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        daily_revenue = Sale.objects.filter(
            date_added__gte=start_of_day,
            date_added__lte=end_of_day
        ).aggregate(total=Sum('grand_total'))['total'] or 0

        daily_cost = Purchase.objects.filter(
            order_date__gte=start_of_day,
            order_date__lte=end_of_day
        ).aggregate(total=Sum('total_value'))['total'] or 0

        daily_profit = float(daily_revenue) - float(daily_cost)
        daily_profit_data.append(daily_profit)
        daily_labels.append(date.strftime('%m/%d'))

    # Reverse to show oldest to newest
    daily_profit_data.reverse()
    daily_labels.reverse()

    # Build Category Sales Trend (Last 30 Days)
    # Determine top categories by total sales in the period
    from django.db.models import ExpressionWrapper
    value_expr = ExpressionWrapper(F('price') * F('quantity'), output_field=FloatField())
    top_categories_qs = (
        SaleDetail.objects.filter(sale__date_added__gte=thirty_days_ago)
        .values('item__category__name')
        .annotate(total=Sum(value_expr))
        .order_by('-total')
    )
    top_categories = [c['item__category__name'] for c in top_categories_qs[:5]]

    category_trend_labels = []
    category_trend_series = {cat: [] for cat in top_categories}

    for i in range(30):
        date = timezone.now() - timedelta(days=i)
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Sales per category for the day
        day_sales = (
            SaleDetail.objects.filter(sale__date_added__gte=start_of_day, sale__date_added__lte=end_of_day)
            .values('item__category__name')
            .annotate(total=Sum(value_expr))
        )
        totals_by_cat = {row['item__category__name']: float(row['total'] or 0) for row in day_sales}

        for cat in top_categories:
            category_trend_series[cat].append(totals_by_cat.get(cat, 0.0))

        category_trend_labels.append(date.strftime('%m/%d'))

    # Reverse to show oldest to newest
    category_trend_labels.reverse()
    for cat in category_trend_series:
        category_trend_series[cat].reverse()

    context = {
        "items": items,
        "profiles": profiles,
        "profiles_count": profiles_count,
        "items_count": items_count,
        "total_items": total_items,
        "vendors": Vendor.objects.all(),
        "delivery": Delivery.objects.filter(is_delivered=False),
        "sales": Sale.objects.all(),
        "categories": json.dumps(categories),
        "category_counts": json.dumps(category_counts),
        "category_emojis": json.dumps(category_emojis),
        "sale_dates_labels": sale_dates_labels,
        "sale_dates_values": sale_dates_values,
        # Profit/Loss values kept for compatibility but chart will be replaced
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "profit_loss": profit_loss,
        # New category trend data
        "category_trend_labels": json.dumps(category_trend_labels),
        "category_trend_series": json.dumps(category_trend_series),
    }
    return render(request, "store/dashboard.html", context)


class ProductListView(LoginRequiredMixin, ExportMixin, tables.SingleTableView):
    """
    View class to display a list of products.

    Attributes:
    - model: The model associated with the view.
    - table_class: The table class used for rendering.
    - template_name: The HTML template used for rendering the view.
    - context_object_name: The variable name for the context object.
    - paginate_by: Number of items per page for pagination.
    """

    model = Item
    table_class = ItemTable
    template_name = "store/productslist.html"
    context_object_name = "items"
    paginate_by = 10
    SingleTableView.table_pagination = False


class ItemSearchListView(ProductListView):
    """
    View class to search and display a filtered list of items.

    Attributes:
    - paginate_by: Number of items per page for pagination.
    """

    paginate_by = 10

    def get_queryset(self):
        result = super(ItemSearchListView, self).get_queryset()

        query = self.request.GET.get("q")
        if query:
            query_list = query.split()
            result = result.filter(
                reduce(
                    operator.and_, (Q(name__icontains=q) for q in query_list)
                )
            )
        return result


class ProductDetailView(LoginRequiredMixin, FormMixin, DetailView):
    """
    View class to display detailed information about a product.

    Attributes:
    - model: The model associated with the view.
    - template_name: The HTML template used for rendering the view.
    """

    model = Item
    template_name = "store/productdetail.html"

    def get_success_url(self):
        return reverse("product-detail", kwargs={"slug": self.object.slug})


class ProductCreateView(LoginRequiredMixin, CreateView):
    """
    View class to create a new product.

    Attributes:
    - model: The model associated with the view.
    - template_name: The HTML template used for rendering the view.
    - form_class: The form class used for data input.
    - success_url: The URL to redirect to upon successful form submission.
    """

    model = Item
    template_name = "store/productcreate.html"
    form_class = ItemForm
    success_url = "/products"

    def test_func(self):
        # item = Item.objects.get(id=pk)
        if self.request.POST.get("quantity") < 1:
            return False
        else:
            return True


class ProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View class to update product information.

    Attributes:
    - model: The model associated with the view.
    - template_name: The HTML template used for rendering the view.
    - fields: The fields to be updated.
    - success_url: The URL to redirect to upon successful form submission.
    """

    model = Item
    template_name = "store/productupdate.html"
    form_class = ItemForm
    success_url = "/products"

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        else:
            return False


class ProductDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    View class to delete a product.

    Attributes:
    - model: The model associated with the view.
    - template_name: The HTML template used for rendering the view.
    - success_url: The URL to redirect to upon successful deletion.
    """

    model = Item
    template_name = "store/productdelete.html"
    success_url = "/products"

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        else:
            return False


class DeliveryListView(
    LoginRequiredMixin, ExportMixin, tables.SingleTableView
):
    """
    View class to display a list of deliveries.

    Attributes:
    - model: The model associated with the view.
    - pagination: Number of items per page for pagination.
    - template_name: The HTML template used for rendering the view.
    - context_object_name: The variable name for the context object.
    """

    model = Delivery
    pagination = 10
    template_name = "store/deliveries.html"
    context_object_name = "deliveries"


class DeliverySearchListView(DeliveryListView):
    """
    View class to search and display a filtered list of deliveries.

    Attributes:
    - paginate_by: Number of items per page for pagination.
    """

    paginate_by = 10

    def get_queryset(self):
        result = super(DeliverySearchListView, self).get_queryset()

        query = self.request.GET.get("q")
        if query:
            query_list = query.split()
            result = result.filter(
                reduce(
                    operator.
                    and_, (Q(customer_name__icontains=q) for q in query_list)
                )
            )
        return result


class DeliveryDetailView(LoginRequiredMixin, DetailView):
    """
    View class to display detailed information about a delivery.

    Attributes:
    - model: The model associated with the view.
    - template_name: The HTML template used for rendering the view.
    """

    model = Delivery
    template_name = "store/deliverydetail.html"


class DeliveryCreateView(LoginRequiredMixin, CreateView):
    """
    View class to create a new delivery.

    Attributes:
    - model: The model associated with the view.
    - fields: The fields to be included in the form.
    - template_name: The HTML template used for rendering the view.
    - success_url: The URL to redirect to upon successful form submission.
    """

    model = Delivery
    form_class = DeliveryForm
    template_name = "store/delivery_form.html"
    success_url = "/deliveries"


class DeliveryUpdateView(LoginRequiredMixin, UpdateView):
    """
    View class to update delivery information.

    Attributes:
    - model: The model associated with the view.
    - fields: The fields to be updated.
    - template_name: The HTML template used for rendering the view.
    - success_url: The URL to redirect to upon successful form submission.
    """

    model = Delivery
    form_class = DeliveryForm
    template_name = "store/delivery_form.html"
    success_url = "/deliveries"


class DeliveryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    View class to delete a delivery.

    Attributes:
    - model: The model associated with the view.
    - template_name: The HTML template used for rendering the view.
    - success_url: The URL to redirect to upon successful deletion.
    """

    model = Delivery
    template_name = "store/productdelete.html"
    success_url = "/deliveries"

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        else:
            return False


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'store/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10
    login_url = 'login'


class CategoryDetailView(LoginRequiredMixin, DetailView):
    model = Category
    template_name = 'store/category_detail.html'
    context_object_name = 'category'
    login_url = 'login'


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    template_name = 'store/category_form.html'
    form_class = CategoryForm
    login_url = 'login'

    def get_success_url(self):
        return reverse_lazy('category-detail', kwargs={'pk': self.object.pk})


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    template_name = 'store/category_form.html'
    form_class = CategoryForm
    login_url = 'login'

    def get_success_url(self):
        return reverse_lazy('category-detail', kwargs={'pk': self.object.pk})


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'store/category_confirm_delete.html'
    context_object_name = 'category'
    success_url = reverse_lazy('category-list')
    login_url = 'login'


@login_required
def mark_delivery_completed(request, pk):
    """
    Mark a delivery as completed (is_delivered=True)
    """
    try:
        delivery = Delivery.objects.get(pk=pk)
        delivery.is_delivered = True
        delivery.save()
        messages.success(request, f'Delivery #{delivery.id} marked as completed!')
    except Delivery.DoesNotExist:
        messages.error(request, 'Delivery not found!')
    except Exception as e:
        messages.error(request, f'Error updating delivery: {str(e)}')
    
    return redirect('deliveries')


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


@csrf_exempt
@require_POST
@login_required
def get_items_ajax_view(request):
    if is_ajax(request):
        try:
            term = request.POST.get("term", "")
            data = []

            items = Item.objects.filter(name__icontains=term)
            for item in items[:10]:
                data.append(item.to_json())

            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Not an AJAX request'}, status=400)
