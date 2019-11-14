__version__ = '0.1.5'

try:
    import pandas
    pandas_df_type = pandas.DataFrame
except ImportError:
    pandas_df_type = type(None)

try:
    import msgpack
    has_msgpack = True
except ImportError:
    has_msgpack = False

try:
    import os
    login = os.getlogin()
except OSError:
    login = ''
