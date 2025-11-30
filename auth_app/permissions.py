from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to access it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if the user is the owner of the object or an admin
        if hasattr(obj, 'user'):
            return obj.user == request.user or request.user.is_admin()
        elif hasattr(obj, 'id'):
            return obj.id == request.user.id or request.user.is_admin()
        return False

class IsAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admins to access.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin()
    
    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user.is_admin()
    


    # ===========================MESSAGING/NOTIFICATION===========================
    