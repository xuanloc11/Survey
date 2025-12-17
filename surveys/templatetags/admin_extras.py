from django import template
from django.contrib.auth.models import User

register = template.Library()


@register.simple_tag
def get_admin_stats():
    """Thống kê tối giản cho admin (tập trung người dùng)"""
    users = User.objects.all()

    return {
        'total_users': users.count(),
        'total_staff': users.filter(is_staff=True).count(),
        'total_superusers': users.filter(is_superuser=True).count(),
        'recent_users': users.order_by('-date_joined')[:10],
    }

