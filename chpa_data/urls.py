from django.urls import path

from chpa_data import views

app_name = 'chpa'

urlpatterns = [

    path('index/', views.index, name='index'),
    path(r'search/<str:column>/<str:kw>',views.search,name='search'),
    path(r'query/',views.query,name='query'),
    path(r'export/<str:type>/<str:c>/',views.export,name='export'),

]
