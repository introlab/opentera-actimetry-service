from ConfigManager import ConfigManager
from libactimetry.db.DBManager import DBManager
from opentera.redis.RedisClient import RedisClient
from opentera.services.ServiceOpenTeraWithAssets import ServiceOpenTeraWithAssets

# Configuration manager
config_man : ConfigManager = ConfigManager()

# DB
db_man : DBManager = None

# Redis client & keys
redis_client : RedisClient = None

# Service
service : ServiceOpenTeraWithAssets = None
