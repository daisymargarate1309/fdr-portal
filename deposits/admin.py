from django.contrib import admin
from .models import AuditLog, FDR, Institution, ReleaseRequest

admin.site.register(Institution)
admin.site.register(FDR)
admin.site.register(ReleaseRequest)
admin.site.register(AuditLog)