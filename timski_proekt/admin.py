from django.contrib import admin
from timski_proekt.models import Child, Questionnaire, ParentResponse

# Register your models here.
admin.site.register(Child)
admin.site.register(Questionnaire)
admin.site.register(ParentResponse)