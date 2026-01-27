import os, sys, django

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, 'apps')
os.chdir(BASE_DIR)
sys.path.insert(0, APP_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')
django.setup()

from knowledge.models import Document
print('所有文档:')
for doc in Document.objects.all():
    print(f'  ID: {doc.id}, 名称: {doc.name}')