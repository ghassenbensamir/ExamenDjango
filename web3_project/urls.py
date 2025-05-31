"""
URL configuration for web3_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# web3_project/urls.py

from django.contrib import admin
from django.urls import path, include
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt # Pour tests GraphQL

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Inclure les URLs de votre application 'api'
    path('api/', include('api_smartcontract.urls')), 
    
    # Endpoint GraphQL (avec l'interface GraphiQL activée pour le développement)
    path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True))),
]

