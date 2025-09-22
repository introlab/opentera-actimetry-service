from ConfigManager import ConfigManager
from libactimetry.db.DBManager import DBManager
from libactimetry.workers.WorkerManager import WorkerManager
from opentera.redis.RedisClient import RedisClient
from opentera.services.ServiceOpenTeraWithAssets import ServiceOpenTeraWithAssets

# Configuration manager
config_man : ConfigManager = ConfigManager()

# DB
db_man : DBManager | None = None

# Redis client & keys
redis_client : RedisClient | None = None

# Service
service : ServiceOpenTeraWithAssets | None = None

# Worker manager
worker_man : WorkerManager | None = None