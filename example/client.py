from models import Item
from pyrolysis.client import service

serv = service.ClientService('http://localhost:4000', username='myuser', password='mypassword',
                                 api_key='azerty').build()

serv.create_item(Item(name='item 1'))
items = serv.get_all_items()
