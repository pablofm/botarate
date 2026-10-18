from django.urls import path

from . import views

urlpatterns = [
    path('ambigu/', views.BebidaListView.as_view(), name='bebidas'),
    path('ambigu/bebidas/nueva/', views.BebidaCreateView.as_view(), name='bebida_nueva'),
    path('ambigu/bebidas/<int:pk>/editar/', views.BebidaUpdateView.as_view(), name='bebida_editar'),
    path('ambigu/bebidas/<int:pk>/eliminar/', views.BebidaDeleteView.as_view(), name='bebida_eliminar'),
    path('ambigu/categorias/', views.CategoríaBebidaListView.as_view(), name='categorias_bebida'),
    path('ambigu/categorias/nueva/', views.CategoríaBebidaCreateView.as_view(),
         name='categoria_bebida_nueva'),
    path('ambigu/categorias/<int:pk>/editar/', views.CategoríaBebidaUpdateView.as_view(),
         name='categoria_bebida_editar'),
    path('ambigu/categorias/<int:pk>/eliminar/', views.CategoríaBebidaDeleteView.as_view(),
         name='categoria_bebida_eliminar'),
    path('ambigu/stock/', views.StockBebidaListView.as_view(), name='stock_bebidas'),
    path('ambigu/stock/nuevo/', views.StockBebidaCreateView.as_view(), name='stock_bebida_nuevo'),
    path('ambigu/stock/<int:pk>/editar/', views.StockBebidaUpdateView.as_view(), name='stock_bebida_editar'),
    path('ambigu/stock/<int:pk>/eliminar/', views.StockBebidaDeleteView.as_view(),
         name='stock_bebida_eliminar'),
    path('ambigu/ventas/', views.VentaBebidaListView.as_view(), name='ventas_bebidas'),
    path('ambigu/ventas/nueva/', views.VentaBebidaCreateView.as_view(), name='venta_bebida_nueva'),
    path('ambigu/ventas/<int:pk>/editar/', views.VentaBebidaUpdateView.as_view(), name='venta_bebida_editar'),
    path('ambigu/ventas/<int:pk>/eliminar/', views.VentaBebidaDeleteView.as_view(),
         name='venta_bebida_eliminar'),
]
